"""Behavioural tests for `vernier.estimation.bootstrap`, written before the bodies exist.

Golden-case coverage per docs/WAVES.md ("tests are schema tests, not scientific tests"):
`cluster_bootstrap_ci` against synthetic clustered data with a known design effect, plus
`design_effect` against a hand-constructed pair of intervals with a hand-computable ratio.
"""

from __future__ import annotations

import numpy as np
import pytest

from vernier.estimation.bootstrap import cluster_bootstrap_ci, design_effect
from vernier.models import AgreementCI

# Small B keeps the test suite fast; the statistical behaviour under test (cluster CI wider
# than iid CI when clusters carry the signal) is already visible at a few thousand replicates.
TEST_B = 2000
TEST_SEED = 12345


def _high_icc_data() -> tuple[list[float], list[str]]:
    """5 clusters, 200 points each. Cluster means are far apart (0, 10, 20, 30, 40); within a
    cluster, noise is tiny (std=0.1). Almost all of the variance is BETWEEN clusters, so which
    few cluster means happen to land in a bootstrap resample dominates the mean's variability --
    a textbook high-design-effect setup. iid resampling of 1000 points can't see this: with that
    many draws the resampled mean barely moves, so its interval stays narrow.
    """
    rng = np.random.default_rng(1)
    cluster_means = [0.0, 10.0, 20.0, 30.0, 40.0]
    values: list[float] = []
    cluster_ids: list[str] = []
    for i, mean in enumerate(cluster_means):
        noise = rng.normal(loc=0.0, scale=0.1, size=200)
        values.extend((mean + noise).tolist())
        cluster_ids.extend([f"worker_{i}"] * 200)
    return values, cluster_ids


def _low_icc_data() -> tuple[list[float], list[str]]:
    """1000 iid points, split into 50 clusters of 20 by assignment that is INDEPENDENT of value
    (cluster label is just position // 20 over a fully shuffled iid draw). Between-cluster
    variance is no larger than within-cluster variance here, so cluster and iid bootstraps
    should agree closely: design effect near 1.
    """
    rng = np.random.default_rng(2)
    values = rng.normal(loc=5.0, scale=1.0, size=1000)
    order = rng.permutation(1000)
    shuffled = values[order]
    cluster_ids = [f"c{i // 20}" for i in range(1000)]
    return shuffled.tolist(), cluster_ids


def test_cluster_ci_is_meaningfully_wider_than_iid_when_between_cluster_variance_dominates() -> None:
    values, cluster_ids = _high_icc_data()

    cluster_ci = cluster_bootstrap_ci(values, cluster_ids, B=TEST_B, seed=TEST_SEED)
    iid_ci = cluster_bootstrap_ci(values, None, B=TEST_B, seed=TEST_SEED)

    cluster_width = cluster_ci.hi - cluster_ci.lo
    iid_width = iid_ci.hi - iid_ci.lo

    # Between-cluster spread (means 0..40) dwarfs within-cluster noise (std=0.1) -- the cluster
    # bootstrap must come out at least an order of magnitude wider, per pre-registration's
    # "the cluster problem": an iid interval on this data would be wrong.
    assert cluster_width > 10 * iid_width


def test_cluster_ci_is_close_to_iid_when_clustering_carries_no_signal() -> None:
    values, cluster_ids = _low_icc_data()

    cluster_ci = cluster_bootstrap_ci(values, cluster_ids, B=TEST_B, seed=TEST_SEED)
    iid_ci = cluster_bootstrap_ci(values, None, B=TEST_B, seed=TEST_SEED)

    cluster_width = cluster_ci.hi - cluster_ci.lo
    iid_width = iid_ci.hi - iid_ci.lo

    # No cluster-level signal -> design effect should be close to 1, not blown up.
    assert 0.5 * iid_width < cluster_width < 2.0 * iid_width


def test_same_seed_gives_identical_ci_twice() -> None:
    values, cluster_ids = _high_icc_data()

    first = cluster_bootstrap_ci(values, cluster_ids, B=TEST_B, seed=TEST_SEED)
    second = cluster_bootstrap_ci(values, cluster_ids, B=TEST_B, seed=TEST_SEED)

    assert first.lo == second.lo
    assert first.hi == second.hi


def test_same_seed_gives_identical_iid_ci_twice() -> None:
    values, _ = _high_icc_data()

    first = cluster_bootstrap_ci(values, None, B=TEST_B, seed=TEST_SEED)
    second = cluster_bootstrap_ci(values, None, B=TEST_B, seed=TEST_SEED)

    assert first.lo == second.lo
    assert first.hi == second.hi


def test_cluster_ids_none_returns_iid_method_and_validates() -> None:
    values, _ = _high_icc_data()

    ci = cluster_bootstrap_ci(values, None, B=TEST_B, seed=TEST_SEED)

    assert ci.method == "iid"
    assert ci.clusters is None
    assert ci.B is None
    # Round-trips through the real pydantic model without the validator raising.
    AgreementCI(lo=ci.lo, hi=ci.hi, method=ci.method, clusters=ci.clusters, B=ci.B)


def test_cluster_ci_reports_distinct_cluster_count() -> None:
    values, cluster_ids = _high_icc_data()
    assert len(set(cluster_ids)) == 5

    ci = cluster_bootstrap_ci(values, cluster_ids, B=TEST_B, seed=TEST_SEED)

    assert ci.method == "cluster-bootstrap"
    assert ci.clusters == 5
    assert ci.B == TEST_B


def test_design_effect_matches_hand_computed_ratio() -> None:
    cluster_ci = AgreementCI(lo=0.0, hi=4.0, method="cluster-bootstrap", clusters=5, B=100)
    iid_ci = AgreementCI(lo=1.0, hi=3.0, method="iid", clusters=None, B=None)

    # width ratio = 4 / 2 = 2, squared = 4.0 -- computed by hand, not derived from the code.
    assert design_effect(cluster_ci, iid_ci) == pytest.approx(4.0)


def test_design_effect_rejects_cluster_ci_with_wrong_method() -> None:
    not_actually_cluster = AgreementCI(lo=1.0, hi=3.0, method="iid", clusters=None, B=None)
    iid_ci = AgreementCI(lo=1.0, hi=3.0, method="iid", clusters=None, B=None)

    with pytest.raises(ValueError):
        design_effect(not_actually_cluster, iid_ci)


def test_design_effect_rejects_iid_ci_with_wrong_method() -> None:
    cluster_ci = AgreementCI(lo=0.0, hi=4.0, method="cluster-bootstrap", clusters=5, B=100)
    not_actually_iid = AgreementCI(lo=0.0, hi=4.0, method="cluster-bootstrap", clusters=5, B=100)

    with pytest.raises(ValueError):
        design_effect(cluster_ci, not_actually_iid)
