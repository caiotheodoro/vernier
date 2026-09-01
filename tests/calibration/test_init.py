"""Behavioural tests for `vernier.calibration`, written before the body exists.

`ece`'s golden case is computed by hand in a comment next to the assertion (standard ECE:
sum over non-empty bins of (n_i/N) * |accuracy_i - mean_conf_i|). Empty-bin handling
(CONTRACTS.md, PRE-REGISTRATION.md "Calibration" row: "empty bins reported empty, never
merged") gets its own test so a future change cannot silently start dropping or merging them.
"""

from __future__ import annotations

import pytest

from tests.fixtures import make_judge_response
from vernier.calibration import (
    FIXED_BIN_COUNT,
    build_calibration_report,
    compute_delta_j,
    compute_j,
    ece,
    reliability_bins,
)
from vernier.models import CalibrationBin

# --- reliability_bins --------------------------------------------------------------------


def test_reliability_bins_default_bin_count_and_edges() -> None:
    bins = reliability_bins([0.05], [True])

    assert len(bins) == FIXED_BIN_COUNT == 10
    assert bins[0].lo == pytest.approx(0.0)
    assert bins[0].hi == pytest.approx(0.1)
    assert bins[-1].lo == pytest.approx(0.9)
    assert bins[-1].hi == pytest.approx(1.0)


def test_reliability_bins_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError):
        reliability_bins([0.1, 0.2], [True])


def test_reliability_bins_last_bin_includes_confidence_of_one() -> None:
    bins = reliability_bins([1.0], [True])

    assert bins[-1].n == 1
    assert bins[-1].mean_conf == pytest.approx(1.0)
    assert bins[-1].accuracy == pytest.approx(1.0)
    # every other bin, including bin 8 which is adjacent to the last edge, stays empty
    for b in bins[:-1]:
        assert b.n == 0
        assert b.mean_conf is None
        assert b.accuracy is None


def test_reliability_bins_empty_bin_reported_not_dropped_or_merged() -> None:
    # Points land only in bin 0 ([0, 0.1)) and bin 9 ([0.9, 1.0]) -- bins 1..8 must still
    # appear in the returned list, each with n=0 and null mean_conf/accuracy.
    confidences = [0.05, 0.95]
    correct = [True, True]

    bins = reliability_bins(confidences, correct)

    assert len(bins) == 10
    for i in range(1, 9):
        assert bins[i].n == 0
        assert bins[i].mean_conf is None
        assert bins[i].accuracy is None
    assert bins[0].n == 1
    assert bins[9].n == 1


def test_reliability_bins_computes_mean_conf_and_accuracy_per_bin() -> None:
    # bin1 = [0.1, 0.2): two points, confidences 0.12 and 0.18 -> mean 0.15; one correct -> 0.5
    confidences = [0.12, 0.18]
    correct = [True, False]

    bins = reliability_bins(confidences, correct)

    assert bins[1].n == 2
    assert bins[1].mean_conf == pytest.approx(0.15)
    assert bins[1].accuracy == pytest.approx(0.5)


# --- ece -----------------------------------------------------------------------------------


def test_ece_hand_computed_golden_case() -> None:
    # confidences = [0.05, 0.15, 0.85, 0.95], correct = [True, False, True, True]
    # bin0 [0.0,0.1): {0.05: True}  -> n=1, mean_conf=0.05, accuracy=1.0
    # bin1 [0.1,0.2): {0.15: False} -> n=1, mean_conf=0.15, accuracy=0.0
    # bin8 [0.8,0.9): {0.85: True} -> n=1, mean_conf=0.85, accuracy=1.0
    # bin9 [0.9,1.0]: {0.95: True} -> n=1, mean_conf=0.95, accuracy=1.0
    # all other bins empty, contribute 0.
    # N = 4
    # ECE = (1/4)|1.0-0.05| + (1/4)|0.0-0.15| + (1/4)|1.0-0.85| + (1/4)|1.0-0.95|
    #     = 0.25*0.95 + 0.25*0.15 + 0.25*0.15 + 0.25*0.05
    #     = 0.2375 + 0.0375 + 0.0375 + 0.0125
    #     = 0.325
    confidences = [0.05, 0.15, 0.85, 0.95]
    correct = [True, False, True, True]

    bins = reliability_bins(confidences, correct)

    assert ece(bins) == pytest.approx(0.325)


def test_ece_empty_bins_contribute_zero() -> None:
    # The n=0 bin carries non-null mean_conf/accuracy to prove exclusion is keyed on `n`, not
    # on whether those fields happen to be populated.
    bins = [
        CalibrationBin(lo=0.0, hi=0.5, n=4, mean_conf=0.5, accuracy=0.5),
        CalibrationBin(lo=0.5, hi=1.0, n=0, mean_conf=0.9, accuracy=0.1),
    ]

    assert ece(bins) == pytest.approx(0.0)


def test_ece_perfectly_calibrated_data_is_near_zero() -> None:
    # 4 equal-width bins; within each bin, confidence is constant and the fraction of
    # `correct` items exactly equals that confidence, so mean_conf == accuracy in every
    # non-empty bin and ECE is exactly 0, not merely approximately.
    confidences: list[float] = []
    correct: list[bool] = []
    for conf, n_correct in [(0.1, 1), (0.3, 3), (0.6, 6), (0.9, 9)]:
        for i in range(10):
            confidences.append(conf)
            correct.append(i < n_correct)

    bins = reliability_bins(confidences, correct, n_bins=4)

    assert ece(bins) == pytest.approx(0.0, abs=1e-9)


def test_ece_explicit_manual_bins() -> None:
    bins = [
        CalibrationBin(lo=0.0, hi=0.5, n=8, mean_conf=0.4, accuracy=0.5),
        CalibrationBin(lo=0.5, hi=1.0, n=2, mean_conf=0.9, accuracy=0.9),
        CalibrationBin(lo=1.0, hi=1.5, n=0, mean_conf=None, accuracy=None),
    ]
    # N = 10
    # ECE = (8/10)|0.5-0.4| + (2/10)|0.9-0.9| + 0
    #     = 0.8*0.1 + 0.2*0.0
    #     = 0.08
    assert ece(bins) == pytest.approx(0.08)


# --- compute_j / compute_delta_j ------------------------------------------------------------
#
# docs/SURVEY.md and docs/DECISIONS.md D028 describe arXiv 2605.06939 only at the level of
# "judge quality J" and "cross-corpus calibration instability delta-J" -- neither this repo nor
# this implementation has verified the paper's exact statistic. Per the task instructions this
# is therefore a clearly-flagged PLACEHOLDER (simple accuracy against gold, and range-of-J
# across corpora), not the paper's real metric -- these tests pin the placeholder's documented
# behaviour, not a claim about the paper.


def test_compute_j_placeholder_is_accuracy_against_gold() -> None:
    responses = [make_judge_response(), make_judge_response(), make_judge_response(), make_judge_response()]
    gold_correct = [True, True, True, False]

    assert compute_j(responses, gold_correct) == pytest.approx(0.75)


def test_compute_j_mismatched_lengths_raises() -> None:
    responses = [make_judge_response()]
    with pytest.raises(ValueError):
        compute_j(responses, [True, False])


def test_compute_j_is_flagged_placeholder_in_docstring() -> None:
    assert "PLACEHOLDER" in (compute_j.__doc__ or "")


def test_compute_delta_j_placeholder_is_range() -> None:
    j_by_corpus = {"egocentric-10k": 0.6, "ego4d": 0.9, "epic-kitchens-100": 0.75}

    assert compute_delta_j(j_by_corpus) == pytest.approx(0.9 - 0.6)


def test_compute_delta_j_single_corpus_is_zero() -> None:
    assert compute_delta_j({"egocentric-10k": 0.6}) == pytest.approx(0.0)


def test_compute_delta_j_empty_raises() -> None:
    with pytest.raises(ValueError):
        compute_delta_j({})


def test_compute_delta_j_is_flagged_placeholder_in_docstring() -> None:
    assert "PLACEHOLDER" in (compute_delta_j.__doc__ or "")


# --- build_calibration_report ---------------------------------------------------------------


def test_build_calibration_report_computes_ece_internally() -> None:
    confidences = [0.05, 0.15, 0.85, 0.95]
    correct = [True, False, True, True]
    bins = reliability_bins(confidences, correct)

    report = build_calibration_report(
        judge="gemini-2.5-flash",
        task="manipulation",
        subset="G200-ego",
        confidence_kind="verbalized",
        bins=bins,
    )

    assert report.judge == "gemini-2.5-flash"
    assert report.task == "manipulation"
    assert report.subset == "G200-ego"
    assert report.confidence_kind == "verbalized"
    assert report.ece == pytest.approx(0.325)
    assert len(report.bins) == 10
    assert report.note


def test_build_calibration_report_keeps_empty_bins() -> None:
    bins = reliability_bins([0.0], [True])

    report = build_calibration_report(
        judge="gemini-2.5-flash",
        task="manipulation",
        subset="G200-ego",
        confidence_kind="logprob",
        bins=bins,
    )

    assert len(report.bins) == 10
    empty = [b for b in report.bins if b.n == 0]
    assert len(empty) == 9
    for b in empty:
        assert b.mean_conf is None
        assert b.accuracy is None
