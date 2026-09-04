"""Draws every sample in `docs/PRE-REGISTRATION.md`'s dependency order and persists each via
`sampling.membership.write_membership` -- the real, missing prerequisite this session found:
`membership.py`'s own docstring states "membership is written to disk before any judge is
called on it", but nothing previously actually ran `draw_sample` end to end and wrote the
result. Every subset sample (`P2k`, `G200-*`, `R100`) reads its parent's membership straight
off disk (`sampling.draw._load_parent_membership`), so without this, drawing any of them raises
`MembershipNotFoundError` -- and `labels/tool.py`'s `_pending_frames` (Wave 3's real frame
pool: `G200-ego`/`G200-ego4d`/`G200-epic` for the primary pass, `R100` for the blind retest)
has nothing to read either.

Dependency order, per `docs/PRE-REGISTRATION.md`'s "Samples" table:
`E10k-ego`/`E10k-ego4d`/`E10k-epic` (roots, no parent) -> `P2k` (parent `E10k-ego`) ->
`G200-ego` (parent `P2k`), `G200-ego4d` (parent `E10k-ego4d`), `G200-epic` (parent `E10k-epic`)
-> `R100` (union of the three `G200-*` sets).

`S10k-U`/`S10k-S` are real, expected failures here (`docs/DECISIONS.md` D044: the raw
Egocentric-10K corpus adapter is unwired, blocked on an HF access grant this account doesn't
have) -- skipped with a clear message, not a reason to fail the rest of the DAG. Absence is
explicit (`CONTRACTS.md` rule 2), not silently swallowed.
"""

from __future__ import annotations

import sys
from pathlib import Path

from vernier.sampling.draw import SampleName, draw_sample
from vernier.sampling.membership import write_membership

_MEMBERSHIP_ROOT = Path("data/membership")  # matches sampling/draw.py's own `_MEMBERSHIP_ROOT`
# -- deliberately re-declared, not imported, per D033's no-shared-file-edits convention already
# established across this codebase for small constants like this one.

# Root-first, dependency order -- a sample is only drawable once every sample it reads
# membership from (sampling/draw.py's `_PARENT`/`_R100_PARENTS`) has already been drawn and
# written in this same run.
_DRAW_ORDER: tuple[SampleName, ...] = (
    "E10k-ego",
    "E10k-ego4d",
    "E10k-epic",
    "S10k-U",
    "S10k-S",
    "P2k",
    "G200-ego",
    "G200-ego4d",
    "G200-epic",
    "R100",
    # docs/DECISIONS.md D066: Build AI's current-product evaluation release -- a root, no
    # parent, and no subset sample reads membership from it (a disclosed, non-pre-registered
    # additional check, not part of the P2k/G200-*/R100 dependency chain above).
    "E100k-ego",
)


def draw_and_persist_all(root: Path = _MEMBERSHIP_ROOT) -> dict[str, int | str]:
    """Draw every sample in `_DRAW_ORDER`, persisting each as it succeeds so later samples in
    the order can read it back as parent membership. Returns `{sample: n_frames}` for each
    sample actually drawn, or `{sample: "skipped: <reason>"}` for one that couldn't be
    (currently only `S10k-U`/`S10k-S`, per D044).
    """
    results: dict[str, int | str] = {}
    for sample in _DRAW_ORDER:
        try:
            frames = draw_sample(sample)
        except NotImplementedError as exc:
            results[sample] = f"skipped: {exc}"
            continue
        write_membership(sample, frames, root)
        results[sample] = len(frames)
    return results


def main(argv: list[str] | None = None) -> int:
    results = draw_and_persist_all()
    for sample, outcome in results.items():
        print(f"{sample}: {outcome}")
    n_skipped = sum(1 for v in results.values() if isinstance(v, str))
    print(f"\n{len(results) - n_skipped} samples drawn and persisted, {n_skipped} skipped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
