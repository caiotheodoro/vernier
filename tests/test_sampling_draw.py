"""Behavioural tests for `draw_sample`/`normalize_worker_id`.

`_candidate_frames` (the Wave 2 HF/parquet seam) and, where a sample is a subset of an
already-drawn sample, `vernier.sampling.membership.load_membership` are monkeypatched to
supply synthetic in-memory `FrameRef` pools -- this unit is offline by design and must not
touch the network or any real corpus file.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest

from vernier.models import FrameRef
from vernier.sampling import draw as draw_mod
from vernier.sampling import membership as membership_mod
from vernier.sampling.draw import (
    _EVAL_ARM_WHY_NO_PROVENANCE,
    PRE_REGISTRATION_SEED,
    draw_sample,
    normalize_worker_id,
)
from vernier.sampling.revisions import PINNED_REVISIONS

EVAL_REPO = "builddotai/Egocentric-10K-Evaluation"
PINNED_REV = PINNED_REVISIONS[EVAL_REPO]
EVAL_REPO_100K = "builddotai/Egocentric-100K-Evaluation"
PINNED_REV_100K = PINNED_REVISIONS[EVAL_REPO_100K]


def _corpus_frame(
    *,
    factory_id: str,
    worker_id: str,
    clip_id: str,
    frame_index: int,
    corpus_rev: str = PINNED_REV,
) -> FrameRef:
    return FrameRef(
        frame_id=f"ego10k/f{factory_id}/w{worker_id}/v{clip_id}/{frame_index:06d}",
        corpus="egocentric-10k",
        corpus_rev=corpus_rev,
        factory_id=factory_id,
        worker_id=worker_id,
        clip_id=clip_id,
        frame_index=frame_index,
        timestamp_s=float(frame_index),
        width=1920,
        height=1080,
        fps=30.0,
        codec="hevc",
        sample="S10k-U",
        stratum="unstratified",
        why_no_provenance=None,
    )


def _eval_frame(
    *,
    sample: str,
    uid: str,
    corpus: str = "egocentric-10k",
    corpus_rev: str = PINNED_REV,
) -> FrameRef:
    return FrameRef(
        frame_id=f"uuid-{uid}",
        corpus=corpus,
        corpus_rev=corpus_rev,
        factory_id=None,
        worker_id=None,
        clip_id=None,
        frame_index=0,
        timestamp_s=None,
        width=1920,
        height=1080,
        fps=None,
        codec=None,
        sample=sample,
        stratum="unstratified",
        why_no_provenance="bare UUID4 frame_id, no provenance columns, no source-video fps/codec (F9, D040)",
    )


# --- determinism / idempotence -------------------------------------------------------------


def test_draw_sample_is_deterministic_for_same_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="1", worker_id=f"w{i}", clip_id=f"c{i}", frame_index=i)
        for i in range(50)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    first = draw_sample("S10k-U", seed=777)
    second = draw_sample("S10k-U", seed=777)

    assert [f.frame_id for f in first] == [f.frame_id for f in second]


def test_draw_sample_different_seeds_can_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="1", worker_id=f"w{i}", clip_id=f"c{i}", frame_index=i)
        for i in range(50)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    a = draw_sample("S10k-U", seed=1)
    b = draw_sample("S10k-U", seed=2)

    assert [f.frame_id for f in a] != [f.frame_id for f in b]


# --- S10k-U ----------------------------------------------------------------------------------


def test_s10k_u_draws_uniformly_from_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="1", worker_id=f"w{i}", clip_id=f"c{i}", frame_index=i)
        for i in range(20)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    frames = draw_sample("S10k-U", seed=PRE_REGISTRATION_SEED)

    assert len(frames) == 20
    assert {f.frame_id for f in frames} == {f.frame_id for f in pool}
    assert all(f.sample == "S10k-U" for f in frames)


def test_s10k_u_caps_at_registered_n(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="1", worker_id=f"w{i}", clip_id=f"c{i}", frame_index=i)
        for i in range(50)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    frames = draw_sample("S10k-U", seed=PRE_REGISTRATION_SEED)

    # pool has 50 frames; the pre-registered n for S10k-U is 10,000, so every candidate frame
    # is used, but never more than the pool actually holds.
    assert len(frames) == len(pool)
    assert len(frames) == len({f.frame_id for f in frames})


# --- S10k-S: <=1-frame-per-clip -----------------------------------------------------------


def test_s10k_s_respects_one_frame_per_clip(monkeypatch: pytest.MonkeyPatch) -> None:
    # Two clips, each with several frames -- the constraint must pick at most one per clip.
    pool = [
        _corpus_frame(factory_id="1", worker_id="w1", clip_id="clipA", frame_index=i)
        for i in range(5)
    ] + [
        _corpus_frame(factory_id="1", worker_id="w2", clip_id="clipB", frame_index=i)
        for i in range(5)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))
    monkeypatch.setattr(draw_mod, "_factory_worker_hours", lambda sample: {"1": 10.0})

    frames = draw_sample("S10k-S", seed=PRE_REGISTRATION_SEED)

    clip_ids = [f.clip_id for f in frames]
    assert len(clip_ids) == len(set(clip_ids))
    assert set(clip_ids) == {"clipA", "clipB"}


# --- S10k-S: worker-hours-proportional stratification, golden case -------------------------


def test_s10k_s_factory_allocation_proportional_to_worker_hours(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Factory "A" gets 3x the worker-hours of factory "B" -> should get 3x the frames, out of
    # a hand-computable total of 40 (so the split is exactly 30 / 10, no rounding ambiguity).
    # Factory A supplies exactly 30 distinct clips and B exactly 10, so the per-clip cap never
    # binds and the full weight-proportional allocation is achievable; the pool (40 frames
    # total) is smaller than the registered n=10,000, so the implementation draws exactly what
    # the pool holds.
    pool = [
        _corpus_frame(factory_id="A", worker_id=f"wA{i}", clip_id=f"cA{i}", frame_index=i)
        for i in range(30)
    ] + [
        _corpus_frame(factory_id="B", worker_id=f"wB{i}", clip_id=f"cB{i}", frame_index=i)
        for i in range(10)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))
    monkeypatch.setattr(
        draw_mod, "_factory_worker_hours", lambda sample: {"A": 30.0, "B": 10.0}
    )

    frames = draw_sample("S10k-S", seed=PRE_REGISTRATION_SEED)

    by_factory: dict[str, int] = {}
    for f in frames:
        assert f.factory_id is not None
        by_factory[f.factory_id] = by_factory.get(f.factory_id, 0) + 1

    assert len(frames) == 40
    assert by_factory == {"A": 30, "B": 10}


def test_s10k_s_stratum_labels_factory(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="A", worker_id=f"wA{i}", clip_id=f"cA{i}", frame_index=i)
        for i in range(10)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))
    monkeypatch.setattr(draw_mod, "_factory_worker_hours", lambda sample: {"A": 1.0})

    frames = draw_sample("S10k-S", seed=PRE_REGISTRATION_SEED)

    assert all(f.stratum == "factory-A" for f in frames)
    assert all(f.sample == "S10k-S" for f in frames)


# --- E10k-* evaluation-release arms ---------------------------------------------------------


def test_e10k_ego_is_essentially_all_candidate_frames(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [_eval_frame(sample="E10k-ego", uid=str(i)) for i in range(15)]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    frames = draw_sample("E10k-ego", seed=PRE_REGISTRATION_SEED)

    assert {f.frame_id for f in frames} == {f.frame_id for f in pool}
    assert all(f.sample == "E10k-ego" for f in frames)
    assert all(f.why_no_provenance is not None for f in frames)


# --- subset relationships: P2k / G200-* / R100 ----------------------------------------------


def test_load_parent_membership_passes_the_root_directory_not_a_file_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard for a real bug (`docs/DECISIONS.md` D045): `_load_parent_membership`
    used to pass a pre-built `<root>/<sample>.json` file path where `load_membership(sample,
    path)` expects the root *directory* (it appends `<sample>.json` itself) -- silently never
    finding any real, on-disk membership. Every other test here monkeypatches
    `load_membership` without checking its `path` argument at all, which is exactly how this
    survived undetected until a real end-to-end run (`scripts/draw_all_samples.py`) hit it."""
    received_paths: list[object] = []

    def _spy(sample: str, path: object) -> list[FrameRef]:
        received_paths.append(path)
        return []

    monkeypatch.setattr(membership_mod, "load_membership", _spy)

    draw_mod._load_parent_membership("E10k-ego")

    assert received_paths == [draw_mod._MEMBERSHIP_ROOT]


def test_p2k_is_subset_of_e10k_ego_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    parent = [_eval_frame(sample="E10k-ego", uid=str(i)) for i in range(30)]
    monkeypatch.setattr(
        draw_mod,
        "_candidate_frames",
        lambda sample: (_ for _ in ()).throw(AssertionError("P2k must not hit the corpus seam")),
    )
    monkeypatch.setattr(
        membership_mod,
        "load_membership",
        lambda sample, path: list(parent) if sample == "E10k-ego" else [],
    )

    frames = draw_sample("P2k", seed=PRE_REGISTRATION_SEED)

    parent_ids = {f.frame_id for f in parent}
    assert len(frames) == len(parent)  # pool has fewer than the registered n=2000
    assert {f.frame_id for f in frames} <= parent_ids
    assert all(f.sample == "P2k" for f in frames)


def test_g200_ego_is_subset_of_p2k_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    p2k = [_eval_frame(sample="P2k", uid=str(i)) for i in range(50)]
    monkeypatch.setattr(
        membership_mod,
        "load_membership",
        lambda sample, path: list(p2k) if sample == "P2k" else [],
    )

    frames = draw_sample("G200-ego", seed=PRE_REGISTRATION_SEED)

    p2k_ids = {f.frame_id for f in p2k}
    assert len(frames) == 50  # pool smaller than registered n=200: take all of it
    assert {f.frame_id for f in frames} <= p2k_ids
    assert all(f.sample == "G200-ego" for f in frames)


def test_r100_is_subset_of_union_of_three_g200_sets(monkeypatch: pytest.MonkeyPatch) -> None:
    g_ego = [_eval_frame(sample="G200-ego", uid=f"ego{i}") for i in range(20)]
    g_ego4d = [_eval_frame(sample="G200-ego4d", uid=f"e4d{i}") for i in range(20)]
    g_epic = [_eval_frame(sample="G200-epic", uid=f"epic{i}") for i in range(20)]
    pools = {
        "G200-ego": g_ego,
        "G200-ego4d": g_ego4d,
        "G200-epic": g_epic,
    }
    monkeypatch.setattr(membership_mod, "load_membership", lambda sample, path: list(pools[sample]))

    frames = draw_sample("R100", seed=PRE_REGISTRATION_SEED)

    union_ids = {f.frame_id for g in pools.values() for f in g}
    assert len(frames) == 60  # registered n=100 > union pool of 60: take all of it
    assert {f.frame_id for f in frames} <= union_ids
    assert all(f.sample == "R100" for f in frames)


# --- revision pinning is actually enforced --------------------------------------------------


def test_draw_sample_calls_assert_pinned_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(factory_id="1", worker_id=f"w{i}", clip_id=f"c{i}", frame_index=i)
        for i in range(10)
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    calls: list[tuple[str, str]] = []

    def _spy(corpus: str, corpus_rev: str) -> None:
        calls.append((corpus, corpus_rev))

    monkeypatch.setattr(draw_mod, "assert_pinned_revision", _spy)

    draw_sample("S10k-U", seed=PRE_REGISTRATION_SEED)

    assert calls == [(EVAL_REPO, PINNED_REV)]


def test_draw_sample_propagates_revision_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [
        _corpus_frame(
            factory_id="1", worker_id="w0", clip_id="c0", frame_index=0, corpus_rev="deadbeef"
        )
    ]
    monkeypatch.setattr(draw_mod, "_candidate_frames", lambda sample: list(pool))

    with pytest.raises(ValueError, match="corpus_rev mismatch"):
        draw_sample("S10k-U", seed=PRE_REGISTRATION_SEED)


# --- normalize_worker_id --------------------------------------------------------------------


def test_normalize_worker_id_is_a_pure_function_of_its_inputs() -> None:
    assert normalize_worker_id("egocentric-10k", "00243") == normalize_worker_id(
        "egocentric-10k", "00243"
    )


def test_normalize_worker_id_preserves_the_raw_value() -> None:
    # Documented as identity-mapping-until-Wave-2 (real Ego4D/EPIC-KITCHENS-100 field names are
    # not yet inspected); the corpus argument disambiguates downstream per CONTRACTS.md.
    assert normalize_worker_id("ego4d", "some-raw-field-value") == "some-raw-field-value"
    assert normalize_worker_id("epic-kitchens-100", "P01_01") == "P01_01"


# --- _frames_from_eval_parquet: real parquet + real image decode, no network ----------------


def _write_eval_parquet(path: Path, rows: list[tuple[str, bytes | None]]) -> None:
    """Build a real local parquet matching the real evaluation release's schema (F9): just
    `frame_id`/`image`, since `_frames_from_eval_parquet` never reads the other two columns."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    table = pa.table(
        {
            "frame_id": pa.array([r[0] for r in rows], type=pa.string()),
            "image": pa.array(
                [{"bytes": r[1], "path": None} for r in rows],
                type=pa.struct([("bytes", pa.binary()), ("path", pa.string())]),
            ),
        }
    )
    pq.write_table(table, str(path))


def _real_jpeg_bytes(width: int, height: int) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="red").save(buf, format="JPEG")
    return buf.getvalue()


def test_frames_from_eval_parquet_decodes_real_dimensions(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet

    path = tmp_path / "eval.parquet"
    frame_a = _real_jpeg_bytes(64, 48)
    frame_b = _real_jpeg_bytes(32, 32)
    _write_eval_parquet(path, [("frame-a", frame_a), ("frame-b", frame_b)])

    frames = _frames_from_eval_parquet(str(path), "E10k-ego", PINNED_REV)

    assert [f.frame_id for f in frames] == ["frame-a", "frame-b"]
    assert (frames[0].width, frames[0].height) == (64, 48)
    assert (frames[1].width, frames[1].height) == (32, 32)
    for f in frames:
        assert f.corpus == "egocentric-10k"
        assert f.corpus_rev == PINNED_REV
        assert f.sample == "E10k-ego"
        assert f.factory_id is None
        assert f.worker_id is None
        assert f.clip_id is None
        assert f.timestamp_s is None
        assert f.fps is None
        assert f.codec is None
        assert f.why_no_provenance is not None


def test_frames_from_eval_parquet_frame_index_is_row_position(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet

    path = tmp_path / "eval.parquet"
    jpeg = _real_jpeg_bytes(16, 16)
    _write_eval_parquet(path, [("f0", jpeg), ("f1", jpeg), ("f2", jpeg)])

    frames = _frames_from_eval_parquet(str(path), "E10k-ego4d", PINNED_REV)

    assert [f.frame_index for f in frames] == [0, 1, 2]


def test_frames_from_eval_parquet_excludes_empty_image_bytes(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet

    path = tmp_path / "eval.parquet"
    jpeg = _real_jpeg_bytes(16, 16)
    _write_eval_parquet(path, [("has-image", jpeg), ("no-image", None), ("empty-image", b"")])

    frames = _frames_from_eval_parquet(str(path), "E10k-epic", PINNED_REV)

    assert [f.frame_id for f in frames] == ["has-image"]


# --- synthetic_frame_id (D066): the 100K-eval schema has no frame_id column -----------------


def test_synthetic_frame_id_is_deterministic() -> None:
    from vernier.sampling.draw import synthetic_frame_id

    jpeg = _real_jpeg_bytes(16, 16)
    assert synthetic_frame_id(jpeg) == synthetic_frame_id(jpeg)


def test_synthetic_frame_id_differs_for_different_bytes() -> None:
    from vernier.sampling.draw import synthetic_frame_id

    assert synthetic_frame_id(_real_jpeg_bytes(16, 16)) != synthetic_frame_id(_real_jpeg_bytes(8, 8))


def test_synthetic_frame_id_format_and_never_matches_a_uuid4() -> None:
    import re

    from vernier.sampling.draw import synthetic_frame_id

    frame_id = synthetic_frame_id(_real_jpeg_bytes(4, 4))
    assert frame_id.startswith("e100k-synth-sha256:")
    digest = frame_id.removeprefix("e100k-synth-sha256:")
    assert re.fullmatch(r"[0-9a-f]{64}", digest)
    uuid4_pattern = r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
    assert not re.fullmatch(uuid4_pattern, frame_id)


# --- _frames_from_eval_parquet_100k (D066): no frame_id column, synthetic id used instead ----


def test_frames_from_eval_parquet_100k_decodes_real_dimensions(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet_100k, synthetic_frame_id

    path = tmp_path / "eval_100k.parquet"
    frame_a = _real_jpeg_bytes(64, 48)
    frame_b = _real_jpeg_bytes(32, 32)
    _write_eval_parquet(path, [("unused-frame-id", frame_a), ("unused-frame-id-2", frame_b)])

    frames = _frames_from_eval_parquet_100k(str(path), "E100k-ego", PINNED_REV_100K)

    assert [f.frame_id for f in frames] == [synthetic_frame_id(frame_a), synthetic_frame_id(frame_b)]
    assert (frames[0].width, frames[0].height) == (64, 48)
    assert (frames[1].width, frames[1].height) == (32, 32)
    for f in frames:
        assert f.corpus == "egocentric-100k"
        assert f.corpus_rev == PINNED_REV_100K
        assert f.sample == "E100k-ego"
        assert f.factory_id is None
        assert f.worker_id is None
        assert f.clip_id is None
        assert f.timestamp_s is None
        assert f.fps is None
        assert f.codec is None
        assert f.why_no_provenance is not None
        assert f.why_no_provenance != _EVAL_ARM_WHY_NO_PROVENANCE


def test_frames_from_eval_parquet_100k_frame_index_is_row_position(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet_100k

    path = tmp_path / "eval_100k.parquet"
    jpeg = _real_jpeg_bytes(16, 16)
    _write_eval_parquet(path, [("_", jpeg), ("_", jpeg), ("_", jpeg)])

    frames = _frames_from_eval_parquet_100k(str(path), "E100k-ego", PINNED_REV_100K)

    assert [f.frame_index for f in frames] == [0, 1, 2]


def test_frames_from_eval_parquet_100k_excludes_empty_image_bytes(tmp_path: Path) -> None:
    from vernier.sampling.draw import _frames_from_eval_parquet_100k, synthetic_frame_id

    path = tmp_path / "eval_100k.parquet"
    jpeg = _real_jpeg_bytes(16, 16)
    _write_eval_parquet(path, [("_", jpeg), ("_", None), ("_", b"")])

    frames = _frames_from_eval_parquet_100k(str(path), "E100k-ego", PINNED_REV_100K)

    assert [f.frame_id for f in frames] == [synthetic_frame_id(jpeg)]


def test_frames_from_eval_parquet_100k_id_set_is_stable_under_row_reordering(tmp_path: Path) -> None:
    """A content-hash id (unlike a row-index id) must produce the same SET of frame_ids
    regardless of row order -- the exact property this scheme was chosen for, since Build AI's
    own commit history (F10) already shows a delete-and-replace can reorder rows."""
    from vernier.sampling.draw import _frames_from_eval_parquet_100k

    jpeg_a, jpeg_b, jpeg_c = _real_jpeg_bytes(16, 16), _real_jpeg_bytes(8, 8), _real_jpeg_bytes(4, 4)
    path_forward = tmp_path / "forward.parquet"
    path_reversed = tmp_path / "reversed.parquet"
    _write_eval_parquet(path_forward, [("_", jpeg_a), ("_", jpeg_b), ("_", jpeg_c)])
    _write_eval_parquet(path_reversed, [("_", jpeg_c), ("_", jpeg_b), ("_", jpeg_a)])

    forward_ids = {f.frame_id for f in _frames_from_eval_parquet_100k(str(path_forward), "E100k-ego", PINNED_REV_100K)}
    reversed_ids = {f.frame_id for f in _frames_from_eval_parquet_100k(str(path_reversed), "E100k-ego", PINNED_REV_100K)}

    assert forward_ids == reversed_ids


# --- structural consistency: every eval-arm entry stays fully wired across the three dicts ---


def test_every_eval_arm_has_a_matching_repo_and_filename_entry() -> None:
    import vernier.sampling.draw as draw_mod

    for sample in draw_mod._EVAL_PARQUET_FILENAME:
        assert sample in draw_mod._EVAL_HF_REPO_FOR_SAMPLE, sample
        assert sample in draw_mod._N, sample
        repo_id = draw_mod._EVAL_HF_REPO_FOR_SAMPLE[sample]
        assert repo_id in PINNED_REVISIONS, (sample, repo_id)


def test_candidate_frames_raises_not_implemented_for_unwired_corpus_samples() -> None:
    from vernier.sampling.draw import _candidate_frames

    with pytest.raises(NotImplementedError, match="S10k-U"):
        _candidate_frames("S10k-U")


# --- image_bytes_for: searches all three eval files by frame_id, not by frame.sample --------


@pytest.fixture(autouse=True)
def _clear_eval_frame_bytes_cache() -> Iterator[None]:
    """`_eval_frame_bytes_by_id` is `@lru_cache`'d at module scope -- without clearing it, one
    test's monkeypatched `_download_eval_parquet` would leak into the next test's cache hit."""
    from vernier.sampling.draw import _eval_frame_bytes_by_id

    _eval_frame_bytes_by_id.cache_clear()
    yield
    _eval_frame_bytes_by_id.cache_clear()


def _patch_eval_downloads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, contents: dict[str, list[tuple[str, bytes | None]]]
) -> None:
    """`contents` maps root sample name ("E10k-ego" etc.) -> rows to write into that sample's
    synthetic local parquet; `_download_eval_parquet` is monkeypatched to return that file's
    path instead of hitting the real network.

    Any real evaluation-release arm NOT named in `contents` (e.g. `E100k-ego`, D066) is
    auto-filled with an empty synthetic parquet -- `image_bytes_for` searches every arm in
    `_EVAL_PARQUET_FILENAME` unconditionally, so a caller testing one arm shouldn't have to
    enumerate every other one just to keep that search from hitting the real network."""
    import vernier.sampling.draw as draw_mod

    paths: dict[str, Path] = {}
    for sample, rows in contents.items():
        path = tmp_path / f"{sample}.parquet"
        _write_eval_parquet(path, rows)
        paths[sample] = path
    for sample in draw_mod._EVAL_PARQUET_FILENAME:
        if sample not in paths:
            path = tmp_path / f"{sample}.parquet"
            _write_eval_parquet(path, [])
            paths[sample] = path

    monkeypatch.setattr(draw_mod, "_download_eval_parquet", lambda sample: str(paths[sample]))


def test_image_bytes_for_finds_a_frame_by_its_own_root_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpeg = _real_jpeg_bytes(8, 8)
    _patch_eval_downloads(
        monkeypatch,
        tmp_path,
        {"E10k-ego": [("uuid-f0", jpeg)], "E10k-ego4d": [], "E10k-epic": []},
    )

    result = draw_mod.image_bytes_for(_eval_frame(sample="E10k-ego", uid="f0"))

    assert result == jpeg


def test_image_bytes_for_finds_a_subset_sample_frame_via_its_root_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression guard for a real bug: a `G200-ego4d` frame is really an `E10k-ego4d` frame
    with `sample` relabelled -- caught live when a real `next_frame()`-returned `G200-ego4d`
    frame raised (frame.sample used to gate which single file was searched)."""
    jpeg = _real_jpeg_bytes(8, 8)
    _patch_eval_downloads(
        monkeypatch,
        tmp_path,
        {"E10k-ego": [], "E10k-ego4d": [("uuid-f0", jpeg)], "E10k-epic": []},
    )
    frame = _eval_frame(sample="G200-ego4d", uid="f0")

    result = draw_mod.image_bytes_for(frame)

    assert result == jpeg


def test_image_bytes_for_r100_frame_found_regardless_of_which_root_arm(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """R100 draws from the union of three different root arms -- `frame.sample == "R100"`
    alone can never say which file to search, so this must work no matter which one holds it."""
    jpeg = _real_jpeg_bytes(8, 8)
    _patch_eval_downloads(
        monkeypatch,
        tmp_path,
        {"E10k-ego": [], "E10k-ego4d": [], "E10k-epic": [("uuid-f0", jpeg)]},
    )
    frame = _eval_frame(sample="R100", uid="f0")

    result = draw_mod.image_bytes_for(frame)

    assert result == jpeg


def test_image_bytes_for_raises_not_implemented_for_s10k_samples() -> None:
    frame = _eval_frame(sample="S10k-U", uid="f0")

    with pytest.raises(NotImplementedError, match="S10k-U"):
        draw_mod.image_bytes_for(frame)


def test_image_bytes_for_raises_key_error_when_truly_not_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_eval_downloads(
        monkeypatch, tmp_path, {"E10k-ego": [], "E10k-ego4d": [], "E10k-epic": []}
    )
    frame = _eval_frame(sample="G200-ego", uid="never-existed")

    with pytest.raises(KeyError, match="never-existed"):
        draw_mod.image_bytes_for(frame)
