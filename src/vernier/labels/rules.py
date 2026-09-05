"""Rubric rules that a label must satisfy, checkable without reading the rubric prose.

`docs/RUBRIC.md` carries twelve numbered rules for the two tasks. Most are judgment the rater
applies while looking at a frame and no program can check. Rule 12 is not: it is a hard
consistency constraint between the two answers, and it went unenforced through 700-odd labels
until `docs/DECISIONS.md` D078 found seven records breaking it, two of them in the primary pass
that backs H4, H5 and every PPI estimate.

Deliberately not a pydantic validator on `HumanLabel`. A validator would refuse to *load* the
already-collected labels, which turns a data question into an outage and makes the violation
harder to see rather than easier. The rule is enforced where a label is created, and reported
across what already exists by `scripts/check_label_rules.py`.
"""

from __future__ import annotations

from vernier.models import HumanLabel

# docs/RUBRIC.md rule 12, verbatim: "Zero hands visible implies `false`. No hands, no hand
# manipulation."
ZERO_HANDS_RULE = "RUBRIC.md rule 12: zero hands visible implies manipulation is false"


def violates_zero_hands_rule(hands_visible: int, manipulation: bool) -> bool:
    """Whether this pair of answers breaks rule 12."""
    return hands_visible == 0 and manipulation


def rule_violations(label: HumanLabel) -> list[str]:
    """Every rule this label breaks, as human-readable strings. Empty when the label is clean."""
    if violates_zero_hands_rule(label.hands_visible, label.manipulation):
        return [ZERO_HANDS_RULE]
    return []
