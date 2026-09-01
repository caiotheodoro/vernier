"""Rubric pilot: an offline self-check of `docs/RUBRIC.md`'s own internal consistency, run in
place of a human pilot-labelling pass (`docs/HANDOFF.md` P1 tier; resolved with Caio as an
offline check, no labelling time spent).

Checks two things a human pilot would otherwise be the first to notice:

1. **Orphan tags** -- a tag in the closed list (`## Tag list, closed`) that no rule's prose ever
   attaches via a `` Tagged `x` `` annotation. An orphan tag means a rater has no written rule
   telling them when to apply it.
2. **Undeclared tags** -- the reverse: a `` Tagged `x` `` annotation whose tag isn't in the
   closed list. This would itself violate `RUBRIC.md`'s own stated rule ("a frame needing a tag
   outside this list means the rubric is incomplete").

This is a documentation-consistency check, not a data-integrity gate like
`check_eval_parquets.py` -- findings here become a `docs/DECISIONS.md` entry (the same
correction discipline every other rubric revision has used), not a blocking assertion, since
`RUBRIC.md` is frozen prose that only a human amends.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

TAG_LIST_HEADING = "## Tag list, closed"
# The rubric's prose uses four surface forms for the same instruction: "Tagged `x`."/"Tag `x`"
# (sentence-initial, capitalized), "tag `x`"/"tagged `x`" (lowercase, mid-sentence) -- all four
# must match, or a real annotation reads as an orphan. `\s+` (not a literal space) because a
# markdown line wrap can put the backtick on the next line for a long list item.
TAGGED_RE = re.compile(r"\btag(?:ged)?\s+`([a-z-]+)`", re.IGNORECASE)
BACKTICK_TAG_RE = re.compile(r"`([a-z-]+)`")


def extract_closed_tags(rubric_text: str) -> set[str]:
    """The tags listed under `## Tag list, closed`, up to the next blank-line-terminated
    paragraph."""
    start = rubric_text.index(TAG_LIST_HEADING) + len(TAG_LIST_HEADING)
    end = rubric_text.index("\n\n", start + 2)
    # +2 skips the heading's own trailing blank line so `end` lands on the list paragraph's own
    # terminator, not the heading's.
    block = rubric_text[start:end]
    return set(BACKTICK_TAG_RE.findall(block))


def extract_referenced_tags(rubric_text: str) -> set[str]:
    """Every tag a rule's prose attaches via a `` Tagged `x` `` annotation."""
    return set(TAGGED_RE.findall(rubric_text))


def find_orphan_tags(rubric_text: str) -> set[str]:
    """Closed-list tags no rule ever instructs a rater to apply."""
    return extract_closed_tags(rubric_text) - extract_referenced_tags(rubric_text)


def find_undeclared_tags(rubric_text: str) -> set[str]:
    """`` Tagged `x` `` annotations whose tag isn't in the closed list."""
    return extract_referenced_tags(rubric_text) - extract_closed_tags(rubric_text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--rubric",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "docs" / "RUBRIC.md",
    )
    args = parser.parse_args(argv)

    text = args.rubric.read_text()
    orphans = find_orphan_tags(text)
    undeclared = find_undeclared_tags(text)

    if not orphans and not undeclared:
        print(f"rubric-pilot-check: {args.rubric} is internally consistent, no findings")
        return 0

    if orphans:
        print(f"ORPHAN TAGS (in the closed list, no rule ever attaches them): {sorted(orphans)}")
    if undeclared:
        print(f"UNDECLARED TAGS (attached by a rule, not in the closed list): {sorted(undeclared)}")
    print("Findings belong in docs/DECISIONS.md, per the rubric's own correction discipline.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
