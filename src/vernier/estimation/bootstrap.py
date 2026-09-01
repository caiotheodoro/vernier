"""Cluster bootstrap intervals and the design-effect computation.

`cluster_ids=None` returns an `iid` interval -- callers must label it a lower bound on width
and never report it alone, per `docs/PRE-REGISTRATION.md` ("the cluster problem").
"""

from __future__ import annotations

import numpy as np

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
    arr = np.asarray(values, dtype=float)
    rng = np.random.default_rng(seed)

    if cluster_ids is None:
        n = arr.shape[0]
        means = np.empty(B, dtype=float)
        for b in range(B):
            resample = arr[rng.integers(0, n, size=n)]
            means[b] = resample.mean()
        lo, hi = np.percentile(means, [2.5, 97.5])
        return AgreementCI(lo=float(lo), hi=float(hi), method="iid", clusters=None, B=None)

    ids = np.asarray(cluster_ids)
    unique_clusters = np.unique(ids)
    n_clusters = unique_clusters.shape[0]
    groups = [arr[ids == cluster] for cluster in unique_clusters]

    means = np.empty(B, dtype=float)
    for b in range(B):
        picks = np.asarray(rng.integers(0, n_clusters, size=n_clusters))
        resample = np.concatenate([groups[int(pick)] for pick in picks])
        means[b] = resample.mean()
    lo, hi = np.percentile(means, [2.5, 97.5])
    return AgreementCI(
        lo=float(lo), hi=float(hi), method="cluster-bootstrap", clusters=int(n_clusters), B=B
    )


def design_effect(cluster_ci: AgreementCI, iid_ci: AgreementCI) -> float:
    """`(cluster CI width / iid CI width) ** 2`."""
    if cluster_ci.method != "cluster-bootstrap":
        raise ValueError(
            f"design_effect: cluster_ci.method must be 'cluster-bootstrap', got {cluster_ci.method!r}"
        )
    if iid_ci.method != "iid":
        raise ValueError(f"design_effect: iid_ci.method must be 'iid', got {iid_ci.method!r}")

    cluster_width = cluster_ci.hi - cluster_ci.lo
    iid_width = iid_ci.hi - iid_ci.lo
    return (cluster_width / iid_width) ** 2
