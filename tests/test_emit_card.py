"""Tests for `scripts/emit_card.py`'s claim-construction logic.

Does not call `main()` here -- that writes the real, committed `MEASUREMENT_CARD.json` at the
repo root, which is `make card`'s job (regenerate-and-commit, the same pattern
`scripts/generate_fixtures.py` already uses for `tests/fixtures/`), not something to trigger as
a side effect of every `pytest` run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import emit_card  # noqa: E402
from emit_card import (  # noqa: E402
    _h1_h1b_claims,
    _h3_claim,
    _h4_claim,
    _h5_claim,
    _h6_claim,
    _h7_claim,
    _h8_claim,
    _intra_rater_claim,
    _ppi_claims,
    _unmet_claims,
)


def test_h8_claim_reports_the_real_corrected_counts() -> None:
    claim = _h8_claim()
    assert "2153" in claim.statement
    assert "923" in claim.statement
    assert "37" in claim.statement
    assert "58.2" in claim.statement  # 2153 / 37, the real spread


def test_h8_claim_is_not_tied_to_a_prevalence_estimate() -> None:
    # _derive_verdict (docs/DECISIONS.md D038) only matches claims with
    # record_type == "PrevalenceEstimate" against prevalence_estimates -- H8 must not
    # accidentally look like one, or it could spuriously satisfy the verdict rule.
    claim = _h8_claim()
    assert claim.record_type != "PrevalenceEstimate"


def test_every_unmet_claim_has_a_named_blocker_reason() -> None:
    items = _unmet_claims()
    assert len(items) == 2  # H2, Result 2 -- H1/H1b/H3/H4/H5/H6/H7 are now real Claims (D054-D056, D059-D061)
    for item in items:
        assert item.reason.strip()
        assert "BLOCKER:" in item.reason


def test_unmet_claims_cover_every_still_blocked_hypothesis() -> None:
    items = {i.item for i in _unmet_claims()}
    for tag in ["H2 ", "Result 2"]:
        assert any(tag in item for item in items), f"missing {tag!r} in unmet claims"
    # H1/H1b/H3 (D054/D055), H4/H5 (D059), H7 (D060), and H6 (D061) moved to real Claims --
    # must not still be listed as blocked, or the card would understate real, completed progress.
    for tag in ["H1 ", "H1b", "H3 ", "H4 ", "H5 ", "H6 ", "H7 "]:
        assert not any(tag in item for item in items), f"{tag!r} should no longer be unmet"


def test_blockers_are_named_specifically() -> None:
    # H2/Result 2's blocker is a real, checked access gap (D044), not "HF_TOKEN not configured"
    # (it is configured).
    items = _unmet_claims()
    reasons = " ".join(i.reason for i in items)
    assert "D044" in reasons
    assert "NOT authorized" in reasons


# --- H1/H1b/H3: real claims from the full-N run (D054/D055) -----------------------------------
#
# These monkeypatch emit_card's own module-level result-file constants rather than depending on
# the real (gitignored, multi-hour-to-produce) data/e2_full_n10000.json / e5_full_n2000.json
# artifacts existing on disk -- a fresh checkout or CI run must not need those to pass tests.


def _write_e2_fixture(path: Path, *, hand_eq2_outside_tolerance: bool, h1b_disagree: bool) -> None:
    path.write_text(
        json.dumps(
            {
                "per_variant": {
                    "P0a": {"n_total": 10000},
                    "P0b": {"n_total": 10000},
                },
                "H1": {
                    "hand_ge1_rate": {
                        "published": 0.9642,
                        "observed_P0a": 0.9545,
                        "diff_pp": 0.97,
                        "within_2pp_tolerance": True,
                    },
                    "hand_eq2_rate": {
                        "published": 0.7634,
                        "observed_P0a": 0.8266,
                        "diff_pp": 6.32,
                        "within_2pp_tolerance": not hand_eq2_outside_tolerance,
                    },
                    "active_manipulation_rate": {
                        "published": 0.9166,
                        "observed_P0a": 0.9128,
                        "diff_pp": 0.38,
                        "within_2pp_tolerance": True,
                    },
                },
                "H1b": {
                    "p0a_active_manipulation_rate": 0.9128,
                    "p0b_active_manipulation_rate": 0.9096 if not h1b_disagree else 0.80,
                    "diff_pp": 0.32 if not h1b_disagree else 11.28,
                    "p0_variants_disagree": h1b_disagree,
                },
            }
        )
    )


def _write_e5_fixture(path: Path, *, manip_spread_pp: float, spread_meets_threshold: bool) -> None:
    path.write_text(
        json.dumps(
            {
                "n_frames_drawn": 2000,
                "H3": {
                    "hand_count_spread_pp": 0.25,
                    "manipulation_spread_pp": manip_spread_pp,
                    "manipulation_spread_at_least_5pp": spread_meets_threshold,
                    "manipulation_spread_exceeds_hand_count_spread": manip_spread_pp > 0.25,
                    "p3_glove_diff_pp": 0.05,
                    "p3_glove_moves_hand_count_by_at_least_2pp": False,
                },
            }
        )
    )


def test_h1_reports_replication_failure_when_any_figure_is_outside_tolerance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e2_path = tmp_path / "e2.json"
    _write_e2_fixture(e2_path, hand_eq2_outside_tolerance=True, h1b_disagree=False)
    monkeypatch.setattr(emit_card, "_E2_RESULTS_PATH", e2_path)

    h1_claim, h1b_claim = _h1_h1b_claims()

    assert "NOT hold" in h1_claim.statement
    assert "1/3" in h1_claim.statement
    assert h1_claim.record_type != "PrevalenceEstimate"
    assert "null" in h1b_claim.statement  # 0.32pp < 1pp threshold


def test_h1b_reports_real_disagreement_when_threshold_is_met(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e2_path = tmp_path / "e2.json"
    _write_e2_fixture(e2_path, hand_eq2_outside_tolerance=True, h1b_disagree=True)
    monkeypatch.setattr(emit_card, "_E2_RESULTS_PATH", e2_path)

    _, h1b_claim = _h1_h1b_claims()

    assert "disagree" in h1b_claim.statement
    assert "null" not in h1b_claim.statement


def test_h3_reports_prediction_not_supported_below_5pp_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e5_path = tmp_path / "e5.json"
    _write_e5_fixture(e5_path, manip_spread_pp=1.25, spread_meets_threshold=False)
    monkeypatch.setattr(emit_card, "_E5_RESULTS_PATH", e5_path)

    claim = _h3_claim()

    assert "not supported" in claim.statement
    assert claim.record_type != "PrevalenceEstimate"


def test_h3_reports_prediction_supported_when_spread_clears_floor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    e5_path = tmp_path / "e5.json"
    _write_e5_fixture(e5_path, manip_spread_pp=6.0, spread_meets_threshold=True)
    monkeypatch.setattr(emit_card, "_E5_RESULTS_PATH", e5_path)

    claim = _h3_claim()

    assert "not supported" not in claim.statement


# --- intra-rater / H4 / H5 / PPI: real Wave 4 claims (D059) ------------------------------------


def _ac1_ci_block(point: float, width: float = 0.1) -> dict[str, object]:
    return {
        "lo": max(0.0, point - width),
        "hi": min(1.0, point + width),
        "method": "iid",
        "clusters": None,
        "B": None,
    }


def _ppi_block(*, corpus: str, published: float) -> dict[str, object]:
    return {
        "corpus": corpus,
        "task": "manipulation",
        "prompt_variant": "P0b",
        "judge": "qwen3-vl",
        "naive": {"value": 0.9, "n": 200},
        "ppi": {
            "value": 0.85,
            "ci": {"lo": 0.75, "hi": 0.95, "level": 0.95},
            "n_gold": 30,
            "n_unlabelled": 170,
            "rectifier": 0.0,
            "method": "ppi++",
            "clustered": False,
            "cluster_by": None,
            "why_not_clustered": "test fixture",
        },
        "published": published,
    }


def _write_wave4_fixture(
    path: Path,
    *,
    intra_rater_ac1: float = 0.85,
    h4_hand_count_ac1: float = 0.90,
    h4_manipulation_ac1: float = 0.80,
    h5_ego_error: float = 0.05,
    h5_epic_error: float = 0.10,
) -> None:
    h5_diff_pp = (h5_epic_error - h5_ego_error) * 100
    path.write_text(
        json.dumps(
            {
                "n_primary": 93,
                "n_retest": 60,
                "intra_rater": {
                    "hand_count": {
                        "ac1": intra_rater_ac1,
                        "ac1_ci": _ac1_ci_block(intra_rater_ac1),
                        "kappa": 0.8,
                        "n_pairs": 34,
                    },
                    "manipulation": {
                        "ac1": intra_rater_ac1,
                        "ac1_ci": _ac1_ci_block(intra_rater_ac1),
                        "kappa": 0.8,
                        "n_pairs": 34,
                    },
                },
                "H4": {
                    "hand_count": {
                        "ac1": h4_hand_count_ac1,
                        "ac1_ci": _ac1_ci_block(h4_hand_count_ac1),
                        "kappa": 0.7,
                        "raw_agreement": 0.9,
                    },
                    "manipulation": {
                        "ac1": h4_manipulation_ac1,
                        "ac1_ci": _ac1_ci_block(h4_manipulation_ac1),
                        "kappa": 0.7,
                        "raw_agreement": 0.9,
                    },
                    "holds": h4_hand_count_ac1 > h4_manipulation_ac1,
                },
                "H5": {
                    "egocentric": {"n": 33, "error_rate": h5_ego_error},
                    "epic_kitchens": {"n": 30, "error_rate": h5_epic_error},
                    "diff_pp": h5_diff_pp,
                    "epic_kitchens_higher": h5_epic_error > h5_ego_error,
                    "holds": h5_diff_pp >= 5.0,
                },
                "ppi": {
                    "G200-ego": {"manipulation": _ppi_block(corpus="egocentric-10k", published=0.9166)},
                    "G200-ego4d": {"manipulation": _ppi_block(corpus="ego4d", published=0.5007)},
                },
                "H7_calibration": {
                    "hand_count": {
                        "judge": "qwen3-vl",
                        "task": "hand_count",
                        "subset": "G200-primary-labelled",
                        "confidence_kind": "logprob",
                        "ece": 0.15,
                        "bins": [{"lo": 0.9, "hi": 1.0, "n": 92, "mean_conf": 0.997, "accuracy": 0.85}],
                        "note": "test fixture",
                        "n": 93,
                    },
                    "manipulation": {
                        "judge": "qwen3-vl",
                        "task": "manipulation",
                        "subset": "G200-primary-labelled",
                        "confidence_kind": "logprob",
                        "ece": 0.06,
                        "bins": [{"lo": 0.9, "hi": 1.0, "n": 92, "mean_conf": 0.997, "accuracy": 0.93}],
                        "note": "test fixture",
                        "n": 93,
                    },
                },
            }
        )
    )


def test_intra_rater_claim_warns_when_below_the_070_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, intra_rater_ac1=0.60)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _intra_rater_claim()

    assert "WARNING" in claim.statement


def test_intra_rater_claim_no_warning_above_the_070_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, intra_rater_ac1=0.90)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _intra_rater_claim()

    assert "WARNING" not in claim.statement
    assert "iid bootstrap CI" in claim.statement


def test_h4_claim_reports_predicted_direction_when_hand_count_ac1_is_higher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, h4_hand_count_ac1=0.90, h4_manipulation_ac1=0.80)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _h4_claim()

    assert "predicted direction" in claim.statement
    assert "OPPOSITE" not in claim.statement
    assert "iid bootstrap CI" in claim.statement


def test_h4_claim_reports_opposite_direction_when_manipulation_ac1_is_higher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, h4_hand_count_ac1=0.70, h4_manipulation_ac1=0.90)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _h4_claim()

    assert "OPPOSITE" in claim.statement


def test_h5_claim_flags_reversed_direction_when_egocentric_error_is_higher(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, h5_ego_error=0.10, h5_epic_error=0.0)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _h5_claim()

    assert "REVERSED" in claim.statement
    assert "NOT met" in claim.statement


def test_h5_claim_reports_met_when_threshold_and_direction_both_hold(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path, h5_ego_error=0.05, h5_epic_error=0.15)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _h5_claim()

    assert "REVERSED" not in claim.statement
    assert "met." in claim.statement


def test_ppi_claims_produce_prevalence_estimate_typed_claims_with_the_real_natural_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claims, estimates = _ppi_claims()

    assert len(claims) == 2  # one per fixture domain in _write_wave4_fixture's "ppi" block
    assert len(estimates) == 2
    refs = {c.record_ref for c in claims}
    assert "egocentric-10k/manipulation/P0b/qwen3-vl" in refs
    assert "ego4d/manipulation/P0b/qwen3-vl" in refs
    for claim in claims:
        assert claim.record_type == "PrevalenceEstimate"


def test_h7_claim_reports_real_ece_and_the_p7_deviation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "wave4.json"
    _write_wave4_fixture(path)
    monkeypatch.setattr(emit_card, "_WAVE4_RESULTS_PATH", path)

    claim = _h7_claim()

    assert "0.1500" in claim.statement  # hand_count ECE
    assert "0.0600" in claim.statement  # manipulation ECE
    assert "P7" in claim.statement  # names the deviation, doesn't silently hide it
    assert "D060" in claim.statement
    assert claim.record_type != "PrevalenceEstimate"  # not pre-registered with a CI


# --- H6: real distillation cascade (D061) ------------------------------------------------------


def _write_rung1_fixture(
    path: Path,
    *,
    fidelity: float = 0.69,
    floor_reached: bool = True,
    agreement_floor: float = 0.84,
    coverage: float = 0.40,
) -> None:
    holds = floor_reached and agreement_floor >= 0.80 and coverage >= 0.70
    payload: dict[str, object] = {
        "backbone": "facebook/dinov2-small",
        "n_train": 600,
        "n_fidelity_holdout": 150,
        "fidelity_vs_gemini_2_5_flash": fidelity,
        "n_calibration_gold": 46,
        "n_eval_gold": 47,
        "target_floor": 0.80,
        "target_coverage": 0.70,
        "floor_reached": floor_reached,
        "holds": holds,
    }
    if floor_reached:
        payload["agreement_floor"] = agreement_floor
        payload["coverage"] = coverage
    else:
        payload["error"] = "target floor 0.8 is unreachable at any coverage > 0 on the given held-out gold"
    path.write_text(json.dumps(payload))


def test_h6_claim_does_not_hold_when_coverage_misses_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "rung1.json"
    _write_rung1_fixture(path, agreement_floor=0.84, coverage=0.40)
    monkeypatch.setattr(emit_card, "_RUNG1_RESULTS_PATH", path)

    claim = _h6_claim()

    assert "does NOT hold" in claim.statement
    assert "dinov2-small" in claim.statement
    assert "D034" in claim.statement
    assert claim.record_type != "PrevalenceEstimate"


def test_h6_claim_holds_when_floor_and_coverage_both_met(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "rung1.json"
    _write_rung1_fixture(path, agreement_floor=0.85, coverage=0.75)
    monkeypatch.setattr(emit_card, "_RUNG1_RESULTS_PATH", path)

    claim = _h6_claim()

    assert "it holds." in claim.statement
    assert "does NOT hold" not in claim.statement


def test_h6_claim_reports_unreachable_floor_explicitly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "rung1.json"
    _write_rung1_fixture(path, floor_reached=False)
    monkeypatch.setattr(emit_card, "_RUNG1_RESULTS_PATH", path)

    claim = _h6_claim()

    assert "UNREACHABLE" in claim.statement
    assert "does not hold" in claim.statement.lower()
