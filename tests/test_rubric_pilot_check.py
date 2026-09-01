from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from rubric_pilot_check import (  # noqa: E402
    extract_closed_tags,
    extract_referenced_tags,
    find_orphan_tags,
    find_undeclared_tags,
)

SYNTHETIC_RUBRIC = """\
# Fixture rubric

## Task 1 -- example

1. **Rule one.** Something happens. Tagged `alpha`.
2. **Rule two.** Something else, tag `beta`.
3. **Rule three.** Mentions a case tagged `gamma` in passing.

## Tag list, closed

`alpha`, `beta`, `gamma`, `delta`.

## Procedure

Nothing else matters for this fixture.
"""


def test_extract_closed_tags() -> None:
    assert extract_closed_tags(SYNTHETIC_RUBRIC) == {"alpha", "beta", "gamma", "delta"}


def test_extract_referenced_tags_matches_all_three_surface_forms() -> None:
    # "Tagged `x`" (capitalized), "tag `x`" (lowercase imperative), "tagged `x`" (lowercase
    # past-tense) -- docs/RUBRIC.md genuinely uses all three for the same instruction.
    assert extract_referenced_tags(SYNTHETIC_RUBRIC) == {"alpha", "beta", "gamma"}


def test_find_orphan_tags_catches_closed_list_tag_no_rule_attaches() -> None:
    assert find_orphan_tags(SYNTHETIC_RUBRIC) == {"delta"}


def test_find_undeclared_tags_empty_when_every_reference_is_closed_list() -> None:
    assert find_undeclared_tags(SYNTHETIC_RUBRIC) == set()


def test_find_undeclared_tags_catches_reference_outside_closed_list() -> None:
    text_with_stray_tag = SYNTHETIC_RUBRIC.replace(
        "Mentions a case tagged `gamma` in passing.",
        "Mentions a case tagged `gamma` in passing, and another tagged `epsilon`.",
    )
    assert find_undeclared_tags(text_with_stray_tag) == {"epsilon"}


def test_real_rubric_is_internally_consistent() -> None:
    # The pilot check originally found `dark` orphaned -- in the closed tag list, but no rule
    # ever instructed tagging a frame `dark` on its own (`docs/RUBRIC.md`'s old Rule 9
    # mentioned darkness only as one cause of `undecidable`). Fixed in RUBRIC.md 1.2.0 (new
    # Rule 9) and recorded in `docs/DECISIONS.md` D036. This asserts the fixed state stays
    # fixed -- a future regression here means RUBRIC.md was revised and needs a follow-up
    # decision, not a silent test update.
    repo_root = Path(__file__).resolve().parent.parent
    text = (repo_root / "docs" / "RUBRIC.md").read_text()
    assert find_orphan_tags(text) == set()
    assert find_undeclared_tags(text) == set()
