"""Rung 3: the abstention cascade -- confidence estimation, a threshold, and escalation.

What turns the distillate into an instrument with a stated floor (D026, H6). The threshold is
calibrated against held-out human gold and must never be tuned on the frames it will later
score. The module exposes coverage and floor as a pair; a caller cannot obtain one without
the other, because a floor at unstated coverage is meaningless.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, NamedTuple, Protocol

from vernier.models import FrameRef, HumanLabel


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

    def calibrate_threshold(self, held_out_gold: list[HumanLabel]) -> None:
        """Fit the abstention threshold. Must be called with gold the cascade will never be
        scored against again.

        Finds the highest-coverage confidence threshold such that predictions at or above it
        achieve >= `target_floor` accuracy against `held_out_gold`: sort by confidence
        descending, and take the longest prefix whose cumulative accuracy still clears the
        floor. If no non-empty prefix clears it -- the floor is unreachable at any coverage > 0
        on this gold -- raises `ValueError` rather than silently picking a near-zero-coverage
        threshold that cannot actually deliver the stated guarantee (D026).

        **No safety margin.** The reported floor is a point estimate on `held_out_gold`, not a
        statistically-guaranteed lower bound -- there is no confidence interval or correction
        for the finite size of `held_out_gold`, so on a small held-out set this can pick a
        threshold that clears `target_floor` on this particular sample by chance without
        reliably clearing it on new data. A larger `held_out_gold` reduces this risk; it is not
        eliminated by this implementation. Independent review flagged this explicitly --
        resolving it with an actual lower-confidence-bound (e.g. a Wilson-score interval on the
        prefix accuracy) is future work, not done here.
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
            if correct / i >= self._target_floor:
                best_threshold = confidence

        if best_threshold is None:
            raise ValueError(
                f"target floor {self._target_floor} is unreachable at any coverage > 0 "
                "on the given held-out gold"
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
