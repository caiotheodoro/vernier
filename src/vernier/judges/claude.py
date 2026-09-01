"""`ClaudeJudge` — second frontier judge, different lineage from Gemini.

Seam: confidence extraction. No confidence under P0a/P0b; verbalized under P7. Calibration is
per judge and never pooled across kinds -- this adapter must report the `Confidence.kind` it
actually has, not flatten it to a float.
"""

from __future__ import annotations

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.models import FrameRef, JudgeResponse


class ClaudeJudge(JudgeAdapter):
    """Second frontier judge, different lineage. No confidence under P0a/P0b; verbalized under P7."""

    judge = "claude"

    def judge_rev(self) -> str:
        raise NotImplementedError

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        raise NotImplementedError
