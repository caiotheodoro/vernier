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
from vernier.distil.cascade import AbstentionCascade, CoverageAndFloor, _wilson_lower_bound
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
    # confidence_level=0.5 is a deliberate mechanism-check pin, not the real default: at that
    # level the Wilson lower bound (docs/DECISIONS.md D063) collapses to the raw point estimate
    # (z = norm.ppf(0.5) == 0.0, so the bound reduces to correct/i exactly), which is what makes
    # this small, hand-verified 7/3 fixture's fractions still checkable by hand. At the real
    # default confidence_level=0.95, small-n golden cases like this one are exactly where a
    # Wilson bound is least forgiving -- see
    # test_wilson_confidence_makes_the_floor_harder_to_clear_at_small_n below for that behaviour.
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.95)
    gold = _golden_gold()

    cascade.calibrate_threshold(gold, confidence_level=0.5)

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
    # confidence_level=0.5 pinned for the same mechanism-check reason as the golden case above.
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.95)

    calibration_gold = _golden_gold()
    evaluation_gold = [
        make_human_label(frame_id=_correct_id(i), hands_visible=1, manipulation=True)
        for i in range(7, 14)
    ]
    predictions.update({_correct_id(i): 1 for i in range(7, 14)})
    confidences.update({_correct_id(i): 0.9 for i in range(7, 14)})

    cascade.calibrate_threshold(calibration_gold, confidence_level=0.5)
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


# --- _wilson_lower_bound (D063): Wilson-score lower confidence bound on a binomial proportion --


def test_wilson_lower_bound_matches_a_published_reference_value() -> None:
    # Cross-checked independently of this codebase: the standard (non-continuity-corrected)
    # Wilson score interval for 8 successes out of 10 trials, two-sided 95% (z=1.96, i.e.
    # confidence_level=0.975 for the one-sided lower half of that interval), has a published
    # lower bound of ~0.4902 -- a commonly cited textbook example, not derived from this
    # function's own formula.
    assert _wilson_lower_bound(8, 10, 0.975) == pytest.approx(0.4902, abs=1e-4)


def test_wilson_lower_bound_at_confidence_level_half_collapses_to_the_point_estimate() -> None:
    # z = norm.ppf(0.5) == 0.0 exactly, so the Wilson bound reduces to the raw point estimate --
    # the mechanism the small-n golden-case tests above rely on to stay hand-verifiable.
    assert _wilson_lower_bound(7, 7, 0.5) == pytest.approx(1.0)
    assert _wilson_lower_bound(3, 10, 0.5) == pytest.approx(0.3)


def test_wilson_lower_bound_edges_stay_in_zero_one() -> None:
    assert _wilson_lower_bound(0, 5, 0.95) == pytest.approx(0.0)
    assert 0.0 <= _wilson_lower_bound(5, 5, 0.95) <= 1.0
    assert _wilson_lower_bound(0, 0, 0.95) == 0.0


def test_wilson_lower_bound_decreases_as_confidence_level_increases() -> None:
    lb_90 = _wilson_lower_bound(8, 10, 0.90)
    lb_95 = _wilson_lower_bound(8, 10, 0.95)
    lb_99 = _wilson_lower_bound(8, 10, 0.99)
    assert lb_90 > lb_95 > lb_99


# --- calibrate_threshold's real Wilson-LCB behaviour change (D063) -----------------------------


def test_calibrate_threshold_default_confidence_level_is_the_real_095() -> None:
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.6)
    gold = _golden_gold()

    # No confidence_level kwarg -- backward-compatible positional call, same as every existing
    # real caller (scripts/distill_rung1.py).
    cascade.calibrate_threshold(gold)

    for i in range(7):
        label, abstain = cascade.predict(make_frame_ref(frame_id=_correct_id(i)))
        assert (label, abstain) == (1, False)


def test_wilson_confidence_correctly_refuses_a_threshold_the_point_estimate_would_accept() -> None:
    # The same 7-correct/3-wrong golden shape as the mechanism-check tests above, at the real
    # default confidence_level=0.95: the raw point estimate at the 7/7 prefix is 1.0 (would
    # clear target_floor=0.95 under the pre-D063 point-estimate search), but its Wilson lower
    # bound at 95% confidence is far below 0.95 -- this small a held-out set cannot actually
    # support that guarantee, and calibrate_threshold must now say so instead of asserting it.
    predictions, confidences = _golden_predictions_and_confidences()
    cascade = _cascade(predictions, confidences, target_floor=0.95)
    gold = _golden_gold()

    with pytest.raises(ValueError):
        cascade.calibrate_threshold(gold, confidence_level=0.95)


def test_wilson_confidence_still_reaches_a_realistic_floor_at_larger_n() -> None:
    # 100 correct at high confidence, 5 wrong at low confidence -- large enough that the Wilson
    # lower bound on the full-100 prefix is not crippled by small-n the way the 7-frame golden
    # case is, demonstrating the fix doesn't make calibration impossible in general.
    correct_predictions = {f"ok-{i}": 1 for i in range(100)}
    correct_confidences = {f"ok-{i}": 0.9 for i in range(100)}
    wrong_predictions = {f"bad-{i}": 0 for i in range(5)}
    wrong_confidences = {f"bad-{i}": 0.2 for i in range(5)}
    predictions = correct_predictions | wrong_predictions
    confidences = correct_confidences | wrong_confidences
    gold = [
        make_human_label(frame_id=f"ok-{i}", hands_visible=1, manipulation=True)
        for i in range(100)
    ] + [
        make_human_label(frame_id=f"bad-{i}", hands_visible=1, manipulation=True)
        for i in range(5)
    ]
    cascade = _cascade(predictions, confidences, target_floor=0.80)

    cascade.calibrate_threshold(gold, confidence_level=0.95)
    result = cascade.coverage_and_floor(gold)

    assert result.agreement_floor >= 0.80
