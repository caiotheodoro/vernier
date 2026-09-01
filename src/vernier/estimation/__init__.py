"""The module the project's credibility rests on.

Consumes `HumanLabel` plus `JudgeResponse` and emits `PrevalenceEstimate`: the naive judge
proportion, the PPI-rectified estimate, and its interval -- clustered over the participant
identifier wherever one exists, and explicitly labelled a width lower bound wherever one does
not.

Three units, split for Wave 1 file-ownership (`docs/DECISIONS.md` D033): `ppi.py` owns
prediction-powered inference and the `PrevalenceEstimate` assembler; `bootstrap.py` owns the
cluster bootstrap and the design-effect computation (measured only where a grouping variable is
available: `S10k-U`/`S10k-S`); `disparity.py` owns H8's participant-count precision-disparity
lookup -- not an ICC-adjusted effective N (D031). This module re-exports all three.

Seam: `clustered` is a property of the arm, not a global setting -- callers must always pass
`cluster_by` explicitly (`None` is a valid, deliberate value) plus, when `None`, the reason.
"""

from __future__ import annotations

from vernier.estimation.bootstrap import (
    CLUSTER_BOOTSTRAP_B,
    CLUSTER_BOOTSTRAP_SEED,
    cluster_bootstrap_ci,
    design_effect,
)
from vernier.estimation.disparity import participant_count_disparity
from vernier.estimation.ppi import estimate_prevalence, ppi_estimate

__all__ = [
    "CLUSTER_BOOTSTRAP_B",
    "CLUSTER_BOOTSTRAP_SEED",
    "cluster_bootstrap_ci",
    "design_effect",
    "estimate_prevalence",
    "participant_count_disparity",
    "ppi_estimate",
]
