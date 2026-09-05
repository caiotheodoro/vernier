"""Tests for `scripts/review_labels_cli.py`.

The two properties that make a targeted review worth running are the two tested here: the set
is salted with controls and stays salted over any prefix, and the labelling path never sees a
judge answer. Everything else is bookkeeping.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import review_labels_cli as cli  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture()
def planned(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """A real plan, from the real primary labels and the real judge output, into a tmp store."""
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    (tmp_path / "caio").mkdir()
    (tmp_path / "caio" / "primary.json").write_text(
        (_ROOT / "data" / "labels" / "caio" / "primary.json").read_text()
    )
    assert cli.plan("caio", 1.0, force=False) == 0
    payload: dict[str, Any] = json.loads((tmp_path / "caio" / "review_set.json").read_text())
    return payload


def test_the_disagreement_arm_is_exactly_the_frames_the_rater_and_judge_differ_on(
    planned: dict[str, Any],
) -> None:
    primary = {
        r["frame_id"]: r
        for r in json.loads((_ROOT / "data" / "labels" / "caio" / "primary.json").read_text())
    }
    judged = cli._judge_answers()
    expected = {
        fid
        for fid, label in primary.items()
        if fid in judged
        and (
            (judged[fid][0] is not None and judged[fid][0] != label["hands_visible"])
            or (judged[fid][1] is not None and judged[fid][1] != label["manipulation"])
        )
    }
    got = {f["frame_id"] for f in planned["frames"] if f["arm"] == "disagreement"}
    assert got == expected
    # D085: 60 more primary labels means more rater/judge disagreements. The count is a
    # tripwire, so it moves deliberately rather than drifting.
    assert len(expected) == 24


def test_the_set_is_salted_and_stays_salted_over_every_prefix(planned: dict[str, Any]) -> None:
    """A sitting that is almost all one arm is the tell the controls exist to remove, so it is
    not enough for the whole set to be balanced -- every prefix must be."""
    arms = [f["arm"] for f in planned["frames"]]
    assert arms.count("control") == arms.count("disagreement") == 24
    for n in range(2, len(arms) + 1):
        seen = arms[:n].count("disagreement")
        assert abs(seen - n / 2) <= 1.5, f"prefix of {n} is {seen} disagreements, too lopsided"


def test_the_written_set_carries_no_judge_answer(planned: dict[str, Any]) -> None:
    """`label` reads this file and nothing else, so anything leaked here reaches the rater."""
    for entry in planned["frames"]:
        assert set(entry) == {"frame_id", "arm"}
    blob = json.dumps(planned)
    for leaked in ("hands_visible", "manipulation", "judge", "confidence", "raw"):
        assert leaked not in blob


def test_plan_is_deterministic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]) -> None:
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    assert cli.plan("caio", 1.0, force=True) == 0
    again = json.loads((tmp_path / "caio" / "review_set.json").read_text())
    assert again == planned


def test_plan_refuses_to_rewrite_a_set_mid_review(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]
) -> None:
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    assert cli.plan("caio", 1.0, force=False) == 1


def test_labelling_never_reads_judge_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]
) -> None:
    """Point the judge directory at nothing and label a frame anyway. If the labelling path
    ever grows a read of judge output, this fails."""
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    monkeypatch.setattr(cli, "_GOLD_JUDGED_ROOT", tmp_path / "no-such-dir")
    monkeypatch.setattr(cli, "_show_frame", lambda _: None)
    monkeypatch.setattr(cli, "image_bytes_for", lambda _: b"")
    answers = iter(["2", "y", "", "easy", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))

    assert cli.label("caio", stop_after=1) == 0
    written = json.loads((tmp_path / "caio" / "review.json").read_text())
    assert len(written) == 1
    assert written[0]["pass"] == "review"
    assert written[0]["hands_visible"] == 2 and written[0]["manipulation"] is True


def test_the_review_pass_never_touches_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]
) -> None:
    before = (tmp_path / "caio" / "primary.json").read_text()
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    monkeypatch.setattr(cli, "_show_frame", lambda _: None)
    monkeypatch.setattr(cli, "image_bytes_for", lambda _: b"")
    answers = iter(["1", "n", "", "medium", ""])
    monkeypatch.setattr("builtins.input", lambda *_: next(answers))
    cli.label("caio", stop_after=1)
    assert (tmp_path / "caio" / "primary.json").read_text() == before


def test_a_salt_changes_the_draw_and_is_recorded_in_the_written_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]
) -> None:
    """D077: the seed is a constant, so without a salt a re-plan reproduces the same set in the
    same order -- which is useless when a pass has to be attempted a second time."""
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    assert cli.plan("caio", 1.0, force=True, salt="D077-rerun") == 0
    salted: dict[str, Any] = json.loads((tmp_path / "caio" / "review_set.json").read_text())

    assert salted["salt"] == "D077-rerun"
    assert planned.get("salt", "") == ""
    assert [f["frame_id"] for f in salted["frames"]] != [f["frame_id"] for f in planned["frames"]]
    # same frames, same arms -- only the order and control choice are re-randomised
    assert {f["frame_id"] for f in salted["frames"] if f["arm"] == "disagreement"} == {
        f["frame_id"] for f in planned["frames"] if f["arm"] == "disagreement"
    }


def test_the_salted_set_is_still_interleaved_over_every_prefix(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, planned: dict[str, Any]
) -> None:
    monkeypatch.setattr(cli, "_LABEL_STORE_ROOT", tmp_path)
    assert cli.plan("caio", 1.0, force=True, salt="D077-rerun") == 0
    frames = json.loads((tmp_path / "caio" / "review_set.json").read_text())["frames"]
    seen = {"disagreement": 0, "control": 0}
    for i, frame in enumerate(frames, start=1):
        seen[frame["arm"]] += 1
        assert abs(seen["disagreement"] - seen["control"]) <= 2, f"prefix of {i} is lopsided"
