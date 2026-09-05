"""Tests for `scripts/export_space_thumbnails.py` -- the licence and likeness controls.

`docs/ETHICS.md` section 4 (D073) permits exactly one set of frames to be republished, and
`make privacy-gate` cannot check it: that gate greps staged paths for `docs/private/`, and
nothing under `space/public/` is gitignored, so a stray frame dropped there would be committed
by default. These tests are the compensating control. The decisive one decodes the committed
atlas and asserts every blank cell is the declared background colour -- a manifest-only check
would pass while shipping an extra frame in the padding.

The likeness exclusions are a manual visual review and no test can confirm them. What is
tested is that the review is applied, is not stale, and that every withheld frame is absent.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_space_thumbnails  # noqa: E402
from export_space_thumbnails import (  # noqa: E402
    _CORPUS,
    _LIKENESS_REVIEWED,
    _PRIVACY_EXCLUDED,
    _SAMPLE,
    _select,
)  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_INDEX_PATH = _ROOT / "data" / "space_thumbnails.json"
_ATLAS_DIR = _ROOT / "space" / "public" / "atlas"


@pytest.fixture(scope="module")
def index() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(_INDEX_PATH.read_text())
    return payload


def _labelled() -> set[str]:
    return {r["frame_id"] for r in json.loads((_ROOT / "data" / "labels" / "caio" / "primary.json").read_text())}


def _gold() -> dict[str, str]:
    rows = json.loads((_ROOT / "data" / "membership" / f"{_SAMPLE}.json").read_text())
    return {r["frame_id"]: r["corpus"] for r in rows}


def test_index_is_the_labelled_egocentric_10k_frames_minus_the_likeness_exclusions(
    index: dict[str, Any],
) -> None:
    gold = _gold()
    # D085: "labelled" and "likeness-reviewed" were the same set exactly once. Adding labels
    # made them different, and only the reviewed set may ship (docs/ETHICS.md section 4).
    expected = {f for f in gold if f in _labelled() and f in _LIKENESS_REVIEWED} - set(_PRIVACY_EXCLUDED)
    assert set(index["tiles"]) == expected
    assert expected < {f for f in gold if f in _labelled()}, (
        "every reviewed frame must be a labelled frame, and there are now labelled frames "
        "awaiting review that must not be in the atlas"
    )
    assert index["n"] == len(expected) == len(index["tiles"])
    assert index["corpus"] == _CORPUS


def test_no_frame_from_a_restricted_corpus_is_shipped(index: dict[str, Any]) -> None:
    """Ego4D's licence forbids it and EPIC-KITCHENS-100 is held to the same rule (D073)."""
    gold = _gold()
    for frame_id in index["tiles"]:
        assert gold[frame_id] == _CORPUS, f"{frame_id} is {gold[frame_id]!r}, not {_CORPUS!r}"


def test_every_shipped_tile_is_a_frame_a_human_judged(index: dict[str, Any]) -> None:
    assert set(index["tiles"]) <= _labelled()


def test_the_likeness_review_is_applied_and_is_not_stale(index: dict[str, Any]) -> None:
    gold = _gold()
    assert set(_PRIVACY_EXCLUDED) <= set(gold), "the review names a frame outside the sample"
    assert set(index["withheld_for_likeness"]) == set(_PRIVACY_EXCLUDED)
    for frame_id, reason in _PRIVACY_EXCLUDED.items():
        assert frame_id not in index["tiles"], f"{frame_id} was withheld but is in the atlas"
        assert reason.strip(), f"{frame_id} is withheld with no stated reason"


def test_the_grid_has_no_unaccounted_cell(index: dict[str, Any]) -> None:
    atlas = index["atlas"]
    assert atlas["cols"] * atlas["rows"] - atlas["n_tiles"] == atlas["n_blank"]
    assert atlas["n_tiles"] == index["n"]
    assert atlas["w"] == atlas["cols"] * index["tile"]["w"]
    assert atlas["h"] == atlas["rows"] * index["tile"]["h"]


def test_committed_atlas_bytes_match_the_manifest_digest(index: dict[str, Any]) -> None:
    """Runs anywhere: no Pillow, no parquet, no network."""
    blob = (_ROOT / "space" / "public" / index["atlas"]["file"]).read_bytes()
    assert len(blob) == index["atlas"]["bytes"]
    assert hashlib.sha256(blob).hexdigest() == index["atlas"]["file_sha256"]


def test_every_blank_cell_is_the_declared_background(index: dict[str, Any]) -> None:
    """The only check that can show no extra frame is hiding in the padding."""
    Image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    atlas = index["atlas"]
    tile_w, tile_h = index["tile"]["w"], index["tile"]["h"]
    occupied = {(t["x"], t["y"]) for t in index["tiles"].values()}
    background = tuple(atlas["background"])
    with Image.open(_ROOT / "space" / "public" / atlas["file"]) as im:
        rgb = im.convert("RGB")
        assert rgb.size == (atlas["w"], atlas["h"])
        for row in range(atlas["rows"]):
            for col in range(atlas["cols"]):
                x, y = col * tile_w, row * tile_h
                if (x, y) in occupied:
                    continue
                # WebP is lossy and bleeds the neighbouring tile across the cell boundary,
                # so check the interior rather than loosening the tolerance. A frame hiding in
                # the padding would blow this apart on the first channel; a flat fill will not.
                inset = 16
                cell = rgb.crop((x + inset, y + inset, x + tile_w - inset, y + tile_h - inset))
                for band, (lo, hi) in enumerate(cell.getextrema()):
                    assert abs(lo - background[band]) <= 4 and abs(hi - background[band]) <= 4, (
                        f"blank cell at ({col},{row}) band {band} spans {lo}..{hi}, not "
                        f"~{background[band]} -- something is in the padding"
                    )


def test_nothing_under_the_atlas_directory_is_a_full_resolution_frame(index: dict[str, Any]) -> None:
    Image = pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    atlas = index["atlas"]
    files = [p for p in _ATLAS_DIR.rglob("*") if p.is_file()]
    assert files, "the atlas directory is empty"
    for path in files:
        assert path.stat().st_size <= 2_000_000, f"{path.name} is larger than any atlas should be"
        with Image.open(path) as im:
            assert im.width <= atlas["w"] and im.height <= atlas["h"], f"{path.name} exceeds the declared grid"


def test_tile_boxes_are_inside_the_grid_and_do_not_overlap(index: dict[str, Any]) -> None:
    atlas, tile = index["atlas"], index["tile"]
    seen: set[tuple[int, int]] = set()
    for frame_id, box in index["tiles"].items():
        assert (box["w"], box["h"]) == (tile["w"], tile["h"]), frame_id
        assert 0 <= box["x"] <= atlas["w"] - tile["w"], frame_id
        assert 0 <= box["y"] <= atlas["h"] - tile["h"], frame_id
        assert box["x"] % tile["w"] == 0 and box["y"] % tile["h"] == 0, frame_id
        assert (box["x"], box["y"]) not in seen, f"{frame_id} overlaps another tile"
        seen.add((box["x"], box["y"]))


def test_the_source_is_the_pinned_apache_licensed_release(index: dict[str, Any]) -> None:
    from vernier.sampling.revisions import PINNED_REVISIONS

    source = index["source"]
    assert source["license"] == "apache-2.0"
    assert source["revision"] == PINNED_REVISIONS[source["dataset"]]


def test_select_honours_an_explicit_withdrawal() -> None:
    """`--exclude` is the withdrawal path section 4 promises; it must actually remove a frame."""
    kept = _select(frozenset())
    victim = kept[0]
    assert victim not in _select(frozenset({victim}))


def test_fresh_build_reproduces_the_committed_raster(index: dict[str, Any]) -> None:
    pytest.importorskip("PIL.Image", reason="Pillow is not installed")
    if export_space_thumbnails._parquet_path() is None:
        pytest.skip("the pinned evaluation parquet is not in the local HF cache")
    built = export_space_thumbnails.build(frozenset())
    assert built is not None
    assert built["atlas"]["raster_sha256"] == index["atlas"]["raster_sha256"]


def test_build_is_a_clean_no_op_without_the_parquet(monkeypatch: pytest.MonkeyPatch) -> None:
    """A cold cache must leave the committed artifacts alone rather than ship a partial atlas."""
    before = (_INDEX_PATH.read_bytes(), (_ROOT / "space" / "public" / "atlas" / "e10k-256.webp").read_bytes())
    monkeypatch.setattr(export_space_thumbnails, "_parquet_path", lambda: None)
    assert export_space_thumbnails.main([]) == 0
    after = (_INDEX_PATH.read_bytes(), (_ROOT / "space" / "public" / "atlas" / "e10k-256.webp").read_bytes())
    assert before == after


def test_ethics_section_4_counts_match_the_committed_index(index: dict[str, Any]) -> None:
    """Section 4 states counts. AGENTS.md rule 2: they are read from files, never typed."""
    text = (_ROOT / "docs" / "ETHICS.md").read_text()
    body = text[text.index("4. **Frames are republished only where") :]
    # Collapse the wrapping so the assertions below are about the prose, not the line breaks.
    section = " ".join(body[: body.index("\n5. **No attempt to identify anyone")].split())

    frames = json.loads((_ROOT / "space" / "public" / "data" / "frames.json").read_text())
    labelled = _labelled()
    by_corpus: dict[str, int] = {}
    for frame in frames:
        if frame["id"] in labelled:
            by_corpus[frame["corpus"]] = by_corpus.get(frame["corpus"], 0) + 1

    for claim in [
        f"{index['n']} frames",
        f"{len(frames) - index['n']} gold frames",
        f"{len(labelled)} human-labelled frames",
        f"{by_corpus['egocentric-10k']} are Egocentric-10K",
        f"{by_corpus['ego4d']} are Ego4D",
        f"{by_corpus['epic-kitchens-100']} are EPIC-KITCHENS-100",
        # D085: withheld is a fraction of the REVIEWED set, not of every labelled frame.
        f"{len(index['withheld_for_likeness'])} of the {len(_LIKENESS_REVIEWED)} reviewed",
        index["source"]["revision"][:8],
        "30,000",
    ]:
        assert claim in section, f"docs/ETHICS.md section 4 no longer states {claim!r}"
