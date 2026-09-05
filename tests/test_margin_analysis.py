"""The exploratory margin estimand (docs/DECISIONS.md D079)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from margin_analysis import _gold_needed_to_exclude, _se_from_block, margin  # noqa: E402

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


def test_gold_needed_scales_with_the_square_of_the_se_ratio() -> None:
    z = 1.959963984540054
    # gap of exactly z*se needs no more labels than it has
    assert _gold_needed_to_exclude(0.0, 0.05, z * 0.05, n_now=30) == 30
    # halving the required se costs four times the labels
    assert _gold_needed_to_exclude(0.0, 0.05, z * 0.025, n_now=30) == 120


def test_gold_needed_is_none_when_there_is_no_gap_to_close() -> None:
    assert _gold_needed_to_exclude(0.1, 0.05, 0.1) is None
