"""Tests for `scripts/export_space_data.py`: every number the Space shows equals what
`MEASUREMENT_CARD.json` / `data/wave4_analysis.json` carry (the `tests/test_emit_card.py`
rule, AGENTS.md rule 2), and the committed `space/public/data/*.json` equal a fresh build.

The parquet-derived fields (`row`, `g`) are asserted on the committed `frames.json` -- which
is what the Space actually serves -- so a machine without the ~5.5GB evaluation parquets in
its HF cache still runs every check that matters; the fresh-parquet-scan equality test skips,
with a stated reason, only where the scan itself is impossible.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import export_space_data  # noqa: E402
from export_space_data import (  # noqa: E402
    _ROWS_API_FILE_ORDER,
    build_frames,
    build_stats,
    load_parquet_index,
    parse_prereg_published,
    row_base,
)

_ROOT = Path(__file__).resolve().parent.parent
_OUT = _ROOT / "space" / "public" / "data"


@pytest.fixture(scope="module")
def committed_frames() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = json.loads((_OUT / "frames.json").read_text())
    return payload


@pytest.fixture(scope="module")
def committed_stats() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((_OUT / "stats.json").read_text())
    return payload


@pytest.fixture(scope="module")
def wave4() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((_ROOT / "data" / "wave4_analysis.json").read_text())
    return payload


@pytest.fixture(scope="module")
def card() -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((_ROOT / "MEASUREMENT_CARD.json").read_text())
    return payload


def _slice(frames: list[dict[str, Any]], *, corpus: str, judge_m: bool, rater_m: bool) -> list[dict[str, Any]]:
    """The web `SliceState` for `#task=manipulation&corpus=<c>&judge=<yes|no>&rater=<yes|no>`."""
    return [
        f
        for f in frames
        if f["corpus"] == corpus
        and f["q"]["s"] == "ok"
        and f["q"]["m"] is judge_m
        and f["r"] is not None
        and f["r"]["m"] is rater_m
    ]


# --- frames.json ---------------------------------------------------------------------------


def test_committed_frames_are_the_600_gold_frames_with_stored_labels_and_rows(
    committed_frames: list[dict[str, Any]],
) -> None:
    assert len(committed_frames) == 600
    assert {f["corpus"] for f in committed_frames} == {"egocentric-10k", "ego4d", "epic-kitchens-100"}
    assert all(f["g"] is not None for f in committed_frames), "g (stored gemini P0b) must come from the parquet scan, never the fallback"
    assert all(f["q"]["s"] == "ok" for f in committed_frames)
    assert sum(1 for f in committed_frames if f["r"] is not None) == 93
    rows = [f["row"] for f in committed_frames]
    assert len(set(rows)) == 600
    assert all(0 <= r < 30_000 for r in rows)


def test_committed_rows_match_membership_frame_index_plus_file_base(
    committed_frames: list[dict[str, Any]],
) -> None:
    """`row` = (file base in the datasets-server split) + (index within that file). The
    membership `frame_index` is that within-file index for every G200 frame (verified live
    against the parquet scan and `/rows`), so the committed rows must satisfy this exactly."""
    assert _ROWS_API_FILE_ORDER == ("ego4d", "egocentric-10k", "epic-kitchens-100")
    rows_per_file = {c: 10_000 for c in _ROWS_API_FILE_ORDER}
    membership: dict[str, int] = {}
    for sample in ("G200-ego", "G200-ego4d", "G200-epic"):
        for ref in json.loads((_ROOT / "data" / "membership" / f"{sample}.json").read_text()):
            membership[ref["frame_id"]] = ref["frame_index"]
    for f in committed_frames:
        assert f["row"] == row_base(f["corpus"], rows_per_file) + membership[f["id"]]


def test_fresh_parquet_scan_reproduces_the_committed_frames(
    committed_frames: list[dict[str, Any]],
) -> None:
    index = load_parquet_index()
    if index is None:
        pytest.skip("evaluation parquets are not in the local HF cache; committed frames.json checked above")
    assert build_frames(index) == committed_frames


def test_fallback_without_parquet_keeps_rows_and_nulls_g(committed_frames: list[dict[str, Any]]) -> None:
    frames = build_frames(None)
    assert [f["row"] for f in frames] == [f["row"] for f in committed_frames]
    assert all(f["g"] is None for f in frames)


# --- stats.json ----------------------------------------------------------------------------


def test_committed_stats_equal_a_fresh_build(
    committed_frames: list[dict[str, Any]], committed_stats: dict[str, Any]
) -> None:
    fresh = build_stats(committed_frames)
    # git_rev is the last commit touching MEASUREMENT_CARD.json; history rewrites move it.
    fresh["generated_from"]["git_rev"] = committed_stats["generated_from"]["git_rev"]
    assert fresh == committed_stats


def test_ppi_equals_wave4_and_the_card(
    committed_stats: dict[str, Any], wave4: dict[str, Any], card: dict[str, Any]
) -> None:
    statements = " ".join(c["statement"] for c in card["claims"] if c["record_type"] == "PrevalenceEstimate")
    seen = 0
    for by_task in wave4["ppi"].values():
        for task, est in by_task.items():
            got = committed_stats["ppi"][est["corpus"]][task]
            assert got["value"] == est["ppi"]["value"]
            assert got["lo"] == est["ppi"]["ci"]["lo"]
            assert got["hi"] == est["ppi"]["ci"]["hi"]
            assert got["naive"] == est["naive"]["value"]
            assert got["n_gold"] == est["ppi"]["n_gold"]
            assert got["n_unlabelled"] == est["ppi"]["n_unlabelled"]
            assert got["clustered"] is False and got["why_not_clustered"]
            assert committed_stats["published"][est["corpus"]][task] == est["published"]
            for number in (est["ppi"]["value"], est["ppi"]["ci"]["lo"], est["ppi"]["ci"]["hi"], est["naive"]["value"], est["published"]):
                assert f"{number:.4f}" in statements
            seen += 1
    assert seen == 6


def test_judge_alone_rates_equal_ppi_naive(committed_stats: dict[str, Any]) -> None:
    for corpus in ("egocentric-10k", "ego4d", "epic-kitchens-100"):
        for task in ("hand_count", "manipulation"):
            assert committed_stats["judge_alone"][corpus][task]["rate"] == pytest.approx(
                committed_stats["ppi"][corpus][task]["naive"]
            )
            assert committed_stats["judge_alone"][corpus][task]["n"] == committed_stats["ppi"][corpus][task]["n_judged"]


def test_agreement_equals_wave4_and_the_card(
    committed_stats: dict[str, Any], wave4: dict[str, Any], card: dict[str, Any]
) -> None:
    statements = " ".join(c["statement"] for c in card["claims"])
    for task in ("hand_count", "manipulation"):
        h4 = committed_stats["agreement"]["h4"][task]
        assert h4["ac1"] == wave4["H4"][task]["ac1"]
        assert (h4["lo"], h4["hi"]) == (wave4["H4"][task]["ac1_ci"]["lo"], wave4["H4"][task]["ac1_ci"]["hi"])
        assert h4["kappa"] == wave4["H4"][task]["kappa"]
        assert h4["raw"] == wave4["H4"][task]["raw_agreement"]
        assert h4["n"] == wave4["n_primary"] == 93
        assert f"{h4['ac1']:.4f}" in statements
        intra = committed_stats["agreement"]["intra_rater"][task]
        assert intra["ac1"] == wave4["intra_rater"][task]["ac1"]
        assert intra["n_pairs"] == wave4["intra_rater"][task]["n_pairs"]
        assert f"{intra['ac1']:.4f}" in statements
    h5 = committed_stats["agreement"]["h5"]
    assert h5["egocentric-10k"]["error_rate"] == wave4["H5"]["egocentric"]["error_rate"]
    assert h5["epic-kitchens-100"]["error_rate"] == wave4["H5"]["epic_kitchens"]["error_rate"]


def test_confusion_tables_reproduce_h4_raw_agreement(
    committed_stats: dict[str, Any], wave4: dict[str, Any]
) -> None:
    confusion = committed_stats["confusion"]
    assert confusion["n"] == wave4["n_primary"]
    hands = confusion["hands"]
    assert sum(sum(row) for row in hands) == confusion["n"]
    assert sum(hands[i][i] for i in range(3)) / confusion["n"] == pytest.approx(wave4["H4"]["hand_count"]["raw_agreement"])
    manipulation = confusion["manipulation"]
    assert sum(sum(row) for row in manipulation) == confusion["n"]
    assert (manipulation[0][0] + manipulation[1][1]) / confusion["n"] == pytest.approx(
        wave4["H4"]["manipulation"]["raw_agreement"]
    )


def test_h5_slice_is_exactly_the_frames_the_claim_counts(
    committed_frames: list[dict[str, Any]], committed_stats: dict[str, Any], wave4: dict[str, Any]
) -> None:
    """SPEC acceptance 3: `#task=manipulation&corpus=egocentric-10k&judge=yes&rater=no` shows
    exactly the frames behind H5's Egocentric error rate."""
    h5 = wave4["H5"]["egocentric"]
    judge_yes_rater_no = _slice(committed_frames, corpus="egocentric-10k", judge_m=True, rater_m=False)
    judge_no_rater_yes = _slice(committed_frames, corpus="egocentric-10k", judge_m=False, rater_m=True)
    assert len(judge_yes_rater_no) == 3
    assert len(judge_no_rater_yes) == 0
    assert len(judge_yes_rater_no) + len(judge_no_rater_yes) == round(h5["error_rate"] * h5["n"])
    assert all(f["g"] is not None and f["r"] is not None for f in judge_yes_rater_no)
    assert committed_stats["confusion"]["manipulation"][1][0] == 3 + len(
        _slice(committed_frames, corpus="ego4d", judge_m=True, rater_m=False)
    ) + len(_slice(committed_frames, corpus="epic-kitchens-100", judge_m=True, rater_m=False))


def test_calibration_equals_wave4_and_keeps_empty_bins(
    committed_stats: dict[str, Any], wave4: dict[str, Any], card: dict[str, Any]
) -> None:
    statements = " ".join(c["statement"] for c in card["claims"])
    for task in ("hand_count", "manipulation"):
        cal = committed_stats["calibration"][task]
        assert cal["ece"] == wave4["H7_calibration"][task]["ece"]
        assert cal["bins"] == wave4["H7_calibration"][task]["bins"]
        assert len(cal["bins"]) == 10
        assert sum(1 for b in cal["bins"] if b["n"] == 0) == 8
        assert f"{cal['ece']:.4f}" in statements


def test_published_comes_from_the_frozen_preregistration_table(committed_stats: dict[str, Any]) -> None:
    parsed = parse_prereg_published((_ROOT / "docs" / "PRE-REGISTRATION.md").read_text())
    for corpus, by_task in parsed.items():
        assert committed_stats["published"][corpus] == by_task
    assert committed_stats["published"]["egocentric-10k"] == {"hand_count": 0.9642, "hand_eq2": 0.7634, "manipulation": 0.9166}
    with pytest.raises(ValueError):
        parse_prereg_published("| Dataset | Frames |\n|---|---|\n")


def test_coverage_counts_the_29400_stored_labels(committed_stats: dict[str, Any]) -> None:
    stored = json.loads((_ROOT / "data" / "rung1_stored_labels.json").read_text())
    coverage = committed_stats["coverage"]
    assert sum(coverage[c]["n"] for c in ("egocentric-10k", "ego4d", "epic-kitchens-100")) == len(stored) == 29_400
    for corpus in ("egocentric-10k", "ego4d", "epic-kitchens-100"):
        assert sum(coverage[corpus]["hands"]) == coverage[corpus]["n"]
        assert sum(coverage[corpus]["manipulation"]) == coverage[corpus]["n"]
        assert "gemini-2.5-flash" in coverage[corpus]["source"]
    # The 100K row exists only because data/e2_100k_eval.json does, and says where it came from.
    assert "egocentric-100k" in committed_stats["corpora"]
    assert "live judge" in coverage["egocentric-100k"]["source"]
    assert sum(coverage["egocentric-100k"]["hands"]) == coverage["egocentric-100k"]["n"] == 9_999


def test_health_and_runs_equal_the_committed_run_files(committed_stats: dict[str, Any]) -> None:
    e2 = json.loads((_ROOT / "data" / "e2_full_n10000.json").read_text())
    health = committed_stats["health"]
    assert health["e2_cost_both_arms_usd"] == pytest.approx(
        e2["per_variant"]["P0a"]["total_cost_usd"] + e2["per_variant"]["P0b"]["total_cost_usd"]
    )
    assert health["e2_judge_time_both_arms_h"] == pytest.approx(
        (e2["per_variant"]["P0a"]["total_latency_ms"] + e2["per_variant"]["P0b"]["total_latency_ms"]) / 3_600_000
    )
    assert health["gold_calls"]["n"] == 600
    assert health["gold_calls"]["max_ms"] == 229_546
    ids = [r["id"] for r in committed_stats["runs"]]
    assert ids[:2] == ["E2 P0a", "E2 P0b"]
    assert sum(1 for i in ids if i.startswith("E5 ")) == 8
    assert sum(1 for i in ids if i.startswith("Gold ")) == 3
    gold = [r for r in committed_stats["runs"] if r["id"].startswith("Gold ")]
    assert all(len(r["latency_ms"]) == 200 and r["n_ok"] == 200 for r in gold)
    e5 = [r for r in committed_stats["runs"] if r["id"].startswith("E5 ")]
    assert all(r["cost_usd"] is None and r["judge_time_ms"] is None for r in e5), "E5 cost/latency are not committed; never invented"


def test_generated_from_names_the_card_digest(committed_stats: dict[str, Any], card: dict[str, Any]) -> None:
    assert committed_stats["generated_from"]["card_digest"] == card["content_digest"]
    assert committed_stats["rows_api"]["source_dataset"] == {
        "egocentric-10k": "egocentric_10k",
        "ego4d": "ego4d",
        "epic-kitchens-100": "epic_kitchens",
    }
    assert export_space_data._OUT_DIR == _OUT
