"""`Qwen3VLJudge` — the sole judge in the panel (`docs/DECISIONS.md` D042): open weights,
self-hosted (Modal, then AWS once Modal credits run out), no API key required.

`ClaudeJudge`/`GeminiJudge` (a second closed judge and the original replication target) are
retired -- `gemini-2.5-flash` is deprecated for new API keys and Anthropic is out of the panel
entirely, per D042. This module's own two-calls-per-frame merge pattern was originally
independently re-implemented across all three adapters (D033's "no shared-file edits" rule);
now it is simply the only one that remains.

Seam: confidence extraction. Exposes logprob confidence -- unlike the retired closed judges,
which only ever exposed verbalized confidence under P7, and only as free-text the model chose
to emit. Because this judge runs open weights, a per-token logprob-derived confidence can be
computed directly from the model's own output distribution regardless of prompt variant -- it
does not depend on the model volunteering a number in its answer text. Calibration is per judge
and never pooled across kinds (ARCHITECTURE.md).

Two calls per frame, one per task (hand_count, manipulation), combined into one `JudgeResponse`.

`_call_qwen3vl` is wired to the real vLLM server (`cloud/modal_qwen3vl.py`, Modal today, AWS
once Modal credits run out) via the standard `openai` client pointed at `QWEN3VL_BASE_URL` --
verified against the installed `openai` package's own response types, not assumed: multimodal
content blocks are `{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}`
alongside a `{"type": "text", ...}` block (vLLM's OpenAI-compatible server implements the same
shape OpenAI's own vision API uses), `response.model` echoes back `--served-model-name`, and
`response.choices[0].logprobs.content` carries real per-output-token logprobs. A documented,
real vLLM limitation: *input*-side prompt logprobs are not properly supported for multimodal
requests (vLLM issue #16107) -- this module only ever reads *output*-token logprobs (the
model's own answer), never prompt logprobs, so that gap does not apply here.
"""

from __future__ import annotations

import base64
import math
import os
import time
from typing import Literal, cast

import openai

from vernier.judges.base import JudgeAdapter, parse_hand_count_response, parse_manipulation_response
from vernier.judges.prompts import PromptVariant, load_prompt
from vernier.models import Confidence, FrameRef, JudgeResponse, JudgeStatus
from vernier.sampling.draw import image_bytes_for

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

_MODEL = "Qwen/Qwen3-VL-8B-Instruct-FP8"
_MAX_OUTPUT_TOKENS = 64  # the answer is always a short JSON object, never free-form prose

# Modal L4 pricing at time of writing (docs/DECISIONS.md D042, verified live) -- a rough
# per-call attribution (this call's own wall-clock share of warm-container time), not an
# invoice. Deliberately excludes idle warm-time between calls, which is a real cost this number
# undercounts; the actual total spend for a run should be read from Modal's own billing, not
# summed from JudgeResponse.cost_usd across many calls.
_MODAL_L4_USD_PER_HOUR = 0.80

# Reported by judge_rev() before any real call has happened -- an open-weights model's
# "revision" is only meaningful once something has actually loaded and answered.
_JUDGE_REV_UNRESOLVED = "unresolved (no live call yet)"


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


def _mean_output_token_probability(
    logprobs: "openai.types.chat.chat_completion.ChoiceLogprobs | None",
) -> float | None:
    """Convert real per-output-token logprobs into a single [0, 1] confidence value.

    The mean token probability across the response's own answer tokens -- this project's own
    operationalization, not a value vLLM/OpenAI hands back directly (there is no single "the
    confidence" field on a chat completion). Chosen over e.g. the first token's probability
    alone because the answer is a short JSON object (`{"hand_count": 2}`) where the
    semantically-decisive token is not reliably the first one emitted. Returns `None` when the
    server didn't return per-token logprobs at all (e.g. `logprobs` wasn't honoured).
    """
    if logprobs is None or not logprobs.content:
        return None
    mean_logprob = sum(t.logprob for t in logprobs.content) / len(logprobs.content)
    return math.exp(mean_logprob)


class Qwen3VLJudge(JudgeAdapter):
    """The sole judge in the panel (`docs/DECISIONS.md` D042): self-hosted, open weights, no
    API key required. Exposes logprob confidence."""

    judge = "qwen3-vl"

    def __init__(self) -> None:
        # Lazy: constructing openai.OpenAI() with no base_url/api_key raises immediately if
        # OPENAI_API_KEY isn't set in the environment, and merely constructing a Qwen3VLJudge
        # (e.g. in a test that monkeypatches _call_qwen3vl and never touches the real client)
        # must not require QWEN3VL_BASE_URL to exist.
        self._client_instance: openai.OpenAI | None = None
        self._last_model_version = _JUDGE_REV_UNRESOLVED

    @property
    def _client(self) -> openai.OpenAI:
        if self._client_instance is None:
            # Caught by a real live call, not assumed: openai.OpenAI()'s *default* base_url
            # already ends in "/v1" (confirmed: constructing the client with no base_url at all
            # yields "https://api.openai.com/v1/"), but the client does not append "/v1" itself
            # for a custom base_url -- it only ever does `base_url + "/chat/completions"`. vLLM's
            # OpenAI-compatible server serves at `/v1/chat/completions`, so a bare
            # QWEN3VL_BASE_URL (just the Modal server's root URL) 404s on every real call unless
            # "/v1" is appended here.
            base_url = os.environ["QWEN3VL_BASE_URL"].rstrip("/") + "/v1"
            self._client_instance = openai.OpenAI(base_url=base_url, api_key="EMPTY")
        return self._client_instance

    def judge_rev(self) -> str:
        return self._last_model_version

    def _image_bytes_for(self, frame: FrameRef) -> bytes:
        """Resolve `frame` to its real JPEG bytes via `sampling.draw.image_bytes_for`
        (`ARCHITECTURE.md`: judges depend on sampling for frames, nothing else). Real for the
        `E10k-*` family; raises `NotImplementedError` for `S10k-U`/`S10k-S` frames, the same as
        the sampling seam it delegates to.
        """
        return image_bytes_for(frame)

    def _call_qwen3vl(self, frame: FrameRef, prompt_text: str) -> tuple[str, int, float, float | None]:
        """Issue one real call to the self-hosted Qwen3-VL server for one task's prompt
        against `frame`'s image, and return `(raw_response_text, latency_ms, cost_usd,
        token_logprob)`.

        `latency_ms` is wall-clock time around the call -- neither vLLM's nor OpenAI's response
        carries a latency/duration field of its own. `cost_usd` is a rough per-call attribution
        of Modal L4 warm-container time (see `_MODAL_L4_USD_PER_HOUR`'s docstring for why this
        is an underestimate, not an invoice). `judge_rev()` becomes resolvable after this call
        via `response.model`.
        """
        image_bytes = self._image_bytes_for(frame)
        image_b64 = base64.standard_b64encode(image_bytes).decode("ascii")

        start = time.monotonic()
        response = self._client.chat.completions.create(
            model=_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                        },
                        {"type": "text", "text": prompt_text},
                    ],
                }
            ],
            max_tokens=_MAX_OUTPUT_TOKENS,
            logprobs=True,
        )
        latency_ms = int((time.monotonic() - start) * 1000)

        self._last_model_version = response.model or self._last_model_version
        cost_usd = (latency_ms / 1000) * (_MODAL_L4_USD_PER_HOUR / 3600)

        choice = response.choices[0]
        token_logprob = _mean_output_token_probability(choice.logprobs)

        return choice.message.content or "", latency_ms, cost_usd, token_logprob

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
        # manipulation call's -- the same hand-count-first convention the retired ClaudeJudge
        # used for its P7 verbalized confidence, applied here across both calls since either may
        # expose a logprob.
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
