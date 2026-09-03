"""Rung 3: the abstention cascade -- confidence estimation, a threshold, and escalation.

What turns the distillate into an instrument with a stated floor (D026, H6). The threshold is
calibrated against held-out human gold and must never be tuned on the frames it will later
score. The module exposes coverage and floor as a pair; a caller cannot obtain one without
the other, because a floor at unstated coverage is meaningless.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple, Protocol

from scipy.stats import norm

from vernier.models import FrameRef, HumanLabel


def _wilson_lower_bound(k: int, n: int, confidence_level: float) -> float:
    """Wilson-score lower confidence bound on a binomial proportion `k/n`, at `confidence_level`
    (e.g. 0.95 for a 95% one-sided lower bound). One-sided `z` deliberately -- `calibrate_
    threshold` only ever needs a lower bound, never the two-sided interval `estimation/ppi.py`
    uses for its `lo`/`hi` pair."""
    if n == 0:
        return 0.0
    z: float = float(norm.ppf(confidence_level))
    p_hat = k / n
    denom = 1 + z**2 / n
    center = p_hat + z**2 / (2 * n)
    margin = z * ((p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) ** 0.5)
    return float((center - margin) / denom)


class CoverageAndFloor(NamedTuple):
    """Always returned together -- see module docstring."""

    coverage: float
    agreement_floor: float


class Distillate(Protocol):
    """Structural type for the thing this cascade wraps -- `LinearProbe` satisfies this without
    inheriting from it. Only `predict` is required: confidence is supplied separately (see
    `AbstentionCascade.__init__`), because `LinearProbe.predict` returns bare class labels with
    no confidence, and this module must not reach into its sklearn internals to invent one."""

    def predict(self, features: Any) -> list[int]: ...


# `features -> one confidence score per prediction`, batched the same way `Distillate.predict`
# is. Injected rather than required on `Distillate` itself: see `__init__` docstring.
ConfidenceFn = Callable[[Any], list[float]]


class AbstentionCascade:
    """Wraps a distillate (`LinearProbe` or `Qwen3VLLoRA`) with a calibrated abstention gate."""

    def __init__(
        self,
        distillate: Distillate,
        confidence_fn: ConfidenceFn,
        target_floor: float = 0.80,
    ) -> None:
        """`confidence_fn` is an injected callable rather than a second required Protocol method
        because `LinearProbe` (Wave 1's only real distillate) does not expose a `predict_proba`
        -style method today -- it wraps sklearn's `LogisticRegression`, which does, but that is
        not surfaced on `LinearProbe` itself. Requiring `predict_proba` on the `Distillate`
        Protocol would silently assume a method that does not exist on the one concrete type
        Wave 1 ships; a reviewer should check whether `linear_probe.py` ever adds one, at which
        point a caller can wire `confidence_fn=lambda feats: probe.predict_proba(feats).max(axis=1)`
        without any change here. `target_floor` is the H6 pre-registered target (>= 0.80); the
        matching coverage is an *output* of calibration, not a tunable input, so it has no
        constructor parameter -- see `coverage_and_floor`.
        """
        self._distillate = distillate
        self._confidence_fn = confidence_fn
        self._target_floor = target_floor
        self._threshold: float | None = None

    def _features_for(self, frame_id: str) -> Any:
        """Features-lookup seam. Wave 1 has no wired feature store, so this stub raises;
        production code (or a test) supplies a real lookup by assigning over this method on the
        instance, e.g. `cascade._features_for = lambda frame_id: store[frame_id]`."""
        raise NotImplementedError(f"no features lookup wired for frame_id={frame_id!r}")

    def _gold_value(self, label: HumanLabel) -> int:
        """The distillate's predictions are compared against `hands_visible` -- H6's
        pre-registered hand-task target. H6 also names a manipulation-task floor at the same
        threshold-calibration mechanism; wiring that up means overriding this method (or
        subclassing), not changing it here, since Wave 1 only commits to the hand task."""
        return label.hands_visible

    def _predict_by_id(self, frame_id: str) -> tuple[Any | None, bool]:
        if self._threshold is None:
            raise RuntimeError("calibrate_threshold must be called before predict")
        features = self._features_for(frame_id)
        prediction = self._distillate.predict([features])[0]
        confidence = self._confidence_fn([features])[0]
        if confidence < self._threshold:
            return None, True
        return prediction, False

    def calibrate_threshold(
        self, held_out_gold: list[HumanLabel], *, confidence_level: float = 0.95
    ) -> None:
        """Fit the abstention threshold. Must be called with gold the cascade will never be
        scored against again.

        Finds the highest-coverage confidence threshold such that predictions at or above it
        achieve a `confidence_level`-level Wilson-score lower bound on accuracy >= `target_floor`
        against `held_out_gold`: sort by confidence descending, and take the longest prefix whose
        Wilson lower bound on cumulative accuracy still clears the floor. If no non-empty prefix
        clears it -- the floor is unreachable at any coverage > 0 on this gold, at this
        confidence level -- raises `ValueError` rather than silently picking a near-zero-coverage
        threshold that cannot actually deliver the stated guarantee (D026).

        **Real safety margin, still a real remaining gap.** D049 named the fix and this applies
        it: the reported floor is now a `confidence_level`-level Wilson-score lower bound on
        prefix accuracy, not the raw point estimate -- a small held-out set can no longer clear
        `target_floor` by chance and have that reported as if it were reliable. This is not the
        full fix D049 names, though: a Wilson bound treats each prefix's accuracy as an
        independent Bernoulli draw, which ignores that successive prefixes are nested, overlapping
        samples, not independent ones. Full Learn-then-Test / conformal risk control (2110.01052,
        the machinery Trust-or-Escalate itself builds on) remains the eventual, not-yet-implemented
        complete answer for that; this is the cheaper, real, disclosed interim step D049's own
        text already named as reachable, not a claim that D049 is fully closed.
        """
        features = [self._features_for(label.frame_id) for label in held_out_gold]
        predictions = self._distillate.predict(features)
        confidences = self._confidence_fn(features)
        gold_values = [self._gold_value(label) for label in held_out_gold]

        triples = sorted(
            zip(confidences, predictions, gold_values), key=lambda t: t[0], reverse=True
        )

        best_threshold: float | None = None
        correct = 0
        for i, (confidence, prediction, gold_value) in enumerate(triples, start=1):
            correct += int(prediction == gold_value)
            if _wilson_lower_bound(correct, i, confidence_level) >= self._target_floor:
                best_threshold = confidence

        if best_threshold is None:
            raise ValueError(
                f"target floor {self._target_floor} is unreachable (at {confidence_level:.0%} "
                "confidence) at any coverage > 0 on the given held-out gold"
            )
        self._threshold = best_threshold

    def predict(self, frame: FrameRef) -> tuple[Any | None, bool]:
        """Returns `(label, should_abstain)`. `label` is `None` iff `should_abstain` is True."""
        return self._predict_by_id(frame.frame_id)

    def coverage_and_floor(self, gold: list[HumanLabel]) -> CoverageAndFloor:
        """Report the pair together, per the module seam -- never floor alone."""
        n = len(gold)
        n_answered = 0
        n_correct = 0
        for label in gold:
            prediction, abstained = self._predict_by_id(label.frame_id)
            if abstained:
                continue
            n_answered += 1
            if prediction == self._gold_value(label):
                n_correct += 1
        coverage = n_answered / n if n else 0.0
        agreement_floor = n_correct / n_answered if n_answered else 0.0
        return CoverageAndFloor(coverage=coverage, agreement_floor=agreement_floor)
