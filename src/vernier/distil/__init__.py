"""Three rungs, in order: `linear_probe` (baseline), `lora` (Qwen3-VL LoRA), `cascade`
(abstention cascade -- the deliverable instrument, D026)."""

from vernier.distil.cascade import AbstentionCascade, CoverageAndFloor
from vernier.distil.linear_probe import LinearProbe, fidelity
from vernier.distil.lora import Qwen3VLLoRA

__all__ = [
    "AbstentionCascade",
    "CoverageAndFloor",
    "LinearProbe",
    "Qwen3VLLoRA",
    "fidelity",
]
