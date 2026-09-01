"""Consumes `JudgeResponse` and `HumanLabel`, emits `AgreementResult`.

Two units, split for Wave 1 file-ownership (`docs/DECISIONS.md` D033): `core.py` owns AC1
(primary), Cohen's kappa, Fleiss' kappa, intra-rater kappa, and the `AgreementResult`
assembler; `dependence.py` owns the judge-error-dependence estimate. This module re-exports
both.

Does not own intervals -- `ci` on `AgreementResult` is computed by `vernier.estimation`
(cluster bootstrap over `worker_id`) and passed in, never recomputed here.
"""

from __future__ import annotations

from vernier.agreement.core import (
    build_agreement_result,
    cohens_kappa,
    fleiss_kappa,
    gwet_ac1,
    intra_rater_kappa,
    raw_agreement,
)
from vernier.agreement.dependence import judge_error_dependence

__all__ = [
    "build_agreement_result",
    "cohens_kappa",
    "fleiss_kappa",
    "gwet_ac1",
    "intra_rater_kappa",
    "judge_error_dependence",
    "raw_agreement",
]
