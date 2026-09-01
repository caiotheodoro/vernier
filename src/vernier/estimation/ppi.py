"""Prediction-powered inference: the primary bias-corrected prevalence estimator.

Bias-corrected estimation from a small human-gold sample plus the large judge-labelled sample,
returning a valid interval for the *true* prevalence regardless of how biased the judge labels
are (`docs/DECISIONS.md` D021, corrected citation D030/D031: the real PPI paper is arXiv
2301.09633, not 2408.15204).
"""

from __future__ import annotations

from vernier.models import HumanLabel, JudgeResponse, PPIBlock, PrevalenceEstimate


def ppi_estimate(
    gold: list[HumanLabel],
    judged: list[JudgeResponse],
    *,
    cluster_by: str | None,
    why_not_clustered: str | None = None,
    method: str = "ppi++",
) -> PPIBlock:
    """Bias-corrected prevalence via prediction-powered inference over human gold plus judge
    labels, with clustered resampling wherever `cluster_by` is not None."""
    raise NotImplementedError


def estimate_prevalence(
    corpus: str,
    task: str,
    prompt_variant: str,
    judge: str,
    gold: list[HumanLabel],
    judged: list[JudgeResponse],
    published: float,
    *,
    cluster_by: str | None,
    why_not_clustered: str | None = None,
) -> PrevalenceEstimate:
    raise NotImplementedError
