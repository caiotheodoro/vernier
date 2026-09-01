"""Behavioural tests for `vernier.distil.cascade`, written before `AbstentionCascade.__init__`
exists (only the three frozen stub methods were present).

A fake distillate + confidence function stand in for `LinearProbe` -- the cascade's contract
is calibration/abstention logic, not any real ML, so a controlled synthetic scorer lets every
case below be hand-verified. `_features_for` is monkeypatched to the identity function so the
fake distillate/confidence function can key directly off `frame_id`.

Case (a) is the golden case for the whole module (D026/H6): a distillate that is right with
high confidence on some frames and wrong with low confidence on others must calibrate a
threshold that abstains on the low-confidence-wrong frames, so `coverage_and_floor` reports a
floor *higher* than raw (un-abstained) accuracy would be -- that gap is the entire point of
Trust-or-Escalate.
"""

from __future__ import annotations

from collections.abc import Callable

import pytest

from tests.fixtures import make_frame_ref, make_human_label
from vernier.distil.cascade import AbstentionCascade, CoverageAndFloor
from vernier.models import HumanLabel


class FakeDistillate:
    """Predicts by frame_id lookup -- deterministic, no ML."""

    def __init__(self, predictions: dict[str, int]) -> None:
        self._predictions = predictions

    def predict(self, features: list[str]) -> list[int]:
        return [self._predictions[f] for f in features]


def make_confidence_fn(confidences: dict[str, float]) -> Callable[[list[str]], list[float]]:
    def _fn(features: list[str]) -> list[float]:
        return [confidences[f] for f in features]

    return _fn


def _identity_features_for(frame_id: str) -> str:
    return frame_id


def _cascade(
    predictions: dict[str, int], confidences: dict[str, float], target_floor: float = 0.80
) -> AbstentionCascade:
    cascade = AbstentionCascade(
        distillate=FakeDistillate(predictions),
        confidence_fn=make_confidence_fn(confidences),
        target_floor=target_floor,
    )
    cascade._features_for = _identity_features_for  # type: ignore[method-assign]
    return cascade


# --- (a) calibration abstains on the low-confidence-wrong frames, floor beats raw accuracy ---
#
# 7 frames: predicted correctly (hands_visible=1), confidence 0.9.
# 3 frames: predicted wrongly (predict 0, gold 1), confidence 0.2.
# Raw accuracy over all 10 = 7/10 = 0.7.
# With target_floor=0.95, only the top-7-by-confidence prefix clears the floor (7/7 = 1.0);
# adding an 8th (a wrong, low-confidence frame) drops to 7/8 = 0.875 < 0.95. So the calibrated
# threshold must sit at 0.9, abstaining on all 3 wrong frames, and the achieved floor (1.0) is
# strictly higher than raw accuracy (0.7) at reduced coverage (0.7).


def _correct_id(i: int) -> str:
    return f"correct-{i}"


def _wrong_id(i: int) -> str:
    return f"wrong-{i}"


def _golden_gold() -> list[HumanLabel]:
    correct = [
        make_human_label(frame_id=_correct_id(i), hands_visible=1, manipulation=True)
        for i in range(7)
    ]
    wrong = [
        make_human_label(frame_id=_wrong_id(i), hands_visible=1, manipulation=True)
        for i in range(3)
    ]
    return correct + wrong


def _golden_predictions_and_confidences() -> tuple[dict[str, int], dict[str, float]]:
    predictions = {_correct_id(i): 1 for i in range(7)} | {_wrong_id(i): 0 for i in range(3)}
    confidences = {_correct_id(i): 0.9 for i in range(7)} | {_wrong_id(i): 0.2 for i in range(3)}
    return predictions, confidences


def test_calibration_abstains_on_low_confidence_wrong_frames_and_raises_the_floor() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.95)
    gold = _golden_gold()

    cascade.calibrate_threshold(gold)

    for i in range(7):
        label, abstain = cascade.predict(make_frame_ref(frame_id=_correct_id(i)))
        assert (label, abstain) == (1, False)
    for i in range(3):
        label, abstain = cascade.predict(make_frame_ref(frame_id=_wrong_id(i)))
        assert (label, abstain) == (None, True)

    result = cascade.coverage_and_floor(gold)
    raw_accuracy = 7 / 10
    assert result.coverage == pytest.approx(0.7)
    assert result.agreement_floor == pytest.approx(1.0)
    assert result.agreement_floor > raw_accuracy


# --- (b) predict before calibrate_threshold raises -------------------------------------------


def test_predict_before_calibrate_raises() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences)

    with pytest.raises(RuntimeError):
        cascade.predict(make_frame_ref(frame_id=_correct_id(0)))


def test_coverage_and_floor_before_calibrate_raises() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences)

    with pytest.raises(RuntimeError):
        cascade.coverage_and_floor(_golden_gold())


# --- (c) coverage_and_floor always returns the pair together, never a bare float -------------


def test_coverage_and_floor_returns_the_named_pair() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.6)
    gold = _golden_gold()
    cascade.calibrate_threshold(gold)

    result = cascade.coverage_and_floor(gold)

    assert isinstance(result, CoverageAndFloor)
    assert isinstance(result, tuple)
    assert not isinstance(result, float)
    assert result.coverage == result[0]
    assert result.agreement_floor == result[1]


# --- (d) target floor unreachable at any coverage > 0 -----------------------------------------
#
# Every frame is predicted wrong regardless of confidence -- no threshold, however high, can
# ever clear a 0.99 floor (dropping to a single frame still yields 0/1 accuracy). Silently
# reporting a near-zero-coverage threshold here would assert a guarantee that does not exist
# (D026's whole point is a *provable* floor); calibrate_threshold raises instead of fabricating
# a threshold that cannot deliver it.


def test_calibrate_raises_when_target_floor_is_unreachable() -> None:
    gold = _golden_gold()
    all_wrong_predictions = {label.frame_id: 0 for label in gold}
    confidences = {label.frame_id: 0.9 for label in gold}
    cascade = _cascade(all_wrong_predictions, confidences, target_floor=0.99)

    with pytest.raises(ValueError):
        cascade.calibrate_threshold(gold)


# --- calibration and evaluation gold must not be the same set in real use ----------------------
#
# The golden case above (test_calibration_abstains_...) reuses one gold set for both calls
# deliberately, as a mechanism check -- it verifies the threshold-finding algorithm, not a real
# floor estimate, and reviewer-flagged as a low-severity nit for exactly that reason. This test
# demonstrates the same mechanism holds with genuinely DISJOINT calibration and evaluation gold,
# which is the D026/H6-faithful usage a real caller must follow (D031's train/eval-leak shape,
# checked here since docs/WAVES.md names this cascade as the next place it could recur).


def test_calibrate_and_evaluate_on_disjoint_gold_still_shows_the_floor_gap() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.95)

    calibration_gold = _golden_gold()
    evaluation_gold = [
        make_human_label(frame_id=_correct_id(i), hands_visible=1, manipulation=True)
        for i in range(7, 14)
    ]
    predictions.update({_correct_id(i): 1 for i in range(7, 14)})
    confidences.update({_correct_id(i): 0.9 for i in range(7, 14)})

    cascade.calibrate_threshold(calibration_gold)
    result = cascade.coverage_and_floor(evaluation_gold)

    assert result.coverage == pytest.approx(1.0)
    assert result.agreement_floor == pytest.approx(1.0)


# --- __init__ defaults -------------------------------------------------------------------------


def test_default_target_floor_matches_h6() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = AbstentionCascade(
        distillate=FakeDistillate(predictions), confidence_fn=make_confidence_fn(confidences)
    )
    assert cascade._target_floor == pytest.approx(0.80)
