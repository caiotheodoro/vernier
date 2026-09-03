"""Behavioural tests for `vernier.distil.linear_probe`, written before the bodies exist.

Rung 1 (docs/METHOD.md E7): a linear probe trained on `gemini-2.5-flash` P0/P0a labels, not
human gold (docs/DECISIONS.md D007). `fidelity` is the teacher-agreement diagnostic, not the
H6 claim -- exact-match accuracy against `teacher_labels`, nothing more elaborate.
"""

from __future__ import annotations

import numpy as np
import pytest

from tests.fixtures import make_judge_response
from vernier.distil.linear_probe import LinearProbe, fidelity


def test_fit_then_predict_recovers_near_perfect_accuracy_on_easy_synthetic_data() -> None:
    # Three well-separated 1D clusters, one per hand-count class -- trivially linearly separable.
    features = np.array(
        [[x] for x in (-5, -4, -3, -2, 5, 6, 7, 8, 15, 16, 17, 18)], dtype=float
    )
    hands_visible = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    judge_labels = [make_judge_response(hands_visible=hv) for hv in hands_visible]

    probe = LinearProbe()
    probe.fit(features, judge_labels)
    predictions = probe.predict(features)

    accuracy = sum(1 for p, y in zip(predictions, hands_visible) if p == y) / len(hands_visible)
    assert accuracy == 1.0


def test_fit_drops_non_ok_labels_and_their_paired_feature_row() -> None:
    # class 0 cluster at x in {-5,-4,-3}; class 1 cluster at x in {2,3,4,5}.
    # A `refused` response sits at x=-3.5, deep inside the class-0 cluster, positioned BEFORE
    # the class-1 rows. If `fit` filtered `judge_labels` but forgot to drop the paired feature
    # row (e.g. zipping the filtered label list against the unfiltered feature array
    # positionally), this row would silently get relabelled with a class-1 target -- planting
    # a class-1-labelled point inside class 0's territory and dragging the decision boundary
    # into the wrong place.
    features = np.array([[-5.0], [-4.0], [-3.0], [-3.5], [2.0], [3.0], [4.0], [5.0]])
    judge_labels = [
        make_judge_response(hands_visible=0),
        make_judge_response(hands_visible=0),
        make_judge_response(hands_visible=0),
        make_judge_response(status="refused"),
        make_judge_response(hands_visible=1),
        make_judge_response(hands_visible=1),
        make_judge_response(hands_visible=1),
        make_judge_response(hands_visible=1),
    ]

    probe = LinearProbe()
    probe.fit(features, judge_labels)

    # A point deep in class-0 territory must still predict class 0 -- it would flip toward
    # class 1 under the misalignment bug described above.
    assert probe.predict(np.array([[-3.5]])) == [0]
    # And the clean, correctly-labelled points must all still be recovered perfectly.
    clean_features = np.array([[-5.0], [-4.0], [-3.0], [2.0], [3.0], [4.0], [5.0]])
    clean_labels = [0, 0, 0, 1, 1, 1, 1]
    predictions = probe.predict(clean_features)
    assert predictions == clean_labels


def test_predict_before_fit_raises() -> None:
    probe = LinearProbe()
    with pytest.raises(RuntimeError):
        probe.predict(np.array([[0.0]]))


def test_predict_proba_before_fit_raises() -> None:
    probe = LinearProbe()
    with pytest.raises(RuntimeError):
        probe.predict_proba(np.array([[0.0]]))


def test_predict_proba_is_high_for_a_point_deep_in_its_own_cluster() -> None:
    features = np.array([[x] for x in (-5, -4, -3, -2, 5, 6, 7, 8, 15, 16, 17, 18)], dtype=float)
    hands_visible = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    judge_labels = [make_judge_response(hands_visible=hv) for hv in hands_visible]

    probe = LinearProbe()
    probe.fit(features, judge_labels)

    # Deep inside class 0's own cluster, far from any decision boundary -- confidence must be
    # high (this is the AbstentionCascade's real confidence_fn source, D061).
    [confidence] = probe.predict_proba(np.array([[-5.0]]))
    assert confidence > 0.9


def test_predict_proba_returns_one_value_per_row() -> None:
    features = np.array([[x] for x in (-5, -4, -3, -2, 5, 6, 7, 8, 15, 16, 17, 18)], dtype=float)
    hands_visible = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    judge_labels = [make_judge_response(hands_visible=hv) for hv in hands_visible]

    probe = LinearProbe()
    probe.fit(features, judge_labels)

    confidences = probe.predict_proba(features)
    assert len(confidences) == len(features)
    assert all(0.0 <= c <= 1.0 for c in confidences)


def test_fidelity_is_one_when_probe_matches_teacher_on_every_row() -> None:
    features = np.array([[x] for x in (-5, -4, -3, -2, 5, 6, 7, 8, 15, 16, 17, 18)], dtype=float)
    hands_visible = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    judge_labels = [make_judge_response(hands_visible=hv) for hv in hands_visible]

    probe = LinearProbe()
    probe.fit(features, judge_labels)

    teacher_labels = [make_judge_response(hands_visible=hv) for hv in probe.predict(features)]
    assert fidelity(probe, features, teacher_labels) == 1.0


def test_fidelity_is_zero_when_teacher_disagrees_on_every_row() -> None:
    features = np.array([[x] for x in (-5, -4, -3, -2, 5, 6, 7, 8, 15, 16, 17, 18)], dtype=float)
    hands_visible = [0, 0, 0, 0, 1, 1, 1, 1, 2, 2, 2, 2]
    judge_labels = [make_judge_response(hands_visible=hv) for hv in hands_visible]

    probe = LinearProbe()
    probe.fit(features, judge_labels)

    predictions = probe.predict(features)
    # Rotate every predicted class by one (mod 3): with exactly 3 distinct classes this is
    # guaranteed to disagree with the prediction on every single row.
    teacher_labels = [make_judge_response(hands_visible=(p + 1) % 3) for p in predictions]
    assert fidelity(probe, features, teacher_labels) == 0.0
