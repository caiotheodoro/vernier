"""Rung 2: a Qwen3-VL LoRA on Modal, trained on `gemini-2.5-flash` P0 labels."""

from __future__ import annotations

from typing import Any

from vernier.models import FrameRef, JudgeResponse


class Qwen3VLLoRA:
    """4-bit LoRA fine-tune of Qwen3-VL, images in and structured output out."""

    def train(self, frames: list[FrameRef], judge_labels: list[JudgeResponse], *, seed: int = 777) -> None:
        raise NotImplementedError

    def predict(self, frame: FrameRef) -> Any:
        raise NotImplementedError
