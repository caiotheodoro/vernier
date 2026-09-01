from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from vernier.labels.store import DuplicateLabelError, HumanLabelStore
from vernier.models import HumanLabel, PassType


def _label(
    frame_id: str = "ego10k/f0051/w00243/v0007/000418",
    rater: str = "R1",
    pass_: PassType = "primary",
    seconds_spent: int = 22,
) -> HumanLabel:
    return HumanLabel.model_validate(
        {
            "frame_id": frame_id,
            "rater": rater,
            "pass": pass_,
            "rubric_rev": "1.0.0",
            "hands_visible": 2,
            "manipulation": True,
            "edge_case": (),
            "difficulty": "hard",
            "note": "left hand behind workpiece, thumb visible",
            "labelled_at": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "seconds_spent": seconds_spent,
        }
    )


def test_fresh_store_has_no_labels(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    assert store.read_pass("primary") == []
    assert store.read_pass("retest") == []
    assert store.has_label("ego10k/f0051/w00243/v0007/000418", "primary") is False
    assert store.has_label("ego10k/f0051/w00243/v0007/000418", "retest") is False


def test_write_then_read_pass_round_trips(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    label = _label()
    store.write(label)
    assert store.read_pass("primary") == [label]


def test_write_duplicate_frame_rater_pass_raises(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    store.write(_label())
    with pytest.raises(DuplicateLabelError):
        store.write(_label(seconds_spent=99))


def test_has_label_reflects_reality_before_and_after_write(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    frame_id = "ego10k/f0051/w00243/v0007/000418"
    assert store.has_label(frame_id, "primary") is False
    store.write(_label(frame_id=frame_id))
    assert store.has_label(frame_id, "primary") is True


def test_primary_and_retest_passes_are_independent(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    frame_id = "ego10k/f0051/w00243/v0007/000418"
    store.write(_label(frame_id=frame_id, pass_="primary"))
    assert store.has_label(frame_id, "retest") is False
    assert store.read_pass("retest") == []
    assert len(store.read_pass("primary")) == 1

    store.write(_label(frame_id=frame_id, pass_="retest"))
    assert store.has_label(frame_id, "retest") is True
    assert len(store.read_pass("retest")) == 1
    assert len(store.read_pass("primary")) == 1


def test_write_same_frame_different_pass_does_not_raise(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    frame_id = "ego10k/f0051/w00243/v0007/000418"
    store.write(_label(frame_id=frame_id, pass_="primary"))
    store.write(_label(frame_id=frame_id, pass_="retest"))
    assert store.has_label(frame_id, "primary") is True
    assert store.has_label(frame_id, "retest") is True


def test_multiple_labels_written_in_order(tmp_path: Path) -> None:
    store = HumanLabelStore(tmp_path / "R1")
    first = _label(frame_id="a")
    second = _label(frame_id="b")
    store.write(first)
    store.write(second)
    assert store.read_pass("primary") == [first, second]


def test_init_creates_path_if_missing(tmp_path: Path) -> None:
    path = tmp_path / "R1" / "nested"
    assert not path.exists()
    HumanLabelStore(path)
    assert path.is_dir()
