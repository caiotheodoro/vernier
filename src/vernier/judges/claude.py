"""`ClaudeJudge` — second frontier judge, different lineage from Gemini.

Seam: confidence extraction. No confidence under P0a/P0b; verbalized under P7. Calibration is
per judge and never pooled across kinds -- this adapter must report the `Confidence.kind` it
actually has, not flatten it to a float.

Seam: `_call_claude` is the Wave 2 API seam (real Anthropic call); it raises `NotImplementedError`
here.

Design note (both-tasks-in-one-response): `JudgeResponse` requires `hands_visible` and
`manipulation` to be non-null together when `status == "ok"`, and both null otherwise
(`vernier.models.JudgeResponse._hands_visible_and_manipulation_null_iff_unparseable_or_worse`).
But `load_prompt` is per-task -- there is no single prompt covering both tasks at once. So
`judge_frame` calls `_call_claude` twice, once per task, and combines the two outcomes into one
`JudgeResponse`: only if BOTH parse to `"ok"` is the combined status `"ok"` with both fields set;
otherwise the combined status is the worse of the two per `_STATUS_SEVERITY` and BOTH fields are
null -- even if the other task's call actually succeeded. That is a real information loss: a
genuine, correctly parsed answer to one task is discarded whenever the other task's call fails,
because the schema has no room to represent a partial result. Worth a future contract revision
(e.g. a per-task status), not something to silently paper over here.
"""

from __future__ import annotations

from typing import Literal, cast

from vernier.judges.base import (
    JudgeAdapter,
    build_confidence,
    parse_hand_count_response,
    parse_manipulation_response,
)
from vernier.judges.prompts import PromptVariant, load_prompt
from vernier.models import FrameRef, JudgeResponse, JudgeStatus

# Worst-to-best. An "error"/"timeout" from either call outranks any parse-level outcome, since
# those mean the call itself didn't complete rather than that it completed with a bad answer.
_STATUS_SEVERITY: dict[JudgeStatus, int] = {
    "error": 4,
    "timeout": 3,
    "refused": 2,
    "unparseable": 1,
    "ok": 0,
}


def _combine_status(a: JudgeStatus, b: JudgeStatus) -> JudgeStatus:
    """The worse of two task outcomes, per `_STATUS_SEVERITY` (error > timeout > refused >
    unparseable > ok). `"ok"` only when both are `"ok"`.
    """
    return a if _STATUS_SEVERITY[a] >= _STATUS_SEVERITY[b] else b


# `judge_rev` placeholder: Wave 1 makes no live call, so there is no real model version string
# to report. This sentinel is clearly not a version Anthropic would ever issue -- it must never
# be mistaken for a fetched value.
_JUDGE_REV_PLACEHOLDER = "unresolved-wave2-live-call-required"


class ClaudeJudge(JudgeAdapter):
    """Second frontier judge, different lineage. No confidence under P0a/P0b; verbalized under P7."""

    judge = "claude"

    def judge_rev(self) -> str:
        return _JUDGE_REV_PLACEHOLDER

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        hand_count_prompt = load_prompt(prompt_variant, task="hand_count")
        manipulation_prompt = load_prompt(prompt_variant, task="manipulation")

        hc_raw, hc_latency, hc_cost = self._call_claude(frame, hand_count_prompt)
        man_raw, man_latency, man_cost = self._call_claude(frame, manipulation_prompt)

        hand_count, hc_status = parse_hand_count_response(hc_raw)
        manipulation, man_status = parse_manipulation_response(man_raw)

        status = _combine_status(hc_status, man_status)
        hands_visible: Literal[0, 1, 2] | None
        if status == "ok":
            # parse_hand_count_response guarantees hand_count in {0, 1, 2} whenever it returns
            # status "ok", and _combine_status is "ok" only when both parses were "ok".
            hands_visible = cast("Literal[0, 1, 2]", hand_count)
        else:
            hands_visible = None
            manipulation = None

        # Confidence: always built from the hand_count call's raw text, even when the
        # manipulation call also carries a confidence value (P7 sends the confidence-schema
        # addition to both task prompts). Picking one consistently -- rather than e.g. averaging
        # or preferring whichever is non-null -- keeps `Confidence` traceable to a single call's
        # raw text; hand_count is chosen arbitrarily since PRE-REGISTRATION.md gives no ordering
        # between the two tasks for this purpose.
        confidence = build_confidence(hc_raw)

        return JudgeResponse(
            frame_id=frame.frame_id,
            judge=self.judge,
            judge_rev=self.judge_rev(),
            prompt_variant=prompt_variant,
            hands_visible=hands_visible,
            manipulation=manipulation,
            confidence=confidence,
            raw=f"hand_count: {hc_raw}\nmanipulation: {man_raw}",
            status=status,
            latency_ms=hc_latency + man_latency,
            cost_usd=hc_cost + man_cost,
        )

    def _call_claude(self, frame: FrameRef, prompt_text: str) -> tuple[str, int, float]:
        """Wave 2 seam: the real Anthropic API call. Returns `(raw_response_text, latency_ms,
        cost_usd)` for one task's prompt against one frame.
        """
        raise NotImplementedError
