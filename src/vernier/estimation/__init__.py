"""The module the project's credibility rests on.

Consumes `HumanLabel` plus `JudgeResponse` and emits `PrevalenceEstimate`: the naive judge
proportion, the PPI-rectified estimate, and its interval -- clustered over the participant
identifier wherever one exists, and explicitly labelled a width lower bound wherever one does
not. Also owns the design-effect computation (measured only where a grouping variable is
available: `S10k-U`/`S10k-S`) and H8's participant-count precision-disparity lookup.

H8 is not an ICC-adjusted effective sample size -- no such computation exists here or anywhere
in this repo (D031). A true effective N, once R100/primary labelling produces real cluster-size
and outcome-variance data, belongs in `design_effect` below, not in a pre-labelling lookup.

Seam: `clustered` is a property of the arm, not a global setting -- callers must always pass
`cluster_by` explicitly (`None` is a valid, deliberate value) plus, when `None`, the reason.
"""

from __future__ import annotations

from vernier.models import AgreementCI, HumanLabel, JudgeResponse, PPIBlock, PrevalenceEstimate

CLUSTER_BOOTSTRAP_B = 10_000
CLUSTER_BOOTSTRAP_SEED = 777


def participant_count_disparity(participant_counts: dict[str, int]) -> dict[str, int]:
    """H8: the participant-count precision disparity per corpus. No experiment required.

    A pass-through report of public participant counts, not an ICC-adjusted effective sample
    size -- see this module's docstring and `docs/DECISIONS.md` D031.
    """
    raise NotImplementedError


def cluster_bootstrap_ci(
    values: list[float],
    cluster_ids: list[str] | None,
    *,
    B: int = CLUSTER_BOOTSTRAP_B,
    seed: int = CLUSTER_BOOTSTRAP_SEED,
) -> AgreementCI:
    """Cluster bootstrap over `cluster_ids` (`worker_id` or the corpus's participant field).

    `cluster_ids=None` returns an `iid` interval -- callers must label it a lower bound on
    width and never report it alone, per `docs/PRE-REGISTRATION.md` ("the cluster problem").
    """
    raise NotImplementedError


def design_effect(cluster_ci: AgreementCI, iid_ci: AgreementCI) -> float:
    """`(cluster CI width / iid CI width) ** 2`."""
    raise NotImplementedError


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
