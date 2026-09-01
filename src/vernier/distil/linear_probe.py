"""Rung 1: a linear probe on frozen features. Cheap, laptop-runnable, the baseline that must
be beaten to justify anything more expensive.

Training targets are `gemini-2.5-flash` P0 labels -- the judge, deliberately, not human gold.
Human gold is the held-out evaluation for both the judge and its distillate.
"""

from __future__ import annotations

from typing import Any

from vernier.models import JudgeResponse


class LinearProbe:
    """A linear probe trained on frozen backbone features against judge labels."""

    def fit(self, features: Any, judge_labels: list[JudgeResponse]) -> None:
        raise NotImplementedError

    def predict(self, features: Any) -> list[int]:
        raise NotImplementedError


def fidelity(probe: LinearProbe, held_out_features: Any, teacher_labels: list[JudgeResponse]) -> float:
    """Point estimate of teacher fidelity: probe agreement with `gemini-2.5-flash` P0a
    (`teacher_labels`) on hand presence. Diagnostic, not the H6 claim -- the claim is the
    abstention cascade's floor-at-coverage against human gold, in `cascade.py`."""
    raise NotImplementedError
