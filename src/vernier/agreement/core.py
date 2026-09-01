"""Agreement statistics and the `AgreementResult` assembler.

Owns Gwet's AC1 as the primary statistic, Cohen's kappa beside it, Fleiss' kappa across the
panel, and intra-rater kappa on `R100`. Every exclusion is counted with its reason and
subtracted from the denominator explicitly.

Does not own intervals -- `ci` on `AgreementResult` is computed by `vernier.estimation`
(cluster bootstrap over `worker_id`) and passed in, never recomputed here.
"""

from __future__ import annotations

from vernier.models import AgreementCI, AgreementResult, HumanLabel, JudgeResponse


def raw_agreement(labels: list[HumanLabel], responses: list[JudgeResponse]) -> float:
    raise NotImplementedError


def gwet_ac1(labels: list[HumanLabel], responses: list[JudgeResponse]) -> float:
    """Primary agreement statistic (pre-registered; stable at the corpus's 96% prevalence
    where Cohen's kappa is not)."""
    raise NotImplementedError


def cohens_kappa(labels: list[HumanLabel], responses: list[JudgeResponse]) -> float:
    """Reported beside AC1. Never the headline."""
    raise NotImplementedError


def fleiss_kappa(responses_by_judge: dict[str, list[JudgeResponse]]) -> float:
    """Agreement across the full judge panel."""
    raise NotImplementedError


def intra_rater_kappa(primary: list[HumanLabel], retest: list[HumanLabel]) -> float:
    """`R100`: primary pass vs. the blind re-label at least seven days later."""
    raise NotImplementedError


def build_agreement_result(
    comparison_a: str,
    comparison_b: str,
    task: str,
    subset: str,
    labels: list[HumanLabel],
    responses: list[JudgeResponse],
    ci: AgreementCI,
    design_effect: float,
) -> AgreementResult:
    """Assemble one `AgreementResult`. `ci` and `design_effect` are supplied by the caller
    (from `vernier.estimation`), not computed here."""
    raise NotImplementedError
