"""`Qwen3VLJudge` — the reproducibility anchor: open weights, no API keys required.

Seam: confidence extraction. Exposes logprob confidence (unlike the closed judges, which only
expose verbalized confidence under P7, and only as free-text the model chooses to emit).
Because this judge runs open weights, a per-token logprob-derived confidence can be computed
directly from the model's own output distribution regardless of prompt variant -- it does not
depend on the model volunteering a number in its answer text. Calibration is per judge and
never pooled across kinds (ARCHITECTURE.md).

Two calls per frame, one per task (hand_count, manipulation), combined into one `JudgeResponse`
-- same shape as `ClaudeJudge`/`GeminiJudge`, independently re-implemented here since these are
separate parallel units, not shared code.
"""

from __future__ import annotations

from typing import Literal, cast

from vernier.judges.base import JudgeAdapter, parse_hand_count_response, parse_manipulation_response
from vernier.judges.prompts import PromptVariant, load_prompt
from vernier.models import Confidence, FrameRef, JudgeResponse, JudgeStatus

# Severity order for combining the two per-task call statuses into one JudgeResponse.status:
# error > timeout > refused > unparseable > ok. Rationale: a hard failure on either call (error,
# timeout) means the pair produced no trustworthy answer at all and should dominate a softer
# failure on the other call; between the two soft-failure kinds, an explicit refusal is a more
# informative outcome than an unparseable response, so it outranks it; "ok" is the weakest and
# only wins when both calls succeeded.
_STATUS_SEVERITY: dict[JudgeStatus, int] = {
    "error": 4,
    "timeout": 3,
    "refused": 2,
    "unparseable": 1,
    "ok": 0,
}

# Wave 1 placeholder: an open-weights model's "revision" is a checkpoint identifier/hash
# resolved from the loaded weights (Wave 2/4), not fabricated here ahead of a real load.
_JUDGE_REV_PLACEHOLDER = "unresolved-wave1-qwen3vl"


def _combine_status(a: JudgeStatus, b: JudgeStatus) -> JudgeStatus:
    """Combine two per-task call statuses per the severity order documented above."""
    return a if _STATUS_SEVERITY[a] >= _STATUS_SEVERITY[b] else b


def _logprob_confidence(token_logprob: float | None) -> Confidence:
    """Build a `Confidence(kind="logprob", ...)` from a raw seam-returned logprob value.

    Mirrors `base.build_confidence`'s handling of an out-of-contract value: wrong type or out
    of [0, 1] is treated as no usable signal (not a reason to raise), so it falls back to
    `kind="none"` same as a null value does.
    """
    if token_logprob is None or isinstance(token_logprob, bool) or not isinstance(token_logprob, (int, float)):
        return Confidence(kind="none", value=None)
    value = float(token_logprob)
    if not 0 <= value <= 1:
        return Confidence(kind="none", value=None)
    return Confidence(kind="logprob", value=value)


class Qwen3VLJudge(JudgeAdapter):
    """The reproducibility anchor: open weights, no API keys required. Exposes logprob confidence."""

    judge = "qwen3-vl"

    def judge_rev(self) -> str:
        return _JUDGE_REV_PLACEHOLDER

    def _call_qwen3vl(self, frame: FrameRef, prompt_text: str) -> tuple[str, int, float, float | None]:
        """Wave 2/4 seam: real local-or-Modal inference call.

        Returns `(raw_response_text, latency_ms, cost_usd, token_logprob)`. `token_logprob` is
        the per-token logprob-derived confidence in [0, 1] when the loaded model exposes one for
        this call, else `None` (e.g. a prompt variant under which this judge chooses not to
        expose one). Not wired in Wave 1.
        """
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        hand_count_prompt = load_prompt(prompt_variant, task="hand_count")
        manipulation_prompt = load_prompt(prompt_variant, task="manipulation")

        hc_raw, hc_latency, hc_cost, hc_logprob = self._call_qwen3vl(frame, hand_count_prompt)
        am_raw, am_latency, am_cost, am_logprob = self._call_qwen3vl(frame, manipulation_prompt)

        hands_visible_raw, hc_status = parse_hand_count_response(hc_raw)
        manipulation, am_status = parse_manipulation_response(am_raw)

        status = _combine_status(hc_status, am_status)
        # `parse_hand_count_response` only ever returns an int here when `hc_status == "ok"`,
        # and only from {0, 1, 2} (base.py's contract) -- the cast narrows `int` to the
        # `JudgeResponse.hands_visible` Literal without re-validating what the parser already
        # guarantees.
        hands_visible: Literal[0, 1, 2] | None = (
            cast("Literal[0, 1, 2]", hands_visible_raw) if status == "ok" else None
        )
        if status != "ok":
            manipulation = None

        # Confidence sources from the hand-count call's token_logprob first, falling back to the
        # manipulation call's -- mirrors ClaudeJudge's P7 convention of sourcing confidence from
        # the hand-count call, applied here across both calls since either may expose one.
        confidence = _logprob_confidence(hc_logprob if hc_logprob is not None else am_logprob)

        return JudgeResponse(
            frame_id=frame.frame_id,
            judge=self.judge,
            judge_rev=self.judge_rev(),
            prompt_variant=prompt_variant,
            hands_visible=hands_visible,
            manipulation=manipulation,
            confidence=confidence,
            raw=f"{hc_raw}\n---\n{am_raw}",
            status=status,
            latency_ms=hc_latency + am_latency,
            cost_usd=hc_cost + am_cost,
        )
