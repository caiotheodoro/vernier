"""`Qwen3VLJudge` — the reproducibility anchor: open weights, no API keys required.

Seam: confidence extraction. Exposes logprob confidence (unlike the closed judges, which only
expose verbalized confidence under P7). Calibration is per judge and never pooled across kinds.
"""

from __future__ import annotations

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.models import FrameRef, JudgeResponse


class Qwen3VLJudge(JudgeAdapter):
    """The reproducibility anchor: open weights, no API keys required. Exposes logprob confidence."""

    judge = "qwen3-vl"

    def judge_rev(self) -> str:
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        raise NotImplementedError
