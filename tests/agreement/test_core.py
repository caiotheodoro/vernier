"""Behavioural tests for `vernier.agreement.core`, written before the bodies exist.

Per `docs/WAVES.md`'s own eval criteria for the `agreement`/`estimation` unit family ("tests are
schema tests, not scientific tests"), this file leads with hand-computable golden cases rather
than shape assertions: a 2x2 confusion matrix with a textbook Gwet's AC1 and Cohen's kappa value
(demonstrating the divergence `docs/PRE-REGISTRATION.md` cites as the reason AC1 is primary), a
3-category confusion matrix for the `hand_count` task, an exclusion-counting case for CONTRACTS.md
rule 2 ("absence is explicit"), and perfect/zero-agreement edges.

Every arithmetic derivation below was cross-checked with `fractions.Fraction` at write time (see
the docstring on each test); the comments show the same arithmetic a reviewer can redo by hand.
"""

from __future__ import annotations

import pytest

from tests.fixtures import make_human_label, make_judge_response
from vernier.agreement.core import (
    build_agreement_result,
    cohens_kappa,
    fleiss_kappa,
    gwet_ac1,
    intra_rater_kappa,
    raw_agreement,
)
from vernier.models import HumanLabel, JudgeResponse

FRAME = "ego10k/f0051/w00243/v0007/{:06d}"


def _frame_id(i: int) -> str:
    return FRAME.format(i)


# --- (a) hand-computed 2x2 confusion matrix, task="manipulation" -----------------------------
#
# 20 frames. Confusion matrix (human rows, judge columns):
#
#              judge=True   judge=False
#   human=True     17            1        (row sum 18)
#   human=False     1            1        (row sum  2)
#
# p_a (raw agreement)      = (17 + 1) / 20 = 18/20 = 0.9
# human marginal(True)     = 18/20 = 0.9 ; marginal(False) = 2/20 = 0.1
# judge marginal(True)     = 18/20 = 0.9 ; marginal(False) = 2/20 = 0.1   (symmetric by design)
#
# Gwet's AC1 (q=2 categories):
#   pooled pi(True)  = (0.9 + 0.9) / 2 = 0.9
#   pooled pi(False) = (0.1 + 0.1) / 2 = 0.1
#   pe = 1/(q-1) * [pi(True)*(1-pi(True)) + pi(False)*(1-pi(False))]
#      = 1 * [0.9*0.1 + 0.1*0.9] = 0.09 + 0.09 = 0.18
#   AC1 = (p_a - pe) / (1 - pe) = (0.9 - 0.18) / (1 - 0.18) = 0.72 / 0.82 = 36/41 = 0.8780487804878049
#
# Cohen's kappa (uses each rater's OWN marginal, not pooled -- this is the whole point of AC1):
#   pe = P(human=True)*P(judge=True) + P(human=False)*P(judge=False) = 0.9*0.9 + 0.1*0.1 = 0.82
#   kappa = (0.9 - 0.82) / (1 - 0.82) = 0.08 / 0.18 = 4/9 = 0.4444444444444444
#
# AC1 (0.878) and kappa (0.444) diverge by more than 0.4 at 90% prevalence on an *identical*
# confusion matrix -- this is PRE-REGISTRATION.md's stated reason to prefer AC1.
def _binary_manipulation_pairs() -> tuple[list[HumanLabel], list[JudgeResponse]]:
    labels: list[HumanLabel] = []
    responses: list[JudgeResponse] = []
    i = 0
    # 17 x (human=True, judge=True)
    for _ in range(17):
        labels.append(make_human_label(frame_id=_frame_id(i), manipulation=True))
        responses.append(make_judge_response(frame_id=_frame_id(i), manipulation=True))
        i += 1
    # 1 x (human=False, judge=False)
    for _ in range(1):
        labels.append(make_human_label(frame_id=_frame_id(i), manipulation=False))
        responses.append(make_judge_response(frame_id=_frame_id(i), manipulation=False))
        i += 1
    # 1 x (human=True, judge=False)
    for _ in range(1):
        labels.append(make_human_label(frame_id=_frame_id(i), manipulation=True))
        responses.append(make_judge_response(frame_id=_frame_id(i), manipulation=False))
        i += 1
    # 1 x (human=False, judge=True)
    for _ in range(1):
        labels.append(make_human_label(frame_id=_frame_id(i), manipulation=False))
        responses.append(make_judge_response(frame_id=_frame_id(i), manipulation=True))
        i += 1
    assert len(labels) == 20
    return labels, responses


def test_raw_agreement_binary_manipulation_golden_case() -> None:
    labels, responses = _binary_manipulation_pairs()
    assert raw_agreement(labels, responses, "manipulation") == pytest.approx(0.9)


def test_gwet_ac1_binary_manipulation_golden_case() -> None:
    labels, responses = _binary_manipulation_pairs()
    assert gwet_ac1(labels, responses, "manipulation") == pytest.approx(36 / 41, abs=1e-9)


def test_cohens_kappa_binary_manipulation_golden_case() -> None:
    labels, responses = _binary_manipulation_pairs()
    assert cohens_kappa(labels, responses, "manipulation") == pytest.approx(4 / 9, abs=1e-9)


def test_ac1_and_kappa_diverge_at_high_prevalence_on_the_same_matrix() -> None:
    # The kappa paradox PRE-REGISTRATION.md cites as the reason AC1 is primary, made concrete:
    # same confusion matrix, same p_a, wildly different "expected chance agreement".
    labels, responses = _binary_manipulation_pairs()
    ac1 = gwet_ac1(labels, responses, "manipulation")
    kappa = cohens_kappa(labels, responses, "manipulation")
    assert ac1 - kappa > 0.4


# --- (c) hand-computed 3-category confusion matrix, task="hand_count" ------------------------
#
# 12 frames. Confusion matrix (human rows 0/1/2, judge columns 0/1/2):
#
#          j=0  j=1  j=2
#   h=0:    2    1    0     (row sum 3)
#   h=1:    0    3    1     (row sum 4)
#   h=2:    0    1    4     (row sum 5)
#
# p_a = (2 + 3 + 4) / 12 = 9/12 = 0.75
# human marginals: P(0)=3/12=0.25, P(1)=4/12=1/3, P(2)=5/12
# judge marginals: P(0)=2/12=1/6,  P(1)=5/12,     P(2)=5/12
#
# Gwet's AC1 multi-category generalisation (Gwet 2008; the formula below reduces to the textbook
# binary formula pe=2*p_bar*(1-p_bar) when q=2 -- see the module docstring for why this is the
# correct generalisation rather than an invented one):
#   pooled pi_j = (human_marginal_j + judge_marginal_j) / 2
#     pi_0 = (1/4 + 1/6)/2 = 5/24 = 0.20833333333333334
#     pi_1 = (1/3 + 5/12)/2 = 3/8 = 0.375
#     pi_2 = (5/12 + 5/12)/2 = 5/12 = 0.4166666666666667
#   pe = 1/(q-1) * sum_j pi_j*(1-pi_j),  q=3 so divide by 2:
#     pi_0*(1-pi_0) = 5/24 * 19/24 = 95/576
#     pi_1*(1-pi_1) = 3/8 * 5/8 = 15/64 = 135/576
#     pi_2*(1-pi_2) = 5/12 * 7/12 = 35/144 = 140/576
#     sum = 370/576 ; pe = 185/576 = 0.3211805555555556
#   AC1 = (0.75 - 185/576) / (1 - 185/576) = 247/391 = 0.6317135549872123
def _three_category_hand_count_pairs() -> tuple[list[HumanLabel], list[JudgeResponse]]:
    # (human, judge) -> count
    matrix = {
        (0, 0): 2, (0, 1): 1, (0, 2): 0,
        (1, 0): 0, (1, 1): 3, (1, 2): 1,
        (2, 0): 0, (2, 1): 1, (2, 2): 4,
    }
    labels: list[HumanLabel] = []
    responses: list[JudgeResponse] = []
    i = 0
    for (human_value, judge_value), count in matrix.items():
        for _ in range(count):
            labels.append(make_human_label(frame_id=_frame_id(i), hands_visible=human_value))
            responses.append(make_judge_response(frame_id=_frame_id(i), hands_visible=judge_value))
            i += 1
    assert len(labels) == 12
    return labels, responses


def test_gwet_ac1_three_category_hand_count_golden_case() -> None:
    labels, responses = _three_category_hand_count_pairs()
    assert gwet_ac1(labels, responses, "hand_count") == pytest.approx(247 / 391, abs=1e-9)


def test_raw_agreement_three_category_hand_count_golden_case() -> None:
    labels, responses = _three_category_hand_count_pairs()
    assert raw_agreement(labels, responses, "hand_count") == pytest.approx(0.75)


# --- (d) excluded (non-"ok") responses are dropped from the denominator ----------------------


def test_non_ok_responses_excluded_from_raw_agreement_denominator() -> None:
    labels, responses = _binary_manipulation_pairs()
    # responses[0] is one of the 17 agreeing (True, True) pairs. If it were silently coerced
    # rather than excluded, raw_agreement would still see all 20 pairs and 18 agreements;
    # excluding it correctly drops both: denominator 20->19, agreements 18->17.
    responses[0] = make_judge_response(
        frame_id=responses[0].frame_id, status="unparseable"
    )
    assert raw_agreement(labels, responses, "manipulation") == pytest.approx(17 / 19)


def test_non_ok_responses_excluded_from_ac1_denominator() -> None:
    labels, responses = _binary_manipulation_pairs()
    responses[0] = make_judge_response(frame_id=responses[0].frame_id, status="timeout")
    # Recompute the golden case by hand on the reduced 19-pair matrix: 16 (True,True), 1
    # (False,False), 1 (True,False), 1 (False,True).
    n = 19
    p_a = (16 + 1) / n
    human_true = (16 + 1) / n
    judge_true = (16 + 1) / n
    pi_true = (human_true + judge_true) / 2
    pi_false = 1 - pi_true
    pe = pi_true * (1 - pi_true) + pi_false * (1 - pi_false)
    expected = (p_a - pe) / (1 - pe)
    assert gwet_ac1(labels, responses, "manipulation") == pytest.approx(expected)


def test_build_agreement_result_counts_exclusions_by_reason() -> None:
    labels, responses = _binary_manipulation_pairs()
    responses[0] = make_judge_response(frame_id=responses[0].frame_id, status="unparseable")
    responses[1] = make_judge_response(frame_id=responses[1].frame_id, status="timeout")
    responses[2] = make_judge_response(frame_id=responses[2].frame_id, status="unparseable")

    from vernier.estimation.bootstrap import CLUSTER_BOOTSTRAP_B, CLUSTER_BOOTSTRAP_SEED
    from vernier.models import AgreementCI

    ci = AgreementCI(lo=0.1, hi=0.9, method="iid", clusters=None, B=None)
    result = build_agreement_result(
        "human:R1",
        "gemini-2.5-flash:P0",
        "manipulation",
        "G200-ego",
        labels,
        responses,
        ci,
        1.0,
    )

    assert result.n == 17
    assert result.n_excluded == 3
    assert result.excluded_why == {"unparseable": 2, "timeout": 1}
    assert result.raw_agreement == pytest.approx(raw_agreement(labels, responses, "manipulation"))
    assert result.ac1 == pytest.approx(gwet_ac1(labels, responses, "manipulation"))
    assert result.kappa == pytest.approx(cohens_kappa(labels, responses, "manipulation"))
    # unused imports guard: constants exist on the sibling (still-unimplemented) module without
    # this test touching its behaviour.
    assert CLUSTER_BOOTSTRAP_B > 0
    assert CLUSTER_BOOTSTRAP_SEED == 777


def test_a_label_with_no_matching_response_is_neither_counted_nor_excluded() -> None:
    labels, responses = _binary_manipulation_pairs()
    # An unmatched label contributes to neither n nor n_excluded: it is not a comparison pair
    # at all, since there is no response on the other side to compare it against.
    labels.append(make_human_label(frame_id="ego10k/no-matching-response", manipulation=True))

    from vernier.models import AgreementCI

    ci = AgreementCI(lo=0.1, hi=0.9, method="iid", clusters=None, B=None)
    result = build_agreement_result(
        "human:R1", "gemini-2.5-flash:P0", "manipulation", "G200-ego", labels, responses, ci, 1.0
    )
    assert result.n == 20
    assert result.n_excluded == 0
    assert result.excluded_why == {}


# --- (e) perfect-agreement and zero-agreement edges -------------------------------------------


def test_gwet_ac1_perfect_agreement_is_one() -> None:
    labels = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)]
    responses = [
        make_judge_response(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)
    ]
    assert gwet_ac1(labels, responses, "manipulation") == pytest.approx(1.0)


def test_cohens_kappa_perfect_agreement_is_one() -> None:
    labels = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)]
    responses = [
        make_judge_response(frame_id=_frame_id(i), manipulation=bool(i % 2)) for i in range(10)
    ]
    assert cohens_kappa(labels, responses, "manipulation") == pytest.approx(1.0)


def test_gwet_ac1_zero_observed_agreement_is_negative() -> None:
    # Every pair disagrees: human and judge always take opposite values.
    labels = [make_human_label(frame_id=_frame_id(i), manipulation=True) for i in range(10)]
    responses = [make_judge_response(frame_id=_frame_id(i), manipulation=False) for i in range(10)]
    ac1 = gwet_ac1(labels, responses, "manipulation")
    assert ac1 < 0


def test_cohens_kappa_zero_observed_agreement_is_negative() -> None:
    # NB: an all-True-vs-all-False matrix (mirroring the AC1 case above) gives kappa's pe = 0
    # too (P(human=True)*P(judge=True) + P(human=False)*P(judge=False) = 1*0 + 0*1 = 0), so
    # kappa collapses to 0 rather than negative -- a real quirk of the formula, not a bug, and
    # exactly the kind of instability PRE-REGISTRATION.md cites as the reason kappa is never the
    # headline. A balanced reversal (each rater 50/50, but always disagreeing) keeps pe > 0 and
    # actually exercises the negative case: pe = 0.5*0.5 + 0.5*0.5 = 0.5, pa = 0,
    # kappa = (0 - 0.5) / (1 - 0.5) = -1.0.
    labels = [make_human_label(frame_id=_frame_id(i), manipulation=bool(i % 2 == 0)) for i in range(10)]
    responses = [
        make_judge_response(frame_id=_frame_id(i), manipulation=bool(i % 2 != 0)) for i in range(10)
    ]
    kappa = cohens_kappa(labels, responses, "manipulation")
    assert kappa == pytest.approx(-1.0)


# --- fleiss_kappa: 3-judge, hand-computed golden case -----------------------------------------
#
# 4 frames, 3 judges, task="manipulation" (True/False). Per-frame (True-count, False-count)
# out of k=3 judges: f1=(3,0), f2=(2,1), f3=(0,3), f4=(2,1).
#
#   P_i = (sum_j n_ij^2 - k) / (k*(k-1)):
#     f1: (9+0-3)/6 = 1
#     f2: (4+1-3)/6 = 1/3
#     f3: (0+9-3)/6 = 1
#     f4: (4+1-3)/6 = 1/3
#   P_bar = (1 + 1/3 + 1 + 1/3) / 4 = (8/3)/4 = 2/3
#
#   total True ratings = 3+2+0+2 = 7 out of N*k = 12  -> p_true = 7/12
#   total False ratings = 0+1+3+1 = 5 out of 12       -> p_false = 5/12
#   P_e_bar = (7/12)^2 + (5/12)^2 = 49/144 + 25/144 = 74/144 = 37/72
#
#   kappa = (P_bar - P_e_bar) / (1 - P_e_bar) = (2/3 - 37/72) / (1 - 37/72)
#         = (11/72) / (35/72) = 11/35 = 0.3142857142857143
def test_fleiss_kappa_three_judge_golden_case() -> None:
    def judge_frames(values: list[bool]) -> list[JudgeResponse]:
        return [
            make_judge_response(frame_id=_frame_id(i), manipulation=v) for i, v in enumerate(values)
        ]

    responses_by_judge = {
        "judge-a": judge_frames([True, True, False, False]),
        "judge-b": judge_frames([True, True, False, True]),
        "judge-c": judge_frames([True, False, False, True]),
    }
    assert fleiss_kappa(responses_by_judge, "manipulation") == pytest.approx(11 / 35, abs=1e-9)


def test_fleiss_kappa_excludes_frames_with_a_non_ok_response_from_any_judge() -> None:
    def judge_frames(values: list[bool]) -> list[JudgeResponse]:
        return [
            make_judge_response(frame_id=_frame_id(i), manipulation=v) for i, v in enumerate(values)
        ]

    responses_by_judge = {
        "judge-a": judge_frames([True, True, False, False]),
        "judge-b": judge_frames([True, True, False, True]),
        "judge-c": judge_frames([True, False, False, True]),
    }
    # Corrupt judge-c's answer on f4 (index 3): if it silently fell back to a value instead of
    # being dropped, the result would differ from the 3-frame-only computation below.
    responses_by_judge["judge-c"][3] = make_judge_response(
        frame_id=_frame_id(3), status="refused"
    )

    def judge_frames_3(values: list[bool]) -> list[JudgeResponse]:
        return [
            make_judge_response(frame_id=_frame_id(i), manipulation=v) for i, v in enumerate(values)
        ]

    reduced = {
        "judge-a": judge_frames_3([True, True, False]),
        "judge-b": judge_frames_3([True, True, False]),
        "judge-c": judge_frames_3([True, False, False]),
    }
    assert fleiss_kappa(responses_by_judge, "manipulation") == pytest.approx(
        fleiss_kappa(reduced, "manipulation")
    )


# --- intra_rater_kappa: hand-computed golden case ----------------------------------------------
#
# 10 frames, same rater, primary vs. retest, task="manipulation".
# Confusion matrix: both True=7, both False=2, primary=True/retest=False=1, primary=False/retest=True=0.
#
#   p_a = (7+2)/10 = 0.9
#   primary marginal(True) = 8/10 = 0.8 ; retest marginal(True) = 7/10 = 0.7
#   pe = 0.8*0.7 + 0.2*0.3 = 0.56 + 0.06 = 0.62
#   kappa = (0.9 - 0.62) / (1 - 0.62) = 0.28/0.38 = 14/19 = 0.7368421052631579
def test_intra_rater_kappa_golden_case() -> None:
    primary_values = [True] * 7 + [False] * 2 + [True]
    retest_values = [True] * 7 + [False] * 2 + [False]
    primary = [
        make_human_label(frame_id=_frame_id(i), manipulation=v) for i, v in enumerate(primary_values)
    ]
    retest = [
        make_human_label(frame_id=_frame_id(i), manipulation=v, rater="R1")
        for i, v in enumerate(retest_values)
    ]
    assert intra_rater_kappa(primary, retest, "manipulation") == pytest.approx(14 / 19, abs=1e-9)


def test_unknown_task_raises_value_error() -> None:
    labels, responses = _binary_manipulation_pairs()
    with pytest.raises(ValueError):
        raw_agreement(labels, responses, "not-a-real-task")
