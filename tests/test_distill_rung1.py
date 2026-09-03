"""Behavioural tests for `scripts/distill_rung1.py`'s pure sampling/splitting logic.

`_extract_features` (real DINOv2 + network calls) is not exercised here -- that seam is
inherently an integration point, verified by actually running the script for real (D061), the
same convention this project already uses for live judge calls.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from distill_rung1 import (  # noqa: E402
    select_training_and_holdout_frame_ids,
    split_gold_for_calibration_and_eval,
)

from vernier.models import FrameRef, HumanLabel


def _frame(frame_id: str) -> FrameRef:
    return FrameRef(
        frame_id=frame_id,
        corpus="egocentric-10k",
        corpus_rev="deadbeef",
        factory_id=None,
        worker_id=None,
        clip_id=None,
        frame_index=0,
        timestamp_s=None,
        width=1920,
        height=1080,
        fps=None,
        codec=None,
        sample="E10k-ego",
        stratum="unstratified",
        why_no_provenance="test fixture",
    )


def _label(frame_id: str) -> HumanLabel:
    return HumanLabel.model_validate(
        {
            "frame_id": frame_id,
            "rater": "R1",
            "pass": "primary",
            "rubric_rev": "1.2.0",
            "hands_visible": 1,
            "manipulation": True,
            "edge_case": [],
            "difficulty": "easy",
            "note": "",
            "labelled_at": "2026-01-01T00:00:00Z",
            "seconds_spent": 5,
        }
    )


# --- select_training_and_holdout_frame_ids -----------------------------------------------------


def test_select_returns_disjoint_train_and_holdout_sets() -> None:
    stored_labels = [{"frame_id": f"f{i}"} for i in range(100)]
    frame_by_id = {f"f{i}": _frame(f"f{i}") for i in range(100)}

    train_ids, holdout_ids = select_training_and_holdout_frame_ids(
        stored_labels, frame_by_id, n_train=60, n_holdout=20
    )

    assert len(train_ids) == 60
    assert len(holdout_ids) == 20
    assert set(train_ids).isdisjoint(holdout_ids)


def test_select_skips_stored_labels_with_no_resolvable_frame() -> None:
    stored_labels = [{"frame_id": f"f{i}"} for i in range(10)]
    # Only half of the stored labels resolve to a real frame -- the rest predate a redraw.
    frame_by_id = {f"f{i}": _frame(f"f{i}") for i in range(5)}

    train_ids, holdout_ids = select_training_and_holdout_frame_ids(
        stored_labels, frame_by_id, n_train=3, n_holdout=2
    )

    assert all(fid in frame_by_id for fid in train_ids + holdout_ids)


def test_select_raises_when_not_enough_resolvable_frames() -> None:
    stored_labels = [{"frame_id": f"f{i}"} for i in range(5)]
    frame_by_id = {f"f{i}": _frame(f"f{i}") for i in range(5)}

    with pytest.raises(ValueError):
        select_training_and_holdout_frame_ids(stored_labels, frame_by_id, n_train=10, n_holdout=10)


def test_select_is_deterministic_given_the_same_seed() -> None:
    stored_labels = [{"frame_id": f"f{i}"} for i in range(50)]
    frame_by_id = {f"f{i}": _frame(f"f{i}") for i in range(50)}

    first = select_training_and_holdout_frame_ids(stored_labels, frame_by_id, n_train=10, n_holdout=5, seed=1)
    second = select_training_and_holdout_frame_ids(stored_labels, frame_by_id, n_train=10, n_holdout=5, seed=1)

    assert first == second


# --- split_gold_for_calibration_and_eval ---------------------------------------------------------


def test_split_gold_is_disjoint_and_covers_everything() -> None:
    gold = [_label(f"g{i}") for i in range(20)]

    calibration, evaluation = split_gold_for_calibration_and_eval(gold)

    calibration_ids = {label.frame_id for label in calibration}
    eval_ids = {label.frame_id for label in evaluation}
    assert calibration_ids.isdisjoint(eval_ids)
    assert calibration_ids | eval_ids == {label.frame_id for label in gold}


def test_split_gold_is_roughly_even() -> None:
    gold = [_label(f"g{i}") for i in range(21)]  # odd count

    calibration, evaluation = split_gold_for_calibration_and_eval(gold)

    assert abs(len(calibration) - len(evaluation)) <= 1


def test_split_gold_is_deterministic_given_the_same_seed() -> None:
    gold = [_label(f"g{i}") for i in range(20)]

    first = split_gold_for_calibration_and_eval(gold, seed=1)
    second = split_gold_for_calibration_and_eval(gold, seed=1)

    assert [label.frame_id for label in first[0]] == [label.frame_id for label in second[0]]
