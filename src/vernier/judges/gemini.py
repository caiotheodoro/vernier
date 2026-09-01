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

`_call_gemini` is wired to the real `google-genai` SDK (Wave 2) -- verified against the
installed package's own response types, not assumed: `types.Part.from_bytes(data=..., mime_type
=...)`, `response.text`, `response.usage_metadata.{prompt_token_count,candidates_token_count}`,
`response.model_version` all confirmed present on the installed SDK. Pricing
(`_INPUT_USD_PER_TOKEN`/`_OUTPUT_USD_PER_TOKEN`) is `gemini-2.5-flash`'s public per-token list
price at time of writing -- re-check before relying on it if pricing has since changed. Image
bytes for `frame` come from `_image_bytes_for`, a separate, still-unwired seam: resolving a
`FrameRef` to real pixel bytes needs the evaluation-parquet adapter
(`sampling.draw._candidate_frames`'s own Wave 2 seam) to have landed first, and is not
duplicated here. `judge_rev()` reports the most recently observed `response.model_version`,
which requires at least one real call to have happened -- unresolved otherwise.
"""

from __future__ import annotations

import json
import time
from typing import Literal, cast

from google import genai
from google.genai import types

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

_MODEL = "gemini-2.5-flash"

# Public per-token list price, USD, at time of writing -- re-verify before relying on this for
# a real cost figure if pricing has since changed. Image tokens are already folded into
# usage_metadata.prompt_token_count by the API; no separate image-token accounting is needed.
_INPUT_USD_PER_TOKEN = 0.30 / 1_000_000
_OUTPUT_USD_PER_TOKEN = 2.50 / 1_000_000

# Reported by judge_rev() before any real call has happened -- no live call means no real
# model version to report yet.
_JUDGE_REV_UNRESOLVED = "unresolved (no live call yet)"


class GeminiJudge(JudgeAdapter):
    """The replication target: Build AI's own judge. No confidence under P0a/P0b; verbalized under P7."""

    judge = "gemini-2.5-flash"

    def __init__(self) -> None:
        # Lazy: genai.Client() raises immediately if no API key is configured, and merely
        # constructing a GeminiJudge (e.g. to read .judge, or in a test that monkeypatches
        # _call_gemini and never touches the real client) must not require one.
        self._client_instance: genai.Client | None = None
        self._last_model_version = _JUDGE_REV_UNRESOLVED

    @property
    def _client(self) -> genai.Client:
        if self._client_instance is None:
            self._client_instance = genai.Client()
        return self._client_instance

    def judge_rev(self) -> str:
        return self._last_model_version

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

    def _image_bytes_for(self, frame: FrameRef) -> bytes:
        """Wave 2 seam: resolve `frame` to its real JPEG bytes.

        Not wired here -- needs the evaluation-parquet adapter
        (`sampling.draw._candidate_frames`'s own still-unwired Wave 2 seam) to supply a
        frame_id -> bytes lookup first, so the two seams aren't duplicated.
        """
        raise NotImplementedError(
            "GeminiJudge._image_bytes_for needs the evaluation-parquet adapter wired first"
        )

    def _call_gemini(self, frame: FrameRef, prompt_text: str) -> tuple[str, int, float]:
        """Issue one real `gemini-2.5-flash` call for one task's prompt against `frame`'s
        image, and return `(raw_response_text, latency_ms, cost_usd)`.

        `latency_ms` is wall-clock time around the call -- neither SDK response carries a
        latency/duration field of its own, confirmed against the installed `google-genai`
        package's own response type. `cost_usd` is computed from `usage_metadata`'s real token
        counts against `_INPUT_USD_PER_TOKEN`/`_OUTPUT_USD_PER_TOKEN` -- image tokens are
        already folded into `prompt_token_count` by the API, no separate accounting needed.
        `judge_rev()` becomes resolvable after this call via `response.model_version`.
        """
        image_bytes = self._image_bytes_for(frame)
        contents = [
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            prompt_text,
        ]
        start = time.monotonic()
        # generate_content's `contents` Union type doesn't type-check cleanly against a
        # str/Part list even though the installed SDK's own docs and source accept exactly
        # this shape at runtime (a stub-generation quirk in the Union arms' list variance, not
        # a real type error) -- verified by constructing this exact call pattern against the
        # installed package before relying on it.
        response = self._client.models.generate_content(model=_MODEL, contents=contents)  # type: ignore[arg-type]
        latency_ms = int((time.monotonic() - start) * 1000)

        self._last_model_version = response.model_version or self._last_model_version
        usage = response.usage_metadata
        input_tokens = (usage.prompt_token_count if usage else None) or 0
        output_tokens = (usage.candidates_token_count if usage else None) or 0
        cost_usd = input_tokens * _INPUT_USD_PER_TOKEN + output_tokens * _OUTPUT_USD_PER_TOKEN

        return response.text or "", latency_ms, cost_usd
