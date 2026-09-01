from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from power_simulation import (  # noqa: E402
    _expected_ac1_for_match_rate,
    _gwet_ac1_binary,
    _solve_match_rate_for_ac1,
    simulate_h5_power,
    simulate_r100_precision,
)


def test_gwet_ac1_perfect_agreement() -> None:
    assert _gwet_ac1_binary(po=1.0, p_bar=0.5) == pytest.approx(1.0)


def test_gwet_ac1_known_textbook_case() -> None:
    # Wallace (2010)-style two-rater binary table: 80/100 raw agreement, 50/50 pooled prevalence
    # -> pe = 2*0.5*0.5 = 0.5, AC1 = (0.8-0.5)/(1-0.5) = 0.6.
    assert _gwet_ac1_binary(po=0.8, p_bar=0.5) == pytest.approx(0.6)


def test_gwet_ac1_high_prevalence_below_kappa_paradox_floor() -> None:
    # At p_bar=0.9 (matching PRE-REGISTRATION.md's 96%-prevalence concern), pe=0.18, so 90%
    # raw agreement still yields a moderate, not near-perfect, AC1 -- the paradox AC1 is
    # pre-registered specifically to avoid (kappa would look far worse here at this prevalence).
    ac1 = _gwet_ac1_binary(po=0.90, p_bar=0.9)
    pe = 2 * 0.9 * 0.1
    assert ac1 == pytest.approx((0.90 - pe) / (1 - pe))


def test_expected_ac1_endpoints_bracket_target_range() -> None:
    assert _expected_ac1_for_match_rate(0.0, prevalence=0.9) == pytest.approx(-1.0)
    assert _expected_ac1_for_match_rate(1.0, prevalence=0.9) == pytest.approx(1.0)


def test_solve_match_rate_for_ac1_round_trips() -> None:
    for target in [0.60, 0.70, 0.80, 0.90]:
        po = _solve_match_rate_for_ac1(target, prevalence=0.9)
        assert _expected_ac1_for_match_rate(po, prevalence=0.9) == pytest.approx(target, abs=1e-6)


def test_r100_precision_recovers_target_ac1_on_average() -> None:
    # Regression test for the bug this script's docstring names: an earlier closed-form
    # inversion assumed p_bar stayed fixed at `prevalence`, which is false under the flip
    # generative model, and biased every measured AC1 downward by a constant ~0.06-0.10
    # regardless of n. This asserts the fix: mean measured AC1 tracks the target closely even
    # at n=100, not just asymptotically.
    results = simulate_r100_precision([0.70, 0.80], n=100, n_sims=4000, seed=1)
    by_target = {r.true_ac1: r.mean_measured_ac1 for r in results}
    assert by_target[0.70] == pytest.approx(0.70, abs=0.03)
    assert by_target[0.80] == pytest.approx(0.80, abs=0.03)


def test_r100_precision_is_monotonic_in_true_ac1() -> None:
    results = simulate_r100_precision([0.60, 0.70, 0.80, 0.90], n=100, n_sims=3000, seed=2)
    probs = [r.p_measured_ge_070 for r in results]
    assert probs == sorted(probs)


def test_h5_power_output_shape_and_bounds() -> None:
    results = simulate_h5_power([0.05, 0.10], n_sims=1000, seed=3)
    assert len(results) == 2
    for r in results:
        assert 0.0 <= r.power <= 1.0


def test_h5_power_increases_as_baseline_error_rate_falls_toward_the_effect_size() -> None:
    # A 5pp effect is proportionally larger, and therefore easier to detect via a proportion
    # test, at a lower baseline rate.
    results = simulate_h5_power([0.05, 0.30], n_sims=8000, seed=4)
    power_by_baseline = {r.baseline_error_rate: r.power for r in results}
    assert power_by_baseline[0.05] > power_by_baseline[0.30]
