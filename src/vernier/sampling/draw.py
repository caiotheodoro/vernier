"""Draws every sample fixed in ``docs/PRE-REGISTRATION.md``. Emits `FrameRef` records.

Owns: seed handling, stratification, the <=1-frame-per-clip constraint, and the `worker_id`
cluster assignment every downstream interval depends on. Depends on: the HF dataset metadata
only -- it never decodes a frame it was not asked for.

Seam: corpus-specific identifier mapping. Ego4D and EPIC-KITCHENS-100 name their participant
field differently; `normalize_worker_id` normalises into `worker_id` and records the original
in `corpus`.

Wave 1 was offline by design: stratification, the worker-hours weighting, the per-clip cap,
seeded determinism, the P2k/G200/R100 subset relationships, and the revision-pin check are all
real and unit-tested against synthetic pools, independent of `_candidate_frames`'s own wiring.

`_candidate_frames` is now real for the `E10k-*` evaluation-release arms (`docs/DECISIONS.md`
D043's follow-on): the actual HF repo (`builddotai/Egocentric-10K-Evaluation`) ships one
parquet file per sub-corpus, not one file filtered by a column (verified live via
`HfApi().list_repo_files` -- `_EVAL_PARQUET_FILENAME` records the real mapping).
`_frames_from_eval_parquet` is the offline-testable half (a local parquet path in, a `FrameRef`
pool out); `_candidate_frames` itself is the thin real-network wrapper
(`huggingface_hub.hf_hub_download`) around it. `S10k-U`/`S10k-S` (the raw, contact-gated
Egocentric-10K corpus, with real factory/worker/clip/timestamp/fps/codec) and
`_factory_worker_hours` remain unwired -- a different, still-ungated-in-this-repo dataset whose
real schema hasn't been inspected yet.
"""

from __future__ import annotations

import io
import random
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pyarrow.parquet as pq
from PIL import Image

from vernier.models import FrameRef
from vernier.sampling.revisions import PINNED_REVISIONS, assert_pinned_revision

SampleName = Literal[
    "E10k-ego",
    "E10k-ego4d",
    "E10k-epic",
    "S10k-U",
    "S10k-S",
    "P2k",
    "G200-ego",
    "G200-ego4d",
    "G200-epic",
    "R100",
]

PRE_REGISTRATION_SEED = 777

# docs/PRE-REGISTRATION.md "Samples" table.
_N: dict[SampleName, int] = {
    "E10k-ego": 10_000,
    "E10k-ego4d": 10_000,
    "E10k-epic": 10_000,
    "S10k-U": 10_000,
    "S10k-S": 10_000,
    "P2k": 2_000,
    "G200-ego": 200,
    "G200-ego4d": 200,
    "G200-epic": 200,
    "R100": 100,
}

# Every sample here is a random subset of exactly one other, already-drawn sample's membership
# (docs/PRE-REGISTRATION.md "Samples" table). R100 is the one exception -- a subset of the
# *union* of three parents -- and is handled separately below.
_PARENT: dict[SampleName, SampleName] = {
    "P2k": "E10k-ego",
    "G200-ego": "P2k",
    "G200-ego4d": "E10k-ego4d",
    "G200-epic": "E10k-epic",
}

_R100_PARENTS: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")

# docs/UPSTREAM-FINDINGS.md F5 / sampling/revisions.py: the evaluation release redistributes
# the Ego4D and EPIC-KITCHENS-100 frames directly, so this one HF repo id covers every corpus
# arm `draw_sample` draws from -- there is (so far) exactly one entry in `PINNED_REVISIONS`.
_EVAL_HF_REPO = "builddotai/Egocentric-10K-Evaluation"

# Where a subset sample's parent membership is read from. `write_membership`/`load_membership`
# take an explicit `path` (sampling/membership.py); `draw_sample`'s signature is frozen with no
# room for one, so this fixes a convention for the parent-membership lookup a subset draw needs.
# Reviewer note: this is this unit's own choice, not one taken from an existing convention
# elsewhere in the repo -- the real on-disk layout is an orchestration concern Wave 2 may need
# to revisit.
_MEMBERSHIP_ROOT = Path("data/membership")


def _rng(seed: int, sample: SampleName) -> random.Random:
    """One independent, deterministic RNG stream per (seed, sample) pair."""
    return random.Random(f"{seed}:{sample}")


# Each `E10k-*` sample draws from its own file within the one pinned evaluation-release repo
# (`_EVAL_HF_REPO`) -- confirmed live via `HfApi().list_repo_files`, not assumed from the
# single-file example `docs/UPSTREAM-FINDINGS.md` F9 happened to inspect.
_EVAL_PARQUET_FILENAME: dict[str, str] = {
    "E10k-ego": "egocentric_10k.parquet",
    "E10k-ego4d": "ego4d.parquet",
    "E10k-epic": "epic_kitchens.parquet",
}

# Every E10k-* frame is null-together on the same six fields for the same reason (F9/D040): a
# bare-UUID4 evaluation release with no factory/worker/clip/timestamp/fps/codec at all.
_EVAL_ARM_WHY_NO_PROVENANCE = (
    "Build AI's evaluation parquet ships frame_id as a bare UUID4 with no factory, worker, "
    "clip, or timestamp component, and no source-video fps/codec at all "
    "(docs/UPSTREAM-FINDINGS.md F9, docs/DECISIONS.md D040)"
)


def _decode_dimensions(image_bytes: bytes) -> tuple[int, int]:
    """Real width/height for one frame's JPEG bytes. The parquet carries neither (F9's schema
    is `frame_id`/`image`/`source_dataset`/`hand_count`/`active_labor` only), but `FrameRef`
    requires both regardless of provenance -- they're always recoverable from the image itself.
    """
    with Image.open(io.BytesIO(image_bytes)) as img:
        return img.width, img.height


def _frames_from_eval_parquet(path: str, sample: SampleName, corpus_rev: str) -> list[FrameRef]:
    """Read one already-local evaluation parquet and build its `FrameRef` pool.

    Offline-testable against a synthetic local parquet (see `tests/test_sampling_draw.py`) --
    `_candidate_frames` is the thin real-network wrapper around this, so the network/HF part
    stays untested-by-unit-test the same way every other real-I/O seam in this project is.

    A frame with empty/absent image bytes is silently excluded from the pool, not raised on --
    `scripts/check_eval_parquets.py` (D016) is the dedicated, explicit check for exactly that
    absence against a drawn sample's membership; this function's job is only to build a pool of
    frames that are actually usable.

    `corpus="egocentric-10k"` for every `E10k-*` arm, not a per-sub-corpus value: it names the
    one published collection all three files come from, matching the existing, reviewed
    `FrameRef__eval_arm_no_provenance` fixture -- `sample` (`E10k-ego`/`E10k-ego4d`/`E10k-epic`)
    already carries the actual sub-corpus distinction machine-readably, so `corpus` doesn't
    need to duplicate it. Flagged here as a judgment call, not a pinned convention found
    elsewhere.
    """
    table = pq.read_table(path, columns=["frame_id", "image"])
    frame_ids = table.column("frame_id").to_pylist()
    images = table.column("image").to_pylist()

    frames: list[FrameRef] = []
    for frame_index, (frame_id, image) in enumerate(zip(frame_ids, images, strict=True)):
        image_bytes = image.get("bytes") if isinstance(image, dict) else None
        if not image_bytes:
            continue
        width, height = _decode_dimensions(image_bytes)
        frames.append(
            FrameRef(
                frame_id=frame_id,
                corpus="egocentric-10k",
                corpus_rev=corpus_rev,
                factory_id=None,
                worker_id=None,
                clip_id=None,
                frame_index=frame_index,
                timestamp_s=None,
                width=width,
                height=height,
                fps=None,
                codec=None,
                sample=sample,
                stratum="unstratified",
                why_no_provenance=_EVAL_ARM_WHY_NO_PROVENANCE,
            )
        )
    return frames


def _download_eval_parquet(sample: str) -> str:
    """Real network I/O, shared by `_candidate_frames` and `image_bytes_for`: resolve one
    E10k-* sample's own evaluation-release file to a local path, downloading and caching it if
    needed (`huggingface_hub` dedupes by content hash -- a second call for the same sample in
    the same process/machine is a cache hit, not a re-download).

    Raises `NotImplementedError` for `S10k-U`/`S10k-S`: a different, contact-gated dataset whose
    real schema hasn't been inspected yet.
    """
    if sample not in _EVAL_PARQUET_FILENAME:
        raise NotImplementedError(
            f"{sample!r} needs the raw Egocentric-10K corpus adapter (S10k-U/S10k-S) -- a "
            "different, still-unwired dataset, see docs/HANDOFF.md"
        )
    from huggingface_hub import hf_hub_download

    return hf_hub_download(
        repo_id=_EVAL_HF_REPO,
        repo_type="dataset",
        revision=PINNED_REVISIONS[_EVAL_HF_REPO],
        filename=_EVAL_PARQUET_FILENAME[sample],
    )


def _candidate_frames(sample: SampleName) -> list[FrameRef]:
    """Wave 2 seam: the pool `draw_sample` samples from.

    Real for the `E10k-*` family (Build AI's evaluation-release frame list) -- see
    `_frames_from_eval_parquet` for the actual parsing. `S10k-U`/`S10k-S` (fresh Egocentric-10K
    corpus metadata) remain unwired: a different, contact-gated dataset whose real schema
    hasn't been inspected yet. Wave 1 unit tests monkeypatch this whole function with
    synthetic in-memory `FrameRef` pools, independent of either path.
    """
    path = _download_eval_parquet(sample)
    return _frames_from_eval_parquet(path, sample, PINNED_REVISIONS[_EVAL_HF_REPO])


@lru_cache(maxsize=None)
def _eval_frame_bytes_by_id(sample: str) -> dict[str, bytes]:
    """Real, process-cached `frame_id -> image bytes` lookup for one E10k-* sample's
    evaluation parquet, built once per (process, sample) and reused.

    `_candidate_frames` already reads and discards the whole `image` column per draw; this is
    the separate, deliberate seam for actually judging a frame (`image_bytes_for` below) --
    without the cache, a real judging run (two calls per frame, many frames) would re-read a
    file up to ~1.8GB from disk on every single call.
    """
    path = _download_eval_parquet(sample)
    table = pq.read_table(path, columns=["frame_id", "image"])
    frame_ids = table.column("frame_id").to_pylist()
    images = table.column("image").to_pylist()
    result: dict[str, bytes] = {}
    for frame_id, image in zip(frame_ids, images, strict=True):
        image_bytes = image.get("bytes") if isinstance(image, dict) else None
        if image_bytes:
            result[frame_id] = image_bytes
    return result


def image_bytes_for(frame: FrameRef) -> bytes:
    """Real JPEG bytes for one already-drawn frame -- the seam `judges/qwen3vl.py`'s
    `_image_bytes_for` and `labels/tool.py`'s labelling CLI both call (`ARCHITECTURE.md`:
    both depend on sampling for frames, nothing else).

    Searches all three evaluation-release files by `frame_id`, NOT by `frame.sample`: a
    real bug, caught live (a real `G200-ego4d` frame from `next_frame()` 404'd here before this
    fix) -- subset samples (`P2k`, `G200-*`, `R100`) relabel `sample` to their own name
    (`_draw_subset`/`_draw_r100`'s `model_copy`) without preserving which root `E10k-*` arm a
    frame originally came from, and `R100` in particular draws from the *union* of three
    different root arms, so `frame.sample` alone can never disambiguate which file to search.
    `frame_id` (a UUID4) is unique across the whole release, so it is the only reliable key.

    `S10k-U`/`S10k-S` frames get their own explicit `NotImplementedError` (a different,
    unwired dataset), not folded into the same "not found" path as a real missing frame.

    Raises `KeyError` if `frame.frame_id` isn't present or has empty image bytes in ANY of the
    three evaluation parquets. `scripts/check_eval_parquets.py` (D016) is the place to check
    this in bulk, ahead of time, across a whole drawn sample's membership; this seam trusts that
    check already passed and fails loud, not silently, if it didn't.
    """
    if frame.sample in ("S10k-U", "S10k-S"):
        raise NotImplementedError(
            f"image_bytes_for for sample {frame.sample!r} needs the raw Egocentric-10K corpus "
            "adapter -- a different, still-unwired dataset, see docs/HANDOFF.md"
        )
    for root_sample in _EVAL_PARQUET_FILENAME:
        by_id = _eval_frame_bytes_by_id(root_sample)
        if frame.frame_id in by_id:
            return by_id[frame.frame_id]
    raise KeyError(
        f"frame_id {frame.frame_id!r} not found or has empty image bytes in any evaluation "
        "parquet"
    )


def _factory_worker_hours(sample: SampleName) -> dict[str, float]:
    """Wave 2 seam: per-factory worker-hours used to weight `S10k-S`'s stratification.

    Not a `FrameRef` field -- Build AI's corpus metadata carries factory worker-hours
    separately from any single frame, so this is its own seam alongside `_candidate_frames`.
    Returns ``{factory_id: worker_hours}``. Real wiring is Wave 2's job.
    """
    raise NotImplementedError


def _apportion(weights: dict[str, float], total: int) -> dict[str, int]:
    """Largest-remainder apportionment of `total` units across `weights`, proportional to
    each key's weight. Deterministic tie-break: remainder units go to the largest fractional
    remainder first, ties broken by key so the result never depends on dict iteration order.
    """
    result = {k: 0 for k in weights}
    total_weight = sum(weights.values())
    if total <= 0 or total_weight <= 0:
        return result
    exact = {k: w / total_weight * total for k, w in weights.items()}
    floors = {k: int(v) for k, v in exact.items()}
    remainder = total - sum(floors.values())
    order = sorted(weights.keys(), key=lambda k: (-(exact[k] - floors[k]), k))
    for k in order[:remainder]:
        floors[k] += 1
    return floors


def _check_revision(sample: SampleName, frames: list[FrameRef]) -> None:
    """Enforce the HF revision pin against every distinct `corpus_rev` in `frames`."""
    revs = sorted({f.corpus_rev for f in frames})
    for rev in revs:
        assert_pinned_revision(_EVAL_HF_REPO, rev)


def _draw_uniform_corpus(sample: SampleName, seed: int) -> list[FrameRef]:
    pool = _candidate_frames(sample)
    n = min(_N[sample], len(pool))
    chosen = _rng(seed, sample).sample(pool, n)
    return [f.model_copy(update={"sample": sample, "stratum": "unstratified"}) for f in chosen]


def _draw_stratified_corpus(sample: SampleName, seed: int) -> list[FrameRef]:
    pool = _candidate_frames(sample)
    weights = _factory_worker_hours(sample)
    rng = _rng(seed, sample)

    by_factory: dict[str, list[FrameRef]] = {}
    for f in pool:
        assert f.factory_id is not None, "S10k-S draws from full-provenance corpus metadata"
        by_factory.setdefault(f.factory_id, []).append(f)

    # <=1 frame per clip, chosen deterministically (rng.choice, seeded) per clip.
    deduped: dict[str, list[FrameRef]] = {}
    for factory_id, frames in by_factory.items():
        by_clip: dict[str, list[FrameRef]] = {}
        for f in frames:
            assert f.clip_id is not None, "S10k-S draws from full-provenance corpus metadata"
            by_clip.setdefault(f.clip_id, []).append(f)
        deduped[factory_id] = [rng.choice(cf) for _, cf in sorted(by_clip.items())]

    total_available = sum(len(v) for v in deduped.values())
    n_target = min(_N[sample], total_available)
    alloc = _apportion({k: weights.get(k, 0.0) for k in deduped}, n_target)

    result: list[FrameRef] = []
    for factory_id, frames in deduped.items():
        k = min(alloc.get(factory_id, 0), len(frames))
        chosen = rng.sample(frames, k)
        result.extend(
            f.model_copy(update={"sample": sample, "stratum": f"factory-{factory_id}"})
            for f in chosen
        )
    return result


def _draw_evaluation_release(sample: SampleName) -> list[FrameRef]:
    # "Essentially all of them" -- not a fresh draw, so no RNG. Sorted by frame_id so the
    # result is deterministic regardless of the upstream pool's own ordering.
    pool = sorted(_candidate_frames(sample), key=lambda f: f.frame_id)
    n = min(_N[sample], len(pool))
    return [f.model_copy(update={"sample": sample}) for f in pool[:n]]


def _load_parent_membership(parent: SampleName) -> list[FrameRef]:
    # Local import: `membership.py` imports `SampleName` from this module at module scope, so
    # importing `membership` back at this module's top level would be circular. Deferred to
    # call time, by which point both modules are fully loaded.
    from vernier.sampling import membership

    # `load_membership(sample, path)` takes the membership ROOT DIRECTORY and appends
    # `<sample>.json` itself (`membership.py`'s own `_member_path`) -- passing a pre-built file
    # path here (the bug this comment replaces: `_membership_path(parent)`, itself already
    # `_MEMBERSHIP_ROOT / f"{parent}.json"`) made every subset draw look for
    # `data/membership/<parent>.json/<parent>.json`, silently never found. Caught only by
    # actually running `scripts/draw_all_samples.py` end to end against real written
    # membership -- every existing test monkeypatches `membership.load_membership` directly,
    # bypassing this call entirely, so nothing here had ever exercised the real path arithmetic.
    return membership.load_membership(parent, _MEMBERSHIP_ROOT)


def _draw_subset(sample: SampleName, seed: int) -> list[FrameRef]:
    parent = _PARENT[sample]
    pool = _load_parent_membership(parent)
    n = min(_N[sample], len(pool))
    chosen = _rng(seed, sample).sample(pool, n)
    return [f.model_copy(update={"sample": sample}) for f in chosen]


def _draw_r100(seed: int) -> list[FrameRef]:
    union = [f for parent in _R100_PARENTS for f in _load_parent_membership(parent)]
    n = min(_N["R100"], len(union))
    chosen = _rng(seed, "R100").sample(union, n)
    return [f.model_copy(update={"sample": "R100"}) for f in chosen]


def draw_sample(sample: SampleName, *, seed: int = PRE_REGISTRATION_SEED) -> list[FrameRef]:
    """Draw the named sample per its definition in `docs/PRE-REGISTRATION.md`.

    Must be called at most once per `sample` for the life of a run: membership is fixed at
    draw time and is never redrawn.
    """
    if sample == "S10k-U":
        frames = _draw_uniform_corpus(sample, seed)
    elif sample == "S10k-S":
        frames = _draw_stratified_corpus(sample, seed)
    elif sample in ("E10k-ego", "E10k-ego4d", "E10k-epic"):
        frames = _draw_evaluation_release(sample)
    elif sample == "R100":
        frames = _draw_r100(seed)
    else:
        frames = _draw_subset(sample, seed)

    _check_revision(sample, frames)
    return frames


def normalize_worker_id(corpus: str, raw_participant_field: str) -> str:
    """The corpus-adapter seam: map a corpus's native participant identifier to `worker_id`.

    TODO(Wave 2): Ego4D and EPIC-KITCHENS-100 name their participant field differently
    (docs/ARCHITECTURE.md's stated seam), but the exact upstream field names are not yet
    inspected anywhere in this repo (`docs/UPSTREAM-FINDINGS.md` documents the evaluation
    parquet schema, F9, but not the raw corpus-side participant field naming). Rather than
    guess a mapping and assert it is correct, this is the identity mapping for every corpus
    until that inspection happens: the caller's raw participant string is returned unchanged,
    and `corpus` disambiguates it downstream, exactly as `CONTRACTS.md` describes ("recorded
    in the same field with corpus disambiguating it").
    """
    return raw_participant_field
