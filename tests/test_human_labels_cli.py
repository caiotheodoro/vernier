"""Behavioural tests for `scripts/human_labels_cli.py`.

`_show_frame` (opens an OS image viewer) and `image_bytes_for`/`next_frame` (real sampling/
labels seams, already tested in their own modules) are monkeypatched -- this file tests the
interactive prompt logic and the one-frame labelling flow, against a real `HumanLabelStore`
(no mocks for persistence itself, same convention as `tests/test_labels_tool.py`).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import human_labels_cli as cli_mod  # noqa: E402

from vernier.labels.store import HumanLabelStore
from vernier.models import FrameRef, HumanLabel
from vernier.sampling.membership import write_membership


def _frame(uid: str = "0") -> FrameRef:
    return FrameRef(
        frame_id=f"uuid-{uid}",
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
        sample="G200-ego",
        stratum="unstratified",
        why_no_provenance="test fixture",
    )


def _inputs(monkeypatch: pytest.MonkeyPatch, answers: list[str]) -> None:
    it = iter(answers)
    monkeypatch.setattr("builtins.input", lambda *_args: next(it))


# --- _prompt_int_choice ----------------------------------------------------------------------


def test_prompt_int_choice_accepts_a_valid_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _inputs(monkeypatch, ["1"])
    assert cli_mod._prompt_int_choice("? ", (0, 1, 2)) == 1


def test_prompt_int_choice_retries_on_non_numeric_then_out_of_range(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs(monkeypatch, ["abc", "9", "2"])
    assert cli_mod._prompt_int_choice("? ", (0, 1, 2)) == 2


# --- _prompt_yes_no ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["y", "yes", "Yes", "true"])
def test_prompt_yes_no_true_variants(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    _inputs(monkeypatch, [raw])
    assert cli_mod._prompt_yes_no("? ") is True


@pytest.mark.parametrize("raw", ["n", "no", "No", "false"])
def test_prompt_yes_no_false_variants(monkeypatch: pytest.MonkeyPatch, raw: str) -> None:
    _inputs(monkeypatch, [raw])
    assert cli_mod._prompt_yes_no("? ") is False


def test_prompt_yes_no_retries_on_garbage(monkeypatch: pytest.MonkeyPatch) -> None:
    _inputs(monkeypatch, ["maybe", "y"])
    assert cli_mod._prompt_yes_no("? ") is True


# --- _prompt_edge_case_tags -------------------------------------------------------------------


def test_prompt_edge_case_tags_accepts_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    _inputs(monkeypatch, [""])
    assert cli_mod._prompt_edge_case_tags() == []


def test_prompt_edge_case_tags_accepts_valid_comma_separated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs(monkeypatch, ["glove, dark"])
    assert cli_mod._prompt_edge_case_tags() == ["glove", "dark"]


def test_prompt_edge_case_tags_rejects_tag_outside_closed_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _inputs(monkeypatch, ["not-a-real-tag", "glove"])
    assert cli_mod._prompt_edge_case_tags() == ["glove"]


# --- _label_one_frame: real HumanLabelStore, mocked frame/image/prompts ----------------------


def test_label_one_frame_writes_a_real_human_label(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = _frame()
    monkeypatch.setattr(cli_mod, "next_frame", lambda pass_, rater: frame)
    monkeypatch.setattr(cli_mod, "image_bytes_for", lambda f: b"\xff\xd8\xff fake jpeg")
    monkeypatch.setattr(cli_mod, "_show_frame", lambda image_bytes: None)
    monkeypatch.setattr(cli_mod, "_LABEL_STORE_ROOT", tmp_path)
    _inputs(monkeypatch, ["2", "y", "glove", "easy", "left hand visible"])

    result = cli_mod._label_one_frame("R1", "primary")

    assert result is True
    store = HumanLabelStore(tmp_path / "R1")
    [label] = store.read_pass("primary")
    assert label.frame_id == frame.frame_id
    assert label.hands_visible == 2
    assert label.manipulation is True
    assert label.edge_case == ("glove",)
    assert label.difficulty == "easy"
    assert label.note == "left hand visible"
    assert label.rubric_rev == cli_mod._RUBRIC_REV
    assert label.seconds_spent >= 0


def test_label_one_frame_returns_false_when_pass_complete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_mod, "next_frame", lambda pass_, rater: None)
    assert cli_mod._label_one_frame("R1", "primary") is False


def test_label_one_frame_defaults_difficulty_to_medium_on_blank(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frame = _frame("1")
    monkeypatch.setattr(cli_mod, "next_frame", lambda pass_, rater: frame)
    monkeypatch.setattr(cli_mod, "image_bytes_for", lambda f: b"\xff\xd8\xff fake jpeg")
    monkeypatch.setattr(cli_mod, "_show_frame", lambda image_bytes: None)
    monkeypatch.setattr(cli_mod, "_LABEL_STORE_ROOT", tmp_path)
    _inputs(monkeypatch, ["0", "n", "", "", ""])

    cli_mod._label_one_frame("R1", "primary")

    [label] = HumanLabelStore(tmp_path / "R1").read_pass("primary")
    assert label.difficulty == "medium"
    assert label.note == ""


# --- _scoped_pending_frames / _scoped_next_frame: D057's balanced reduced-target scoping ------


def _frames(sample: str, n: int) -> list[FrameRef]:
    return [
        FrameRef(
            frame_id=f"{sample}-{i}",
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
            sample=sample,
            stratum="unstratified",
            why_no_provenance="test fixture",
        )
        for i in range(n)
    ]


def test_scoped_pending_frames_excludes_already_labelled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(cli_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")
    frames = _frames("G200-ego", 3)
    write_membership("G200-ego", frames, tmp_path / "membership")

    store = HumanLabelStore(tmp_path / "labels" / "R1")
    store.write(
        HumanLabel.model_validate(
            {
                "frame_id": frames[0].frame_id,
                "rater": "R1",
                "pass": "primary",
                "rubric_rev": "1.2.0",
                "hands_visible": 1,
                "manipulation": False,
                "edge_case": [],
                "difficulty": "easy",
                "note": "",
                "labelled_at": "2026-01-01T00:00:00Z",
                "seconds_spent": 5,
            }
        )
    )

    pending = cli_mod._scoped_pending_frames("G200-ego", "primary", "R1")

    assert {f.frame_id for f in pending} == {frames[1].frame_id, frames[2].frame_id}


def test_scoped_next_frame_returns_none_when_sample_exhausted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(cli_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")
    write_membership("G200-ego", [], tmp_path / "membership")

    assert cli_mod._scoped_next_frame("G200-ego", "primary", "R1") is None


def test_scoped_next_frame_is_deterministic_and_scoped_to_its_own_sample(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cli_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(cli_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")
    ego_frames = _frames("G200-ego", 5)
    other_frames = _frames("G200-ego4d", 5)
    write_membership("G200-ego", ego_frames, tmp_path / "membership")
    write_membership("G200-ego4d", other_frames, tmp_path / "membership")

    first = cli_mod._scoped_next_frame("G200-ego", "primary", "R1")
    second = cli_mod._scoped_next_frame("G200-ego", "primary", "R1")

    assert first is not None
    assert second is not None
    assert first.frame_id == second.frame_id  # repeated calls, no label recorded -> same frame
    assert first.sample == "G200-ego"  # never leaks a frame from the other scoped sample


# --- main: loop termination and Ctrl-C handling -----------------------------------------------


def test_main_stops_cleanly_when_pool_exhausted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_mod, "_label_one_frame", lambda rater, pass_, sample: False)

    assert cli_mod.main(["--rater", "R1", "--pass", "primary"]) == 0


def test_main_handles_keyboard_interrupt_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(rater: str, pass_: str, sample: str | None) -> bool:
        raise KeyboardInterrupt

    monkeypatch.setattr(cli_mod, "_label_one_frame", _raise)

    assert cli_mod.main(["--rater", "R1", "--pass", "primary"]) == 0


# --- main: --sample and --stop-after (D057's reduced-target scoping) --------------------------


def test_main_rejects_sample_with_retest_pass() -> None:
    with pytest.raises(SystemExit):
        cli_mod.main(["--rater", "R1", "--pass", "retest", "--sample", "G200-ego"])


def test_main_stops_after_n_labels_regardless_of_pool_remaining(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"n": 0}

    def _always_true(rater: str, pass_: str, sample: str | None) -> bool:
        calls["n"] += 1
        return True

    monkeypatch.setattr(cli_mod, "_label_one_frame", _always_true)

    assert cli_mod.main(["--rater", "R1", "--pass", "primary", "--stop-after", "3"]) == 0
    assert calls["n"] == 3  # the pool never runs out here -- --stop-after must be what stops it


def test_main_passes_sample_through_to_label_one_frame(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str | None] = []

    def _fake(rater: str, pass_: str, sample: str | None) -> bool:
        seen.append(sample)
        return len(seen) < 2

    monkeypatch.setattr(cli_mod, "_label_one_frame", _fake)

    cli_mod.main(["--rater", "R1", "--pass", "primary", "--sample", "G200-ego"])

    assert seen == ["G200-ego", "G200-ego"]
