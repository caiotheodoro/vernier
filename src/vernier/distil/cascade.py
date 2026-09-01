"""Rung 3: the abstention cascade -- confidence estimation, a threshold, and escalation.

What turns the distillate into an instrument with a stated floor (D026, H6). The threshold is
calibrated against held-out human gold and must never be tuned on the frames it will later
score. The module exposes coverage and floor as a pair; a caller cannot obtain one without
the other, because a floor at unstated coverage is meaningless.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from vernier.models import FrameRef, HumanLabel


class CoverageAndFloor(NamedTuple):
    """Always returned together -- see module docstring."""

    coverage: float
    agreement_floor: float


class AbstentionCascade:
    """Wraps a distillate (`LinearProbe` or `Qwen3VLLoRA`) with a calibrated abstention gate."""

    def calibrate_threshold(self, held_out_gold: list[HumanLabel]) -> None:
        """Fit the abstention threshold. Must be called with gold the cascade will never be
        scored against again."""
        raise NotImplementedError

    def predict(self, frame: FrameRef) -> tuple[Any | None, bool]:
        """Returns `(label, should_abstain)`. `label` is `None` iff `should_abstain` is True."""
        raise NotImplementedError

    def coverage_and_floor(self, gold: list[HumanLabel]) -> CoverageAndFloor:
        """Report the pair together, per the module seam -- never floor alone."""
        raise NotImplementedError
