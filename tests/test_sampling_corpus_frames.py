"""Behavioural tests for `vernier.sampling.corpus_frames` -- the raw Egocentric-10K adapter.

Every test here is offline. The manifest is a plain list of dicts, so the pool construction
(the part with real statistical consequences) is exercised without touching the corpus; the
ffmpeg invocation is tested as an argv-building function for the same reason.
"""

from __future__ import annotations

from typing import Any

import pytest

from vernier.sampling.corpus_frames import (
    candidate_frames_from_manifest,
    factory_worker_hours_from_manifest,
    ffmpeg_extract_argv,
    subfile_url,
)


def _clip(
    factory: str, worker: str, index: int, duration: float, fps: float = 30.0
) -> dict[str, Any]:
    return {
        "shard": f"{factory}/workers/{worker}/{factory}_{worker}_part{index:02d}.tar",
        "clip_id": f"{factory}_{worker}_{index:05d}",
        "factory_id": factory,
        "worker_id": worker,
        "video_index": index,
        "duration_sec": duration,
        "fps": fps,
        "width": 1920,
        "height": 1080,
        "codec": "h265",
        "mp4_offset": 512,
        "mp4_size": 1_000_000,
    }


_MANIFEST = [
    _clip("factory_001", "worker_001", 0, 180.0),
    _clip("factory_001", "worker_002", 1, 1200.0),
    _clip("factory_002", "worker_001", 2, 433.4),
]


# --- S10k-S: one candidate per clip ---------------------------------------------------


def test_stratified_pool_has_exactly_one_candidate_per_clip() -> None:
    """`_draw_stratified_corpus` dedupes to <=1 frame per clip and then apportions across
    factories by worker-hours. Handing it more than one candidate per clip would let a factory
    of few long clips be starved by the dedupe step rather than by its apportionment, so the
    pool is built at clip granularity to begin with."""
    pool = candidate_frames_from_manifest(_MANIFEST, "S10k-S", corpus_rev="abc123", seed=777)

    assert len(pool) == len(_MANIFEST)
    assert sorted(f.clip_id or "" for f in pool) == sorted(c["clip_id"] for c in _MANIFEST)


def test_every_corpus_frame_carries_full_provenance() -> None:
    """`FrameRef`'s null-together validator is what makes H2 possible at all: these frames are
    the only ones in the project with a real `worker_id`."""
    pool = candidate_frames_from_manifest(_MANIFEST, "S10k-S", corpus_rev="abc123", seed=777)

    for frame in pool:
        assert frame.factory_id is not None
        assert frame.worker_id is not None
        assert frame.clip_id is not None
        assert frame.timestamp_s is not None
        assert frame.fps is not None
        assert frame.codec == "h265"
        assert frame.why_no_provenance is None
        assert frame.corpus_rev == "abc123"


def test_timestamp_and_frame_index_agree_and_stay_inside_the_clip() -> None:
    """Neither `timestamp_s` nor `frame_index` exists in the raw data (D065) -- both are
    constructed here, so their consistency is a property of this module, not of the corpus."""
    pool = candidate_frames_from_manifest(_MANIFEST, "S10k-S", corpus_rev="abc123", seed=777)
    by_clip = {c["clip_id"]: c for c in _MANIFEST}

    for frame in pool:
        clip = by_clip[frame.clip_id or ""]
        assert frame.timestamp_s is not None and frame.fps is not None
        assert frame.timestamp_s == pytest.approx(frame.frame_index / frame.fps)
        assert 0.0 <= frame.timestamp_s < clip["duration_sec"]


# --- S10k-U: uniform over FRAMES, not over clips --------------------------------------


def test_uniform_pool_is_frame_uniform_not_clip_uniform() -> None:
    """The pre-registration says `S10k-U` is uniform over *frames*. One candidate per clip
    would silently make it uniform over *clips*, which over-weights short clips by the ratio of
    their lengths -- in the real corpus, a 180s clip against a 1200s one, a 6.7x error on the
    design effect's own denominator.

    Two clips, 100:1 in length. A frame-uniform pool lands ~99% of its mass on the long one.
    """
    manifest = [
        _clip("factory_001", "worker_001", 0, 10.0),
        _clip("factory_001", "worker_002", 1, 1000.0),
    ]

    pool = candidate_frames_from_manifest(manifest, "S10k-U", corpus_rev="abc", seed=777)

    long_share = sum(1 for f in pool if f.worker_id == "factory_001/worker_002") / len(pool)
    assert 0.97 < long_share < 1.0  # clip-uniform would be exactly 0.5


def test_uniform_pool_is_larger_than_the_draw_it_feeds() -> None:
    """`_draw_uniform_corpus` takes a seeded `rng.sample(pool, 10_000)`. If the pool were
    exactly 10,000 the "draw" would be a permutation and the seed would stop mattering, so the
    pool is deliberately an over-sample that a real random subsample is then taken from."""
    pool = candidate_frames_from_manifest(_MANIFEST, "S10k-U", corpus_rev="abc", seed=777)

    assert len(pool) > 10_000


def test_pool_construction_is_deterministic_under_a_fixed_seed() -> None:
    first = candidate_frames_from_manifest(_MANIFEST, "S10k-U", corpus_rev="abc", seed=777)
    second = candidate_frames_from_manifest(_MANIFEST, "S10k-U", corpus_rev="abc", seed=777)
    other = candidate_frames_from_manifest(_MANIFEST, "S10k-U", corpus_rev="abc", seed=778)

    assert [f.frame_id for f in first] == [f.frame_id for f in second]
    assert [f.frame_id for f in first] != [f.frame_id for f in other]


def test_frame_ids_are_unique_within_a_pool() -> None:
    pool = candidate_frames_from_manifest(_MANIFEST, "S10k-U", corpus_rev="abc", seed=777)

    assert len({f.frame_id for f in pool}) == len(pool)


def test_a_clip_shorter_than_one_frame_is_skipped() -> None:
    """`int(duration * fps)` is 0 for a truncated clip; drawing `randrange(0)` would raise.
    Dropping it is correct -- it contributes no frames to a frame-uniform draw either."""
    manifest = [
        _clip("factory_001", "worker_001", 0, 0.0),
        _clip("factory_001", "worker_002", 1, 60.0),
    ]

    pool = candidate_frames_from_manifest(manifest, "S10k-S", corpus_rev="abc", seed=777)

    assert [f.worker_id for f in pool] == ["factory_001/worker_002"]


def test_worker_id_is_globally_unique_not_just_within_a_factory() -> None:
    """The corpus numbers workers per factory: `worker_001` exists in all 85 of them. Caught
    live -- a partial manifest held 37 distinct bare `worker_id`s across 216 real
    (factory, worker) pairs.

    `models.py`: "worker_id is the cluster unit for every reported interval." Anything reading
    `frame.worker_id` on its own -- which is every consumer, by that contract -- would have
    pooled 85 different people into one cluster and inflated H2's design effect by collapsing
    ~2,144 clusters into ~85.
    """
    manifest = [
        _clip("factory_001", "worker_001", 0, 60.0),
        _clip("factory_002", "worker_001", 0, 60.0),
    ]

    pool = candidate_frames_from_manifest(manifest, "S10k-S", corpus_rev="abc", seed=777)

    assert len({f.worker_id for f in pool}) == 2
    # factory_id stays unqualified -- S10k-S stratifies on it.
    assert {f.factory_id for f in pool} == {"factory_001", "factory_002"}


# --- worker-hours ---------------------------------------------------------------------


def test_factory_worker_hours_sums_recorded_duration_per_factory() -> None:
    """Golden case, hand-computable: 1800 + 1800 seconds is exactly 1.0 hour, 900 is 0.25."""
    manifest = [
        _clip("factory_001", "worker_001", 0, 1800.0),
        _clip("factory_001", "worker_002", 1, 1800.0),
        _clip("factory_002", "worker_001", 2, 900.0),
    ]

    assert factory_worker_hours_from_manifest(manifest) == {
        "factory_001": 1.0,
        "factory_002": 0.25,
    }


# --- ffmpeg invocation ----------------------------------------------------------------


def test_subfile_url_spans_exactly_the_mp4_member() -> None:
    """`end` is exclusive in ffmpeg's `subfile` protocol. Off by one and the decoder either
    truncates the final packet or reads a tar header as video."""
    assert (
        subfile_url(512, 1000, "https://cdn/x.tar")
        == "subfile,,start,512,end,1512,,:https://cdn/x.tar"
    )


def test_ffmpeg_argv_seeks_before_the_input() -> None:
    """`-ss` before `-i` is an input seek: ffmpeg jumps to the nearest keyframe using the moov
    index and range-requests only that region. After `-i` it decodes from the start of the
    file and discards, which over a 1200-second clip means downloading the whole thing."""
    argv = ffmpeg_extract_argv("subfile,,start,512,end,1512,,:https://cdn/x.tar", 250.0)

    assert argv[0] == "ffmpeg"
    assert argv.index("-ss") < argv.index("-i")
    assert argv[argv.index("-ss") + 1] == "250.000"
    assert argv[argv.index("-i") + 1] == "subfile,,start,512,end,1512,,:https://cdn/x.tar"
    # The inner protocol whitelist: without it ffmpeg refuses https inside subfile with
    # "Protocol 'https' not on whitelist 'file'!" -- a real error hit while sizing this.
    assert "https" in argv[argv.index("-protocol_whitelist") + 1]
    assert argv[-1] == "-"
