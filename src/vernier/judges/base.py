"""One adapter per judge behind a single interface: frame in, `JudgeResponse` out.

Owns: prompt-variant substitution, response parsing, `status` classification, cost and
latency accounting, retry policy, and recording `judge_rev` per response. Depends on:
`sampling` for frames, nothing else.

A judge never decides ground truth -- it is the object of measurement, not the oracle.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod

from vernier.models import Confidence, FrameRef, JudgeResponse, JudgeStatus
from vernier.judges.prompts import PromptVariant

__all__ = [
    "JudgeAdapter",
    "parse_hand_count_response",
    "parse_manipulation_response",
    "build_confidence",
]

# First-person refusal phrasing checked when no JSON object can be extracted at all. This is
# deliberately narrow: it is not a general refusal classifier, only a marker that the model
# declined rather than answered badly. Any malformed/non-JSON text that does NOT match one of
# these markers is classified "unparseable", not "refused" -- e.g. a truncated response or a
# model that answers in free prose without ever saying it is declining. A caller with a richer
# signal (e.g. an API-level content-filter block reason) should prefer that over this heuristic;
# this function only ever sees the model's raw text.
_REFUSAL_MARKERS = (
    "i cannot",
    "i can't",
    "i can not",
    "i'm unable",
    "i am unable",
    "cannot assist",
    "unable to assist",
    "as an ai",
    "i won't",
    "i will not",
    "i'm not able",
    "i am not able",
    "sorry, i",
    "sorry, but i",
)


# The real, verified answer format every prompt variant (P0-P7) actually specifies
# (`docs/DECISIONS.md` D043) -- never JSON. P0-P6: a bare value, "No extra words". P7: the same
# bare value, then a comma and a confidence number in [0, 1]. Case-insensitive (yes/no), and
# tolerant of a model wrapping the bare value in quotes/backticks or a trailing period despite
# the "no extra words" instruction -- that much formatting noise is not a content deviation.
# Anything else (extra prose, a missing value) is a real "no extra words" violation and is
# honestly unparseable, not coerced into "ok".
_VALUE_RE = re.compile(
    r"^\s*[\"'`]?\s*(?P<value>[0-2]|yes|no)\s*[\"'`]?\s*"
    r"(?:,\s*(?P<confidence>[0-9]*\.?[0-9]+))?\s*\.?\s*$",
    re.IGNORECASE,
)


def _match_value(raw: str) -> re.Match[str] | None:
    return _VALUE_RE.match(raw)


def _looks_like_refusal(raw: str) -> bool:
    """See `_REFUSAL_MARKERS` docstring above for what this does and does not check."""
    lowered = raw.lower()
    return any(marker in lowered for marker in _REFUSAL_MARKERS)


def parse_hand_count_response(raw: str) -> tuple[int | None, JudgeStatus]:
    """Parse a raw response to the hand-count prompt against the real, shipped bare-value
    format (`docs/DECISIONS.md` D043) -- never JSON.

    - A bare `0`, `1`, or `2` (optionally quoted/backticked, optionally followed by a P7-style
      `, <confidence>` or a trailing period) -> `(value, "ok")`.
    - Any other recognizable value token (e.g. `yes`/`no`, out of range) -> `(None,
      "unparseable")`.
    - No value token recoverable at all, and the text matches a first-person refusal marker
      (see `_REFUSAL_MARKERS`) -> `(None, "refused")`.
    - No value token recoverable and no refusal marker matched -> `(None, "unparseable")`.
    """
    match = _match_value(raw.strip())
    if match is None:
        return (None, "refused") if _looks_like_refusal(raw) else (None, "unparseable")

    value = match.group("value")
    if value not in ("0", "1", "2"):
        return None, "unparseable"
    return int(value), "ok"


def parse_manipulation_response(raw: str) -> tuple[bool | None, JudgeStatus]:
    """Parse a raw response to the manipulation prompt against the real, shipped bare-value
    format (`docs/DECISIONS.md` D043) -- never JSON.

    Same classification rules as `parse_hand_count_response`: a bare `yes`/`no` (case-
    insensitive) is `"ok"`; any other recognizable value token is `"unparseable"`; no value
    token falls back to the same refusal-marker heuristic.
    """
    match = _match_value(raw.strip())
    if match is None:
        return (None, "refused") if _looks_like_refusal(raw) else (None, "unparseable")

    value = match.group("value").lower()
    if value == "yes":
        return True, "ok"
    if value == "no":
        return False, "ok"
    return None, "unparseable"


def build_confidence(raw: str) -> Confidence:
    """Build a `Confidence` from a raw response's bare-value text, covering only the `"none"`
    and `"verbalized"` cases.

    Per `docs/UPSTREAM-FINDINGS.md` F8, the published Build AI prompts (P0a/P0b, and P1-P6
    which only touch the hand/manipulation rule text) never ask for a confidence value at all,
    so `kind="none"` is the correct result there. `P7` (`docs/PRE-REGISTRATION.md`) extends the
    answer with a comma-separated confidence number in [0, 1] (never JSON, `docs/DECISIONS.md`
    D043); when present and valid this returns `kind="verbalized"`. A confidence token that is
    present but out of range or not a number is treated as no usable signal and also falls back
    to `kind="none"` rather than raising, since a judge emitting a malformed confidence value is
    a parsing failure of that one field, not grounds to fail the whole response.

    This function does NOT handle `kind="logprob"`: per `docs/ARCHITECTURE.md`'s
    confidence-extraction seam, only judges with open-weights access (Qwen3-VL) can produce a
    logprob-based confidence, and doing so requires the raw model output (token logprobs) that
    this function -- which only sees the already-serialized response text -- does not have
    access to. The caller (that adapter) constructs `Confidence(kind="logprob", ...)` itself.
    """
    match = _match_value(raw.strip())
    if match is None or match.group("confidence") is None:
        return Confidence(kind="none", value=None)

    value = float(match.group("confidence"))
    if not 0 <= value <= 1:
        return Confidence(kind="none", value=None)

    return Confidence(kind="verbalized", value=value)


class JudgeAdapter(ABC):
    """Base interface every judge (closed API or open weights) implements."""

    #: The judge name as recorded on every `JudgeResponse` (e.g. "gemini-2.5-flash").
    judge: str

    @abstractmethod
    def judge_rev(self) -> str:
        """The model version string as reported by the API/checkpoint, at call time."""
        raise NotImplementedError

    @abstractmethod
    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        """Score one frame under one prompt variant. Never raises on a bad judge answer --
        an unparseable, refused, timed-out or erroring response is returned with the matching
        `status`, not thrown."""
        raise NotImplementedError
