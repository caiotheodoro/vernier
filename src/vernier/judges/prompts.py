"""Prompt registry. `P0a`/`P0b` are pinned verbatim in `docs/upstream/`; `P1`-`P7` are fixed
in `docs/PRE-REGISTRATION.md`. No variant is added after that file is frozen.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Callable

from vernier.models import PromptVariant

__all__ = ["PromptVariant", "load_prompt"]

# Repo root is four levels up from this file (judges/ -> vernier/ -> src/ -> root).
_UPSTREAM_DIR = Path(__file__).resolve().parents[3] / "docs" / "upstream"

_TASK_UPSTREAM_STEM = {"hand_count": "hand_count", "manipulation": "active_manipulation"}


def _check_task(task: str) -> None:
    if task not in _TASK_UPSTREAM_STEM:
        raise ValueError(
            f"unknown task {task!r}; load_prompt only knows 'hand_count' and 'manipulation'"
        )


@lru_cache(maxsize=None)
def _read_upstream(source: str, task: str) -> str:
    """Read one `docs/upstream/{source}-{stem}.txt` file. Cached: these files never change
    at runtime, and every P1-P7 derivation re-reads the P0b text they're built from."""
    stem = _TASK_UPSTREAM_STEM[task]
    return (_UPSTREAM_DIR / f"{source}-{stem}.txt").read_text()


# --- P1-P4: hand-count rule variants, each one documented textual change on top of P0b -------
#
# PRE-REGISTRATION.md gives literal wording for the rule that's tightened or removed (it quotes
# the existing P0b clauses being changed), but not for the new clauses P3/P4 add -- it names the
# instruction ("a gloved hand counts as a hand", "reflections or on screens do not count") without
# giving pinned sentence text. The wording below for P3/P4 is a faithful, minimal construction of
# the documented change, NOT pinned upstream text -- flagged here and in the final report.

_HC_DIRECTLY_VISIBLE = "• Only count hands that are directly visible.\n"
_HC_UNAMBIGUOUS = "• Only count hands that are clearly and unambiguously visible.\n"
_HC_FINGERTIP = "• Any amount of visibility counts (even fingertips).\n"
_HC_GLOVE = "• A gloved hand counts as a hand.\n"
_HC_REFLECTION = "• Hands seen only in a reflection or on a screen do not count.\n"
_HC_RETURN_LINE = "• Return only one of: 0, 1, 2. No extra words."
_HC_RETURN_WITH_CONFIDENCE = (
    "• Return one of: 0, 1, 2, followed by a comma and a confidence value between "
    "0.0 and 1.0. No extra words."
)


def _p1_hand_count(text: str) -> str:
    # "clearly and unambiguously visible", fingertip clause removed (PRE-REGISTRATION.md P1).
    text = text.replace(_HC_DIRECTLY_VISIBLE, _HC_UNAMBIGUOUS)
    return text.replace(_HC_FINGERTIP, "")


def _p2_hand_count(text: str) -> str:
    # The fingertip line deleted entirely, nothing else changed (PRE-REGISTRATION.md P2).
    return text.replace(_HC_FINGERTIP, "")


def _p3_hand_count(text: str) -> str:
    # Gloved-hand instruction added -- not pinned wording, see module docstring above.
    return text.replace(_HC_FINGERTIP, _HC_FINGERTIP + _HC_GLOVE)


def _p4_hand_count(text: str) -> str:
    # Reflection/screen exclusion added -- not pinned wording, see module docstring above.
    return text.replace(_HC_FINGERTIP, _HC_FINGERTIP + _HC_REFLECTION)


def _p7_hand_count(text: str) -> str:
    return text.replace(_HC_RETURN_LINE, _HC_RETURN_WITH_CONFIDENCE)


# --- P5-P6: manipulation definition variants -- PRE-REGISTRATION.md describes the change, not
# literal sentence text, for either one. Both are faithful-but-not-pinned constructions.

_AM_RULES_HEADER = "Rules:\n"
_AM_CONTACT_REQUIRED = (
    "• Manipulation requires visible contact with the object; reaching toward it "
    "without touching does not count.\n"
)
_AM_REACHING_COUNTS = (
    "• Reaching toward an object counts as manipulation, even without touching it.\n"
)
_AM_RESPOND_LINE = '• Respond only with: "yes" or "no."'
_AM_RESPOND_WITH_CONFIDENCE = (
    '• Respond with "yes" or "no", followed by a comma and a confidence value between '
    "0.0 and 1.0. No extra words."
)


def _p5_manipulation(text: str) -> str:
    return text.replace(_AM_RULES_HEADER, _AM_RULES_HEADER + _AM_CONTACT_REQUIRED)


def _p6_manipulation(text: str) -> str:
    return text.replace(_AM_RULES_HEADER, _AM_RULES_HEADER + _AM_REACHING_COUNTS)


def _p7_manipulation(text: str) -> str:
    return text.replace(_AM_RESPOND_LINE, _AM_RESPOND_WITH_CONFIDENCE)


# Each variant's documented change targets one task. PRE-REGISTRATION.md gives P1-P4 no effect
# on "manipulation" and P5-P6 none on "hand_count"; a missing entry here means "return P0b for
# that task, unmodified" -- deliberate, not an oversight (see report to reviewer).
_VARIANT_TRANSFORMS: dict[str, dict[str, Callable[[str], str]]] = {
    "P1": {"hand_count": _p1_hand_count},
    "P2": {"hand_count": _p2_hand_count},
    "P3": {"hand_count": _p3_hand_count},
    "P4": {"hand_count": _p4_hand_count},
    "P5": {"manipulation": _p5_manipulation},
    "P6": {"manipulation": _p6_manipulation},
    "P7": {"hand_count": _p7_hand_count, "manipulation": _p7_manipulation},
}


def load_prompt(variant: PromptVariant, *, task: str) -> str:
    """Return the pinned prompt text for `variant` and `task` ("hand_count" or "manipulation").

    `P0a`/`P0b` load verbatim from `docs/upstream/`, cached in-process after first read (the
    files are static for the life of the run). `P1`-`P7` are derived from `P0b`'s text for the
    given task by applying the single documented change PRE-REGISTRATION.md describes for that
    variant; where the pre-registration names the change but not its literal wording (P3, P4,
    P5, P6, and the confidence-schema addition in P7), the inserted sentence is a faithful,
    minimal construction of the described change, not pinned upstream text -- see the comments
    above each `_p*` function. A variant whose documented change targets only the other task
    (e.g. `P1` under `task="manipulation"`) returns `P0b`'s text for the given task unmodified,
    since PRE-REGISTRATION.md defines no transformation there.

    `P0` is the hand-count prompt "run once" (PRE-REGISTRATION.md: identical across P0a/P0b
    apart from an apostrophe glyph). `P0a`/`P0b` for hand_count still differ in incidental
    whitespace beyond that glyph (line-wrap and a trailing newline), so `P0` cannot alias both
    byte-for-byte; `P0b` -- the file actually shipped in `prompts/`, not the dataset-card
    excerpt -- is picked as the single canonical source, read once. `P0` is undefined for
    "manipulation": P0a/P0b genuinely diverge there (D014/D015), so no single unified P0 exists
    for that task.
    """
    _check_task(task)

    if variant == "P0":
        if task != "hand_count":
            raise ValueError(
                "P0 is only defined for task='hand_count' -- 'manipulation' has no unified P0, "
                "P0a and P0b diverge there (see docs/DECISIONS.md D014)"
            )
        return _read_upstream("P0b", task)

    if variant in ("P0a", "P0b"):
        return _read_upstream(variant, task)

    base = _read_upstream("P0b", task)
    transform = _VARIANT_TRANSFORMS[variant].get(task)
    return base if transform is None else transform(base)
