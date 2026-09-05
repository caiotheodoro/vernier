"""Drift lint (`docs/REVIEW.md` R10): fail if prose describing a design or state the project no
longer has appears in a public document. `AGENTS.md` rule 2 says a number the pipeline no
longer produces is a bug; this is the same rule applied to a *design* (the pre-D042 three-judge
panel, the pre-Wave-1 "documentation only" state) rather than a number.

**Deviates from R10's literal pattern list in one place, deliberately**: the reviewer's own
list includes a bare `gemini-2.5-flash` match, but that string is now legitimately correct in
many places (`docs/DECISIONS.md` D047: rung-1 trains on `gemini-2.5-flash`'s own *stored*
labels; `MODEL_CARD.md`'s targets row; `README.md`'s Result 2 section; this docstring). A
lint that fails on a model name regardless of context would immediately false-positive on the
D047/D048 fixes that corrected the real staleness -- checked live: 14 files legitimately
mention `gemini-2.5-flash` post-fix. Dropped from the pattern list for that reason; the other
four patterns are stale in every context, not just some.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Every one of these phrases describes a state or design the project no longer has, in every
# context -- unlike a bare model name, none of these has a legitimate current use.
_STALE_PATTERNS = (
    "three judges",
    "three-judge panel",
    "documentation only",
    "documentation-only",
    "no judge has been called",
    "JUDGES=gemini",
    "no human label exists",
    "no model has been trained",
    "no model trained",
    # D065 granted raw-corpus access, superseding D044's 403. Every phrase below asserts the
    # opposite as a *current* state. Added after D065/D068 fixed the card but left five prose
    # files still saying H2 was blocked on access -- the exact drift class R10 exists to catch,
    # invisible to the lint because no earlier pattern covered it.
    "blocked on gated corpus",
    "not authorized for the raw",
    "still-inaccessible gated raw corpus",
    "Nothing here is an engineering gap",
    # D072 closed H2, leaving Result 2 as the only unmet item. Six public files (README,
    # AGENTS, llms.txt, COVERAGE, HANDOFF, the card's own sample_definition in emit_card.py)
    # kept saying two items were blocked, or that the corpus draws did not exist -- the fourth
    # time this drift class has recurred. Every phrase below asserts a pre-D072 state.
    "two items blocked",
    "Two items remain",
    "Two hypotheses remain",
    "still not drawn",
    "raw corpus is inaccessible",
    "Not testable on the published protocol",
    # AGENTS.md carried the pre-D042 three-judge framing under a capitalisation the
    # "three judges" pattern (case-sensitive by design) could not see.
    "Three judges are not three",
    # D073 replaced ETHICS.md section 4's flat promise with a split policy. The old
    # sentence was repeated in eight other files that would have gone stale silently --
    # exactly what this lint exists to catch. The Space now ships 24 frames; any document
    # still saying none are is wrong, in every context.
    "No frames are republished",
    "No frame is republished",
    "no-republish policy",
    "No frame is copied into this Space",
    "No frame is redistributed anywhere",
    "never copied",
)

# Historical-record files: DECISIONS.md documents what WAS true and when it changed, by design;
# UPSTREAM-FINDINGS.md/LINEAGE.md/REVIEW.md quote or describe past states as facts about the
# past, not current design claims; WAVES.md's Wave-1 unit table is explicitly left as a
# historical record (its own docstring says so) rather than rewritten; RED-TEAM.md's own stated
# rule is that "Attack" paragraphs are "published unedited" once written, by design (its own
# header) -- an attack posed using the language of the flaw it describes is not itself a stale
# claim, and rewriting it to dodge a lint would violate the file's own discipline.
# `check_stale_prose.py` itself is exempt for the obvious reason: it is where the retired
# sentences are written down. Same class as DECISIONS.md -- a record of what is no longer
# true is not a claim that it is.
_EXEMPT_FILES = {
    "scripts/check_stale_prose.py",
    "docs/DECISIONS.md",
    "docs/UPSTREAM-FINDINGS.md",
    "docs/LINEAGE.md",
    "docs/REVIEW.md",
    "docs/WAVES.md",
    "docs/RED-TEAM.md",
}


def find_stale_prose(repo_root: Path) -> dict[str, list[tuple[int, str]]]:
    """Scan every tracked `.md` file under `repo_root`, plus `Makefile` and `llms.txt` (neither
    is `.md`, and both were previously invisible to this scan even though `llms.txt` carried
    the literal "documentation only" claim, undetected until a scorecard review found it by
    hand -- the same scope gap D064 already fixed once for `Makefile`), excluding
    `_EXEMPT_FILES` and anything under `docs/private/`, `docs/upstream/`, for
    `_STALE_PATTERNS`. Returns `{relative_path: [(line_number, pattern), ...]}` for every file
    with a hit."""
    hits: dict[str, list[tuple[int, str]]] = {}
    # D073 widened the scope again: the retired no-republish sentence also lived in
    # `space/src/App.tsx` and in two export scripts' docstrings, neither of which any
    # earlier scope could see.
    paths = (
        sorted(repo_root.rglob("*.md"))
        + sorted((repo_root / "space" / "src").rglob("*.tsx"))
        + sorted((repo_root / "scripts").glob("*.py"))
        + sorted((repo_root / "paper").rglob("*.tex"))
    + [repo_root / "Makefile", repo_root / "llms.txt"]
    )
    for path in paths:
        if not path.is_file():
            continue
        rel = path.relative_to(repo_root).as_posix()
        if rel in _EXEMPT_FILES:
            continue
        if rel.startswith("docs/private/") or rel.startswith("docs/upstream/"):
            continue
        if "/.git/" in f"/{rel}" or rel.startswith(".git/"):
            continue
        text = path.read_text()
        for line_no, line in enumerate(text.splitlines(), start=1):
            for pattern in _STALE_PATTERNS:
                if pattern in line:
                    hits.setdefault(rel, []).append((line_no, pattern))
    return hits


def main(argv: list[str] | None = None) -> int:
    hits = find_stale_prose(_REPO_ROOT)
    if not hits:
        print("check-stale-prose: no stale design language found")
        return 0

    print("check-stale-prose: FAILING -- stale design language found:")
    for rel, file_hits in hits.items():
        for line_no, pattern in file_hits:
            print(f"  {rel}:{line_no}: {pattern!r}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
