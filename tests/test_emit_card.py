"""Tests for `scripts/emit_card.py`'s claim-construction logic.

Does not call `main()` here -- that writes the real, committed `MEASUREMENT_CARD.json` at the
repo root, which is `make card`'s job (regenerate-and-commit, the same pattern
`scripts/generate_fixtures.py` already uses for `tests/fixtures/`), not something to trigger as
a side effect of every `pytest` run.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from emit_card import _h8_claim, _unmet_claims  # noqa: E402


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
    assert len(items) == 9  # H1, H1b, H2, H3, H4, H5, H6, H7, Result 2
    for item in items:
        assert item.reason.strip()
        assert "BLOCKER:" in item.reason


def test_unmet_claims_cover_every_pre_registered_hypothesis() -> None:
    items = {i.item for i in _unmet_claims()}
    for tag in ["H1 ", "H1b", "H2 ", "H3 ", "H4 ", "H5 ", "H6 ", "H7 ", "Result 2"]:
        assert any(tag in item for item in items), f"missing {tag!r} in unmet claims"


def test_credential_blockers_are_named_specifically() -> None:
    items = _unmet_claims()
    reasons = " ".join(i.reason for i in items)
    assert "GEMINI_API_KEY" in reasons
    assert "ANTHROPIC_API_KEY" in reasons
    assert "HF_TOKEN" in reasons
    assert "600 primary human labels" in reasons
