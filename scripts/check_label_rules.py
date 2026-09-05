"""Report human labels that break a machine-checkable rubric rule.

Shaped like `scripts/check_corpus_manifest.py`: it states what the rubric requires, states what
the collected data does, and exits nonzero on a mismatch rather than editing either.

Deliberately NOT part of `make validate`. `docs/DECISIONS.md` D078 corrected the seven records
that existed when this was written, so it passes today; wiring it into the gate would mean a
future violation blocks every commit in the repository, including the one that records the
rater's reasoning about it. A violation here is a question for the rater, not a broken build.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from typing import get_args  # noqa: E402

from vernier.labels.rules import rule_violations  # noqa: E402
from vernier.models import PassType  # noqa: E402
from vernier.labels.store import _LABEL_LIST_ADAPTER  # noqa: E402

_LABEL_ROOT = Path("data/labels")
_PASS_FILES = frozenset(get_args(PassType))


def check(root: Path = _LABEL_ROOT) -> int:
    found = 0
    checked = 0
    for path in sorted(root.rglob("*.json")):
        # Only live pass files are checked. `review_set*.json` is a plan, not labels, and
        # `review_first_unblinded.json` (D077) is an archive of what was actually collected --
        # it still breaks rule 12 and must keep breaking it, because editing a record of the
        # past to satisfy a rule found later is the failure this repository exists to object to.
        if path.stem not in _PASS_FILES:
            continue
        labels = _LABEL_LIST_ADAPTER.validate_json(path.read_bytes())
        checked += len(labels)
        for label in labels:
            for violation in rule_violations(label):
                found += 1
                print(
                    f"{path.relative_to(root.parent.parent) if root == _LABEL_ROOT else path}: "
                    f"{label.frame_id} ({label.pass_}) -- {violation} "
                    f"[hands_visible={label.hands_visible}, manipulation={label.manipulation}]"
                )
    if found:
        print(f"\ncheck-label-rules: {found} of {checked} labels break a rubric rule", file=sys.stderr)
        return 1
    print(f"check-label-rules: {checked} labels, none breaking a machine-checkable rubric rule")
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
