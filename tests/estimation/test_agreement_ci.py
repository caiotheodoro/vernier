"""Behavioural tests for `vernier.estimation.agreement_ci`.

Mirrors `tests/agreement/test_core.py`'s golden-case discipline: hand-verifiable fixtures where
possible, plus the standard "does this actually behave like a bootstrap CI" checks (contains the
point estimate, narrows as N grows, collapses on perfect agreement) where an exact closed-form
bound isn't hand-derivable -- a bootstrap CI's width depends on the resampling distribution, not
a formula the way a single AC1 value is.
"""

from __future__ import annotations

import pytest

from tests.fixtures import make_human_label, make_judge_response
from vernier.agreement.core import gwet_ac1
from vernier.estimation.agreement_ci import ac1_bootstrap_ci, intra_rater_ac1_bootstrap_ci
from vernier.models import AgreementCI, HumanLabel, JudgeResponse

# Small B keeps the suite fast -- same rationale as tests/estimation/test_bootstrap.py's TEST_B.
TEST_B = 2000
TEST_SEED = 12345

FRAME = "ego10k/f0051/w00243/v0007/{:06d}"


def _frame_id(i: int) -> str:
    return FRAME.format(i)


def _binary_manipulation_pairs(scale: int = 1) -> tuple[list[HumanLabel], list[JudgeResponse]]:
    """Same 17/1/1/1 confusion matrix as test_core.py's golden case, optionally repeated `scale`
    times (with distinct frame ids) to build a larger-N fixture for the narrowing check."""
    labels: list[HumanLabel] = []
    responses: list[JudgeResponse] = []
    i = 0
    matrix = [(True, True, 17), (False, False, 1), (True, False, 1), (False, True, 1)]
    for _ in range(scale):
        for human_value, judge_value, count in matrix:
            for _ in range(count):
                labels.append(make_human_label(frame_id=_frame_id(i), manipulation=human_value))
                responses.append(
                    make_judge_response(frame_id=_frame_id(i), manipulation=judge_value)
                )
                i += 1
    return labels, responses


def _perfect_agreement_pairs() -> tuple[list[HumanLabel], list[JudgeResponse]]:
    labels = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)]
    responses = [
        make_judge_response(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)
    ]
    return labels, responses


def test_ci_contains_the_point_estimate() -> None:
    labels, responses = _binary_manipulation_pairs()
    point = gwet_ac1(labels, responses, "manipulation")

    ci = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.lo <= point <= ci.hi


def test_method_clusters_b_are_always_iid_none_none() -> None:
    labels, responses = _binary_manipulation_pairs()

    ci = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.method == "iid"
    assert ci.clusters is None
    assert ci.B is None
    # Round-trips through the real pydantic model without the validator raising.
    AgreementCI(lo=ci.lo, hi=ci.hi, method=ci.method, clusters=ci.clusters, B=ci.B)


def test_same_seed_gives_identical_ci_twice() -> None:
    labels, responses = _binary_manipulation_pairs()

    first = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)
    second = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert first.lo == second.lo
    assert first.hi == second.hi


def test_interval_narrows_as_n_grows_holding_the_same_proportions() -> None:
    small_labels, small_responses = _binary_manipulation_pairs(scale=1)
    large_labels, large_responses = _binary_manipulation_pairs(scale=10)

    small_ci = ac1_bootstrap_ci(small_labels, small_responses, "manipulation", B=TEST_B, seed=TEST_SEED)
    large_ci = ac1_bootstrap_ci(large_labels, large_responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert (large_ci.hi - large_ci.lo) < (small_ci.hi - small_ci.lo)


def test_perfect_agreement_collapses_to_a_point_mass_at_one() -> None:
    labels, responses = _perfect_agreement_pairs()

    ci = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.lo == pytest.approx(1.0)
    assert ci.hi == pytest.approx(1.0)


def test_small_n_does_not_crash() -> None:
    labels = [make_human_label(frame_id=_frame_id(0), manipulation=True)]
    responses = [make_judge_response(frame_id=_frame_id(0), manipulation=True)]

    ci = ac1_bootstrap_ci(labels, responses, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.lo == pytest.approx(1.0)
    assert ci.hi == pytest.approx(1.0)


# --- intra_rater_ac1_bootstrap_ci: same shape, primary vs. retest instead of human vs. judge ---


def test_intra_rater_ci_contains_the_point_estimate() -> None:
    primary = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2 == 0)) for i in range(20)]
    retest_values = [True] * 10 + [False] * 8 + [True, False]
    retest = [
        make_human_label(frame_id=_frame_id(i), manipulation=v, rater="R1")
        for i, v in enumerate(retest_values)
    ]

    ci = intra_rater_ac1_bootstrap_ci(primary, retest, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.method == "iid"
    assert ci.clusters is None
    assert ci.B is None
    assert ci.lo <= ci.hi


def test_intra_rater_perfect_agreement_collapses_to_a_point_mass_at_one() -> None:
    primary = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)]
    retest = [
        make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2), rater="R1")
        for i in range(10)
    ]

    ci = intra_rater_ac1_bootstrap_ci(primary, retest, "manipulation", B=TEST_B, seed=TEST_SEED)

    assert ci.lo == pytest.approx(1.0)
    assert ci.hi == pytest.approx(1.0)
