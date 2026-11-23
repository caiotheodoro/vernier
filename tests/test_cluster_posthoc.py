"""Tests for `scripts/cluster_posthoc.py` (D091/D092 post-hoc cluster and error-direction analyses)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "scripts"))

from cluster_posthoc import (  # noqa: E402
    _error_direction_both_judges,
    anova_icc,
    expected_m_tilde,
    wilson_ci,
)


def test_anova_icc_is_one_when_clusters_are_constant_and_differ() -> None:
    values = [0.0] * 10 + [1.0] * 5 + [0.0] * 3 + [1.0] * 12
    clusters = ["a"] * 10 + ["b"] * 5 + ["c"] * 3 + ["d"] * 12
    res = anova_icc(values, clusters)
    assert res["icc"] == pytest.approx(1.0)
    assert res["m_tilde"] == pytest.approx((100 + 25 + 9 + 144) / 30)
    assert res["deff_analytic"] == pytest.approx(res["m_tilde"])


def test_anova_icc_is_near_zero_when_cluster_means_equal_grand_mean() -> None:
    values = [0.0, 1.0] * 20
    clusters = [f"w{i // 4}" for i in range(40)]
    res = anova_icc(values, clusters)
    # Identical cluster means give MSB = 0 and slightly negative finite-sample ANOVA ICC.
    assert res["icc"] <= 0.0
    assert res["m_bar"] == pytest.approx(4.0)
    assert res["m_tilde"] == pytest.approx(4.0)
    assert res["deff_analytic"] == pytest.approx(1.0)


def test_expected_m_tilde_matches_uniform_multinomial_identity() -> None:
    assert expected_m_tilde(1, 1 / 37) == 1.0
    assert expected_m_tilde(38, 1 / 37) == pytest.approx(2.0)
    assert expected_m_tilde(9800, 1 / 37) == pytest.approx(1.0 + 9799 / 37)


def test_wilson_ci_zero_over_n_has_zero_lower_and_positive_upper() -> None:
    ci = wilson_ci(0, 129)
    assert ci["rate_pct"] == 0.0
    assert ci["lo_pct"] == 0.0
    assert ci["hi_pct"] == pytest.approx(2.89, abs=0.05)


def test_committed_posthoc_artifact_matches_committed_inputs() -> None:
    path = _ROOT / "data" / "cluster_posthoc.json"
    assert path.is_file(), "run scripts/cluster_posthoc.py first"
    committed = json.loads(path.read_text())

    # Deterministic error-direction block must equal a fresh recomputation bit-for-bit.
    assert committed["error_direction_both_judges"] == _error_direction_both_judges()

    # Worker-level deffs must match the frozen H2 artifacts.
    for arm in ("S10k-U", "S10k-S"):
        h2 = json.loads((_ROOT / "data" / f"h2_design_effect.{arm}.json").read_text())
        for task in ("hand_ge1", "hand_eq2", "active_manipulation"):
            block = committed["raw_corpus_clustering"][arm]["tasks"][task]
            assert block["worker_deff"] == h2["tasks"][task]["design_effect"]
            assert block["worker_anova"]["m_tilde"] > block["worker_anova"]["m_bar"]
            assert 0.0 < block["worker_anova"]["icc"] < 0.25

    # Vendor full-arm iid margin must match margin_exploratory.json.
    margin = json.loads((_ROOT / "data" / "margin_exploratory.json").read_text())
    v_manip = committed["evaluation_cluster_sensitivity"]["arms"]["vendor_full_arm"][
        "egocentric_minus_epic_margin"
    ]["manipulation"]
    src_manip = margin["vendor_full_arm"]["comparisons"]["egocentric-10k_minus_epic-kitchens-100"][
        "manipulation"
    ]
    assert v_manip["corrected_margin_pp"] == pytest.approx(src_manip["corrected_margin_pp"])
    assert v_manip["iid_ci_pp"]["lo"] == pytest.approx(src_manip["ci_pp"]["lo"])
    assert v_manip["iid_ci_pp"]["hi"] == pytest.approx(src_manip["ci_pp"]["hi"])
    assert v_manip["iid_gold_per_arm"]["gold_per_arm"] == 89
    assert v_manip["model2_direct_deff"]["gold_per_arm_to_exclude_published"]["gold_per_arm"] > 89
