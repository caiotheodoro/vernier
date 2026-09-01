"""One class per member of the judge panel fixed in `docs/PRE-REGISTRATION.md`.

Seam: confidence extraction. `logprob` from open weights, `verbalized` from the closed APIs,
`none` where neither is available. Calibration is per judge and never pooled across kinds --
each adapter must report the `Confidence.kind` it actually has, not flatten it to a float.
"""

from __future__ import annotations

from vernier.models import FrameRef, JudgeResponse
from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant


class GeminiJudge(JudgeAdapter):
    """The replication target: Build AI's own judge. No confidence under P0a/P0b; verbalized under P7."""

    judge = "gemini-2.5-flash"

    def judge_rev(self) -> str:
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        raise NotImplementedError


class ClaudeJudge(JudgeAdapter):
    """Second frontier judge, different lineage. No confidence under P0a/P0b; verbalized under P7."""

    judge = "claude"

    def judge_rev(self) -> str:
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        raise NotImplementedError


class Qwen3VLJudge(JudgeAdapter):
    """The reproducibility anchor: open weights, no API keys required. Exposes logprob confidence."""

    judge = "qwen3-vl"

    def judge_rev(self) -> str:
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        raise NotImplementedError
