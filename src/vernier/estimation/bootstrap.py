"""Cluster bootstrap intervals and the design-effect computation.

`cluster_ids=None` returns an `iid` interval -- callers must label it a lower bound on width
and never report it alone, per `docs/PRE-REGISTRATION.md` ("the cluster problem").
"""

from __future__ import annotations

from vernier.models import AgreementCI

CLUSTER_BOOTSTRAP_B = 10_000
CLUSTER_BOOTSTRAP_SEED = 777


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
