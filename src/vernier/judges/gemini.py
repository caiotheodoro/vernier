"""`GeminiJudge` — the replication target: Build AI's own judge.

Seam: confidence extraction. No confidence under P0a/P0b; verbalized under P7. Calibration is
per judge and never pooled across kinds -- this adapter must report the `Confidence.kind` it
actually has, not flatten it to a float.

Resolution of the one-call-per-task-vs-both-fields ambiguity: `models.py`'s `JudgeResponse`
validator requires `hands_visible` and `manipulation` to be non-null together when
`status == "ok"`, and null together otherwise -- a response carrying only one of the two is
illegal at any status. `judges.prompts.load_prompt` only ever returns one task's prompt per
call, so `judge_frame` calls the `_call_gemini` seam twice (once for the hand_count prompt,
once for the manipulation prompt) and merges the two parses into a single `JudgeResponse`,
matching `CONTRACTS.md`'s example, which shows both fields populated from what is presented as
one logical judge call. `latency_ms`/`cost_usd` are the sum of both calls; `raw` holds both
verbatim texts (JSON-encoded, keyed by task) since the schema has only one `raw` field for what
is, under this merge, two underlying responses. Where the two calls disagree on status, the
worse one wins (`_STATUS_SEVERITY` below) and both parsed fields are dropped to null, per the
validator. Where the two calls disagree on confidence, the hand_count call's is canonical --
CONTRACTS.md gives no ordering rule between the two, so this is a documented, arbitrary
tie-break, not a derived requirement.
"""

from __future__ import annotations

import json
from typing import Literal, cast

from vernier.judges.base import (
    JudgeAdapter,
    build_confidence,
    parse_hand_count_response,
    parse_manipulation_response,
)
from vernier.judges.prompts import PromptVariant, load_prompt
from vernier.models import Confidence, FrameRef, JudgeResponse, JudgeStatus

# Worse status wins when hand_count and manipulation calls disagree. "ok" is never a max here
# since a mixed ok/non-ok pair always yields the non-ok status covering both fields.
_STATUS_SEVERITY: dict[JudgeStatus, int] = {
    "ok": 0,
    "unparseable": 1,
    "refused": 2,
    "timeout": 3,
    "error": 4,
}

# Wave 1 makes no live API call, so there is no real model version string to report. Wave 2
# resolves this from the live Gemini API response at call time.
_JUDGE_REV_UNRESOLVED = "unresolved (Wave 1: no live call; Wave 2 resolves from the API response)"


class GeminiJudge(JudgeAdapter):
    """The replication target: Build AI's own judge. No confidence under P0a/P0b; verbalized under P7."""

    judge = "gemini-2.5-flash"

    def judge_rev(self) -> str:
        return _JUDGE_REV_UNRESOLVED

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        hc_prompt = load_prompt(prompt_variant, task="hand_count")
        manip_prompt = load_prompt(prompt_variant, task="manipulation")

        raw_hc, latency_hc, cost_hc = self._call_gemini(frame, hc_prompt)
        raw_manip, latency_manip, cost_manip = self._call_gemini(frame, manip_prompt)

        hands_visible_raw, hc_status = parse_hand_count_response(raw_hc)
        manipulation, manip_status = parse_manipulation_response(raw_manip)

        status = self._merge_status(hc_status, manip_status)
        hands_visible: Literal[0, 1, 2] | None
        if status == "ok":
            # parse_hand_count_response guarantees hand_count in {0, 1, 2} whenever it returns
            # status "ok" (base.py); mypy can't narrow int -> Literal[0, 1, 2] on its own.
            hands_visible = cast(Literal[0, 1, 2], hands_visible_raw)
        else:
            hands_visible, manipulation = None, None

        confidence = build_confidence(raw_hc)

        return JudgeResponse(
            frame_id=frame.frame_id,
            judge=self.judge,
            judge_rev=self.judge_rev(),
            prompt_variant=prompt_variant,
            hands_visible=hands_visible,
            manipulation=manipulation,
            confidence=confidence,
            raw=json.dumps({"hand_count": raw_hc, "manipulation": raw_manip}),
            status=status,
            latency_ms=latency_hc + latency_manip,
            cost_usd=cost_hc + cost_manip,
        )

    @staticmethod
    def _merge_status(hc_status: JudgeStatus, manip_status: JudgeStatus) -> JudgeStatus:
        if hc_status == "ok" and manip_status == "ok":
            return "ok"
        return max((hc_status, manip_status), key=lambda s: _STATUS_SEVERITY[s])

    def _call_gemini(self, frame: FrameRef, prompt_text: str) -> tuple[str, int, float]:
        """Wave-2 seam: issue one real Gemini call for one task's prompt and return
        `(raw_response_text, latency_ms, cost_usd)`. Wave 1 is offline -- unwired here."""
        raise NotImplementedError(
            "GeminiJudge._call_gemini is wired to the live API in Wave 2; Wave 1 is offline"
        )
