"""The exploratory margin estimand (docs/DECISIONS.md D079)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from margin_analysis import (  # noqa: E402
    _gold_needed_to_exclude,
    _se_from_block,
    _variance_components,
    margin,
)

from vernier.models import PPIBlock, PPICI  # noqa: E402


def _block(value: float, se: float, n_gold: int = 30, n_unlabelled: int = 170) -> PPIBlock:
    z = 1.959963984540054
    return PPIBlock(
        value=value,
        ci=PPICI(lo=value - z * se, hi=value + z * se, level=0.95),
        n_gold=n_gold,
        n_unlabelled=n_unlabelled,
        rectifier=0.0,
        method="ppi++",
        clustered=False,
        cluster_by=None,
        why_not_clustered="test fixture",
    )


def test_se_is_recovered_exactly_from_the_interval() -> None:
    assert _se_from_block(_block(0.8, 0.05)) == pytest.approx(0.05)


def test_margin_is_the_difference_and_variances_add() -> None:
    m = margin(_block(0.80, 0.03), _block(0.90, 0.04), 0.85, 0.80)
    assert m["corrected_margin_pp"] == pytest.approx(-10.0)
    assert m["se_pp"] == pytest.approx(5.0)  # sqrt(3^2 + 4^2)
    assert m["published_margin_pp"] == pytest.approx(5.0)


def test_sign_flipped_is_true_only_when_the_correction_crosses_zero() -> None:
    flipped = margin(_block(0.80, 0.03), _block(0.90, 0.04), 0.90, 0.80)
    assert flipped["sign_flipped"] is True
    intact = margin(_block(0.90, 0.03), _block(0.80, 0.04), 0.90, 0.80)
    assert intact["sign_flipped"] is False


def test_published_inside_ci_is_reported_separately_from_the_sign() -> None:
    """A flipped point estimate whose interval still covers the published value does not refute
    it -- the distinction the whole entry turns on."""
    # corrected margin -5pp, CI about [-18.9, +8.9]; published +6pp is inside it.
    m = margin(_block(0.80, 0.05), _block(0.85, 0.05), 0.86, 0.80)
    assert m["corrected_margin_pp"] == pytest.approx(-5.0)
    assert m["published_margin_pp"] == pytest.approx(6.0)
    assert m["sign_flipped"] is True
    assert m["published_inside_corrected_ci"] is True


def test_gold_sizing_accounts_for_the_unlabelled_floor(tmp_path: Path) -> None:
    """D088: the old version scaled the whole standard error as 1/sqrt(n), which ignores that
    the unlabelled term does not shrink with more labels. It returned a sample size smaller than
    the one already collected."""
    # gap of 0.05, so target SE is 0.05/1.96 = 0.02551, target variance 6.51e-4.
    # floor 1e-4 leaves 5.51e-4 for the gold term; residual variance 0.05 needs n = 91.
    out = _gold_needed_to_exclude(point=0.0, published=0.05, var_resid_sum=0.05, unl_floor=1e-4)
    assert out["achievable_by_labelling_alone"] is True
    assert out["gold_per_arm"] == 91


def test_gold_sizing_reports_when_labelling_cannot_reach_the_target(tmp_path: Path) -> None:
    """When the unlabelled pool alone exceeds the target variance, no number of labels helps."""
    out = _gold_needed_to_exclude(point=0.0, published=0.01, var_resid_sum=0.05, unl_floor=1e-3)
    assert out["achievable_by_labelling_alone"] is False
    assert "floor_half_width_pp" in out
    assert "gold_per_arm" not in out


def test_variance_components_reproduce_the_committed_interval() -> None:
    """The decomposition must add back up to the standard error the estimator reported."""
    import json

    from vernier.labels.store import HumanLabelStore
    from vernier.models import JudgeResponse

    gold = HumanLabelStore(Path("data/labels/caio")).read_pass("primary")
    judged = [
        JudgeResponse.model_validate(r)
        for r in json.loads(Path("data/gold_judged/G200-ego.P0b.json").read_text())
    ]
    ids = {j.frame_id for j in judged}
    arm_gold = [lab for lab in gold if lab.frame_id in ids]
    var_resid, unl_term, n, big_n = _variance_components(arm_gold, judged, "manipulation")
    committed = json.loads(Path("data/wave4_analysis.json").read_text())
    block = committed["ppi"]["G200-ego"]["manipulation"]["ppi"]
    se_committed = (block["ci"]["hi"] - block["ci"]["lo"]) / (2 * 1.959963984540054)
    assert abs((var_resid / n + unl_term) ** 0.5 - se_committed) < 1e-9
    assert (n, big_n) == (block["n_gold"], block["n_unlabelled"])
