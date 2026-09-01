"""One adapter per judge behind a single interface: frame in, `JudgeResponse` out.

Owns: prompt-variant substitution, response parsing, `status` classification, cost and
latency accounting, retry policy, and recording `judge_rev` per response. Depends on:
`sampling` for frames, nothing else.

A judge never decides ground truth -- it is the object of measurement, not the oracle.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from vernier.models import FrameRef, JudgeResponse
from vernier.judges.prompts import PromptVariant


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
