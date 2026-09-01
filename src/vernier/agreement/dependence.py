"""Judge-error-dependence: whether the panel's errors correlate.

A panel with correlated errors buys less than N independent opinions -- this is what makes the
three-judge panel's agreement an upper bound rather than a guarantee (`docs/RED-TEAM.md` A3).
"""

from __future__ import annotations

from vernier.models import HumanLabel, JudgeResponse


def judge_error_dependence(
    responses_by_judge: dict[str, list[JudgeResponse]], gold: list[HumanLabel]
) -> float:
    """Whether the panel's errors correlate -- a panel with correlated errors buys less than
    N independent opinions."""
    raise NotImplementedError
