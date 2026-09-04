"""The raw Egocentric-10K corpus adapter: `S10k-U` and `S10k-S`'s frame pools, their
stratification weights, and single-frame extraction out of h265 video.

This is the unit `docs/DECISIONS.md` D065 declined to scope. Three facts make it small:

1. **Cluster labels are free.** Every clip's `.json` sidecar inside the shard carries
   `factory_id`/`worker_id`, so `scripts/build_corpus_manifest.py` indexes the whole corpus
   with ranged reads and never downloads a shard. This module consumes that manifest.
2. **No new dependency.** ffmpeg's `subfile` protocol presents a byte window of another URL as
   a seekable file, so a single frame comes out of an mp4 inside a tar over HTTP range
   requests. PyAV would have been the obvious choice and is unavailable here anyway (no
   cp313 wheel for this platform on any release).
3. **`-ss` before `-i` is an input seek.** ffmpeg reads the moov index and range-requests only
   the GOP it needs -- a few MB, not the 200-600 MB clip.

**Two constructions are made here and neither exists in the raw data.** D065: the corpus ships
`duration_sec` and `fps` per clip and nothing per frame, so `timestamp_s` and `frame_index` are
chosen by this module. They are drawn, seeded, from `range(int(duration_sec * fps))` -- uniform
over frames by construction, which is what `PRE-REGISTRATION.md` specifies for `S10k-U`.

The pools differ by sample on purpose, and the difference is statistical, not cosmetic:

- **`S10k-S`** gets one candidate per clip. `_draw_stratified_corpus` dedupes to <=1 frame per
  clip and then apportions across factories by worker-hours; a pool with several candidates
  per clip would let the dedupe step, rather than the apportionment, decide how many frames a
  factory of few long clips can contribute.
- **`S10k-U`** gets a frame-uniform over-sample. The corpus holds order-1e9 frames, so a
  literal frame-level pool cannot be materialised; instead clips are drawn with probability
  proportional to their frame count and given a uniform in-clip frame index, which gives every
  frame in the corpus equal selection probability. `_draw_uniform_corpus` then takes its own
  seeded subsample of that pool, so the draw's seed still does real work.
"""

from __future__ import annotations

import json
import os
import random
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Any

from vernier.models import FrameRef

CORPUS_REPO_ID = "builddotai/Egocentric-10K"
CORPUS_NAME = "egocentric-10k-raw"
MANIFEST_PATH = Path("data/corpus_manifest_10k.jsonl")

# The `S10k-U` pool is an over-sample so that `_draw_uniform_corpus`'s own seeded
# `rng.sample(pool, 10_000)` is a real random subsample rather than a permutation.
_UNIFORM_POOL_MULTIPLE = 10
_UNIFORM_POOL_TARGET = 100_000

# Whitelisting the inner protocols is mandatory: `subfile` defaults to `file` only, and an
# https URL inside it fails with "Protocol 'https' not on whitelist 'file'!".
_PROTOCOL_WHITELIST = "file,http,https,tls,tcp,crypto,subfile"
_FFMPEG_TIMEOUT_S = 180


# --------------------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------------------


def load_manifest(path: Path = MANIFEST_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} does not exist -- build it first with "
            "`python3 scripts/build_corpus_manifest.py --limit 0`"
        )
    with path.open() as handle:
        return [json.loads(line) for line in handle if line.strip()]


@lru_cache(maxsize=1)
def _manifest_cached() -> tuple[dict[str, Any], ...]:
    return tuple(load_manifest())


def factory_worker_hours_from_manifest(manifest: list[dict[str, Any]]) -> dict[str, float]:
    """`{factory_id: recorded_hours}` -- `S10k-S`'s stratification weights.

    Recorded video duration is the only worker-hours measure this corpus ships. It is not the
    same quantity as hours worked, and any claim built on it says "recorded hours".
    """
    hours: dict[str, float] = {}
    for clip in manifest:
        factory = str(clip["factory_id"])
        hours[factory] = hours.get(factory, 0.0) + float(clip["duration_sec"]) / 3600.0
    return hours


def factory_worker_hours() -> dict[str, float]:
    return factory_worker_hours_from_manifest(list(_manifest_cached()))


# --------------------------------------------------------------------------------------
# Pools
# --------------------------------------------------------------------------------------


def _n_frames(clip: dict[str, Any]) -> int:
    return int(float(clip["duration_sec"]) * float(clip["fps"]))


def qualified_worker_id(factory_id: str, worker_id: str) -> str:
    """`worker_id` that is unique across the whole corpus, not just within one factory.

    The corpus numbers workers per factory -- `worker_001` exists in every one of the 85 -- so
    the sidecar's own `worker_id` is not an identifier on its own. `models.py` states flatly
    that "worker_id is the cluster unit for every reported interval", and every consumer reads
    that single field, so the factory has to be folded into it here rather than left for each
    caller to remember. Passing the composite through `normalize_worker_id` keeps
    `docs/ARCHITECTURE.md`'s declared corpus-adapter seam as the one place this mapping lives.

    Caught by a live draw, not by review: a partial manifest yielded 37 distinct bare
    `worker_id`s across 216 real (factory, worker) pairs. Left alone it would have collapsed
    ~2,144 clusters into ~85 and inflated H2's design effect -- a number that would have looked
    like a strong positive result for the project's own central hypothesis.
    """
    from vernier.sampling.draw import normalize_worker_id

    return normalize_worker_id(CORPUS_NAME, f"{factory_id}/{worker_id}")


def _frame_ref(clip: dict[str, Any], frame_index: int, sample: str, corpus_rev: str) -> FrameRef:
    fps = float(clip["fps"])
    return FrameRef(
        frame_id=f"ego10k/{clip['clip_id']}/{frame_index:08d}",
        corpus=CORPUS_NAME,
        corpus_rev=corpus_rev,
        factory_id=str(clip["factory_id"]),
        worker_id=qualified_worker_id(str(clip["factory_id"]), str(clip["worker_id"])),
        clip_id=str(clip["clip_id"]),
        frame_index=frame_index,
        timestamp_s=frame_index / fps,
        width=int(clip["width"]),
        height=int(clip["height"]),
        fps=fps,
        codec=str(clip["codec"]),
        sample=sample,
        stratum="unstratified",
        why_no_provenance=None,
    )


def candidate_frames_from_manifest(
    manifest: list[dict[str, Any]],
    sample: str,
    *,
    corpus_rev: str,
    seed: int,
) -> list[FrameRef]:
    """The pool `draw_sample` samples from, built from an already-loaded manifest.

    Clips with fewer than one whole frame are dropped rather than special-cased: they
    contribute nothing to a frame-uniform draw, and `randrange(0)` would raise.
    """
    usable = [clip for clip in manifest if _n_frames(clip) > 0]
    rng = random.Random(f"{seed}:{sample}")

    if sample == "S10k-S":
        return [
            _frame_ref(clip, rng.randrange(_n_frames(clip)), sample, corpus_rev)
            for clip in usable
        ]

    if sample == "S10k-U":
        weights = [_n_frames(clip) for clip in usable]
        target = max(_UNIFORM_POOL_TARGET, _UNIFORM_POOL_MULTIPLE * len(usable))
        pool: list[FrameRef] = []
        seen: set[str] = set()
        for clip in rng.choices(usable, weights=weights, k=target):
            frame_index = rng.randrange(_n_frames(clip))
            frame = _frame_ref(clip, frame_index, sample, corpus_rev)
            if frame.frame_id in seen:
                continue  # same clip, same frame twice: keep the pool a set of frames
            seen.add(frame.frame_id)
            pool.append(frame)
        return pool

    raise ValueError(f"{sample!r} is not a raw-corpus sample (expected S10k-U or S10k-S)")


def candidate_frames(sample: str, *, corpus_rev: str, seed: int) -> list[FrameRef]:
    return candidate_frames_from_manifest(
        list(_manifest_cached()), sample, corpus_rev=corpus_rev, seed=seed
    )


# --------------------------------------------------------------------------------------
# Frame extraction
# --------------------------------------------------------------------------------------


def subfile_url(offset: int, size: int, url: str) -> str:
    """ffmpeg's `subfile` spec for one tar member. `end` is exclusive."""
    return f"subfile,,start,{offset},end,{offset + size},,:{url}"


def ffmpeg_extract_argv(input_url: str, timestamp_s: float) -> list[str]:
    """`-ss` goes before `-i`: that is an *input* seek, so ffmpeg consults the moov index and
    range-requests only the GOP containing the timestamp. Placed after `-i` it would decode
    from byte zero and discard, downloading the entire clip for one frame.
    """
    return [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-loglevel",
        "error",
        "-protocol_whitelist",
        _PROTOCOL_WHITELIST,
        "-seekable",
        "1",
        "-multiple_requests",
        "1",
        "-ss",
        f"{timestamp_s:.3f}",
        "-i",
        input_url,
        "-frames:v",
        "1",
        "-f",
        "image2pipe",
        "-vcodec",
        "mjpeg",
        "-q:v",
        "2",
        "-",
    ]


@lru_cache(maxsize=1)
def _clip_index() -> dict[str, dict[str, Any]]:
    return {str(clip["clip_id"]): clip for clip in _manifest_cached()}


def _resolved_shard_url(shard: str) -> str:
    from huggingface_hub import get_hf_file_metadata, hf_hub_url

    token = os.environ.get("HF_TOKEN") or None
    url = hf_hub_url(CORPUS_REPO_ID, shard, repo_type="dataset")
    return str(get_hf_file_metadata(url, token=token).location)


def image_bytes_for_corpus_frame(frame: FrameRef) -> bytes:
    """Real JPEG bytes for one `S10k-*` frame, decoded from the corpus video.

    The signed CDN URL is resolved per call rather than cached: it carries an `Expires` claim,
    and a stale one fails as a 403 that reads like a permissions error. Resolution is one small
    metadata request against a decode that fetches several MB, so it is not the cost here.
    """
    if frame.clip_id is None or frame.timestamp_s is None:
        raise ValueError(f"frame {frame.frame_id!r} has no clip provenance to extract from")
    clip = _clip_index().get(frame.clip_id)
    if clip is None:
        raise KeyError(f"clip {frame.clip_id!r} is not in {MANIFEST_PATH}")

    url = subfile_url(
        int(clip["mp4_offset"]), int(clip["mp4_size"]), _resolved_shard_url(str(clip["shard"]))
    )
    result = subprocess.run(
        ffmpeg_extract_argv(url, frame.timestamp_s),
        capture_output=True,
        timeout=_FFMPEG_TIMEOUT_S,
    )
    if not result.stdout:
        raise RuntimeError(
            f"ffmpeg produced no frame for {frame.frame_id!r} at t={frame.timestamp_s:.3f}s: "
            f"{result.stderr.decode('utf-8', 'replace')[:400]}"
        )
    return result.stdout
