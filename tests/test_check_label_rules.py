"""`scripts/check_label_rules.py` and the rule it enforces (docs/DECISIONS.md D078)."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_label_rules import check  # noqa: E402

from vernier.labels.rules import rule_violations, violates_zero_hands_rule  # noqa: E402
from vernier.labels.store import HumanLabelStore  # noqa: E402
from vernier.models import HumanLabel  # noqa: E402


def _label(frame_id: str, hands_visible: int, manipulation: bool, pass_: str = "primary") -> HumanLabel:
    return HumanLabel.model_validate(
        {
            "frame_id": frame_id,
            "rater": "R1",
            "pass": pass_,
            "rubric_rev": "1.2.0",
            "hands_visible": hands_visible,
            "manipulation": manipulation,
            "edge_case": [],
            "difficulty": "easy",
            "note": "",
            "labelled_at": datetime.now(timezone.utc).isoformat(),
            "seconds_spent": 10,
        }
    )


def test_zero_hands_with_manipulation_is_the_only_combination_that_violates() -> None:
    assert violates_zero_hands_rule(0, True)
    assert not violates_zero_hands_rule(0, False)
    assert not violates_zero_hands_rule(1, True)
    assert not violates_zero_hands_rule(2, True)


def test_rule_violations_names_the_rubric_rule_rather_than_returning_a_bare_bool() -> None:
    assert rule_violations(_label("a", 0, True)) == [
        "RUBRIC.md rule 12: zero hands visible implies manipulation is false"
    ]
    assert rule_violations(_label("a", 2, True)) == []


def test_check_fails_on_a_violating_label_in_a_live_pass(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "caio")
    store.write(_label("clean", 2, True))
    store.write(_label("bad", 0, True))
    assert check(tmp_path) == 1


def test_check_passes_when_every_live_label_is_clean(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "caio")
    store.write(_label("clean", 0, False))
    assert check(tmp_path) == 0


def test_an_archived_pass_is_not_checked_so_the_record_of_what_was_collected_stands(
    tmp_path: Path,
) -> None:
    """D077's archive still breaks rule 12 and has to keep breaking it."""
    store = HumanLabelStore(tmp_path / "caio")
    store.write(_label("clean", 0, False))
    (tmp_path / "caio" / "review_first_unblinded.json").write_bytes(
        (tmp_path / "caio" / "primary.json").read_bytes().replace(b'"manipulation":false', b'"manipulation":true')
    )
    assert check(tmp_path) == 0
