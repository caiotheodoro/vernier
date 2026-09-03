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
from emit_card import _h1_h1b_claims, _h3_claim, _h8_claim, _unmet_claims  # noqa: E402


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
    assert len(items) == 6  # H2, H4, H5, H6, H7, Result 2 -- H1/H1b/H3 are now real Claims (D054/D055)
    for item in items:
        assert item.reason.strip()
        assert "BLOCKER:" in item.reason


def test_unmet_claims_cover_every_still_blocked_hypothesis() -> None:
    items = {i.item for i in _unmet_claims()}
    for tag in ["H2 ", "H4 ", "H5 ", "H6 ", "H7 ", "Result 2"]:
        assert any(tag in item for item in items), f"missing {tag!r} in unmet claims"
    # H1/H1b/H3 moved to real Claims (D054/D055's full-N run) -- must not still be listed as
    # blocked, or the card would understate real, completed progress.
    for tag in ["H1 ", "H1b", "H3 "]:
        assert not any(tag in item for item in items), f"{tag!r} should no longer be unmet"


def test_blockers_are_named_specifically() -> None:
    # H2/Result 2's blocker is a real, checked access gap (D044), not "HF_TOKEN not configured"
    # (it is configured); H4-H7's blocker is purely the human labelling itself, the tooling for
    # which is real and ready.
    items = _unmet_claims()
    reasons = " ".join(i.reason for i in items)
    assert "D044" in reasons
    assert "NOT authorized" in reasons
    assert "600 primary + 100 retest human labels" in reasons


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
