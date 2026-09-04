"""Rung 1: a linear probe on frozen features. Cheap, laptop-runnable, the baseline that must
be beaten to justify anything more expensive.

Training targets are `gemini-2.5-flash` P0 labels -- the judge, deliberately, not human gold.
Human gold is the held-out evaluation for both the judge and its distillate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import joblib
import numpy as np
from sklearn.linear_model import LogisticRegression

from vernier.models import JudgeResponse


def _filter_and_align(
    features: Any, judge_labels: list[JudgeResponse]
) -> tuple[Any, list[int]]:
    """`features[i]` is assumed to correspond positionally to `judge_labels[i]` -- an implicit
    contract CONTRACTS.md does not itself state, so callers must keep the two in the same row
    order. Rows whose label has `status != "ok"` are dropped from `judge_labels` and from
    `features` together, by the same index set, so filtering can never desynchronise the two
    (CONTRACTS.md's "absence is explicit": a non-"ok" response carries no `hands_visible` to
    train or score against).
    """
    keep = [i for i, label in enumerate(judge_labels) if label.status == "ok"]
    aligned_features = np.asarray(features)[keep]
    aligned_labels = [cast(int, judge_labels[i].hands_visible) for i in keep]
    return aligned_features, aligned_labels


class LinearProbe:
    """A linear probe trained on frozen backbone features against judge labels."""

    def __init__(self) -> None:
        self._model: LogisticRegression | None = None

    def fit(self, features: Any, judge_labels: list[JudgeResponse]) -> None:
        aligned_features, aligned_labels = _filter_and_align(features, judge_labels)
        model = LogisticRegression(max_iter=1000)
        model.fit(aligned_features, aligned_labels)
        self._model = model

    def predict(self, features: Any) -> list[int]:
        if self._model is None:
            raise RuntimeError("LinearProbe.predict called before fit")
        return [int(p) for p in self._model.predict(np.asarray(features))]

    def predict_proba(self, features: Any) -> list[float]:
        """Max class probability per row -- the confidence source `cascade.py`'s own docstring
        names as the anticipated extension point (`AbstentionCascade`'s `confidence_fn` is
        injected specifically because this method didn't exist yet). Real `sklearn`
        `predict_proba`, not invented: this just surfaces it and reduces to the winning class's
        probability, matching what `predict` itself reports."""
        if self._model is None:
            raise RuntimeError("LinearProbe.predict_proba called before fit")
        return [float(row.max()) for row in self._model.predict_proba(np.asarray(features))]

    def save(self, path: str | Path) -> None:
        """Persist the fitted sklearn model via `joblib` -- turns a training run into a real,
        loadable artifact (`docs/DECISIONS.md` D064), not just the metrics it produced. Loading
        the weights back is not the whole instrument: a caller also needs the exact backbone
        (`facebook/dinov2-small`, `scripts/distill_rung1.py`'s `_BACKBONE`), its `_preprocess`
        steps, and its mean-pooling-over-patch-tokens choice -- none of that travels with the
        weights, by construction, since this class only ever sees already-extracted features."""
        if self._model is None:
            raise RuntimeError("LinearProbe.save called before fit")
        joblib.dump(self._model, path)

    @classmethod
    def load(cls, path: str | Path) -> "LinearProbe":
        probe = cls()
        probe._model = joblib.load(path)
        return probe


def fidelity(probe: LinearProbe, held_out_features: Any, teacher_labels: list[JudgeResponse]) -> float:
    """Point estimate of teacher fidelity: probe agreement with `gemini-2.5-flash` P0a
    (`teacher_labels`) on hand presence. Diagnostic, not the H6 claim -- the claim is the
    abstention cascade's floor-at-coverage against human gold, in `cascade.py`."""
    aligned_features, aligned_labels = _filter_and_align(held_out_features, teacher_labels)
    predictions = probe.predict(aligned_features)
    matches = sum(1 for p, t in zip(predictions, aligned_labels) if p == t)
    return matches / len(aligned_labels)
