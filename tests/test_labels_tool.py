"""Behavioural tests for `next_frame`/`record_label`.

`_pending_frames` is monkeypatched with synthetic in-memory `FrameRef` pools for `next_frame`'s
own tests -- those only exercise the random-order/pool-shrinking logic. `_pending_frames`
itself (real sample membership + `HumanLabelStore.has_label`) has its own tests further down,
against a real `write_membership`'d `tmp_path` and a real `HumanLabelStore`, not mocks --
`sampling/draw.py`'s D045 was a wiring bug that only mocked tests, none of which checked a real
`path` argument, let through.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from vernier.labels import tool as tool_mod
from vernier.labels.tool import next_frame, record_label
from vernier.models import FrameRef, HumanLabel


def _frame(uid: str) -> FrameRef:
    return FrameRef(
        frame_id=f"ego10k/f0051/w00243/v0007/{uid}",
        corpus="egocentric-10k",
        corpus_rev="deadbeef",
        factory_id="0051",
        worker_id="00243",
        clip_id="0007",
        frame_index=1,
        timestamp_s=1.0,
        width=1920,
        height=1080,
        fps=30.0,
        codec="hevc",
        sample="S10k-U",
        stratum="unstratified",
        why_no_provenance=None,
    )


# --- record_label ---------------------------------------------------------------------------


def test_record_label_builds_matching_human_label() -> None:
    frame = _frame("000418")
    result = record_label(
        frame=frame,
        rater="R1",
        pass_="primary",
        rubric_rev="1.2.0",
        hands_visible=2,
        manipulation=True,
        edge_case=["glove", "tool-occlusion"],
        difficulty="hard",
        note="left hand behind workpiece, thumb visible",
        seconds_spent=22,
    )

    assert isinstance(result, HumanLabel)
    assert result.frame_id == frame.frame_id
    assert result.rater == "R1"
    assert result.pass_ == "primary"
    assert result.rubric_rev == "1.2.0"
    assert result.hands_visible == 2
    assert result.manipulation is True
    assert result.edge_case == ("glove", "tool-occlusion")
    assert result.difficulty == "hard"
    assert result.note == "left hand behind workpiece, thumb visible"
    assert result.seconds_spent == 22


def test_record_label_rejects_invalid_edge_case_tag() -> None:
    frame = _frame("000419")
    with pytest.raises(ValidationError):
        record_label(
            frame=frame,
            rater="R1",
            pass_="primary",
            rubric_rev="1.2.0",
            hands_visible=2,
            manipulation=True,
            edge_case=["not-a-real-tag"],  # type: ignore[list-item]
            difficulty="easy",
            note="",
            seconds_spent=5,
        )


def test_record_label_rejects_out_of_range_hands_visible() -> None:
    frame = _frame("000420")
    with pytest.raises(ValidationError):
        record_label(
            frame=frame,
            rater="R1",
            pass_="primary",
            rubric_rev="1.2.0",
            hands_visible=3,
            manipulation=False,
            edge_case=[],
            difficulty="easy",
            note="",
            seconds_spent=5,
        )


# --- next_frame -------------------------------------------------------------------------


def test_next_frame_returns_one_of_the_pending_pool(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [_frame("000001"), _frame("000002"), _frame("000003")]
    monkeypatch.setattr(tool_mod, "_pending_frames", lambda pass_, rater: pool)

    picked = next_frame(pass_="primary", rater="R1")

    assert picked is not None
    assert picked in pool


def test_next_frame_returns_none_when_pool_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tool_mod, "_pending_frames", lambda pass_, rater: [])

    assert next_frame(pass_="primary", rater="R1") is None


def test_next_frame_returns_none_once_pool_exhausted_across_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remaining = [_frame("000001"), _frame("000002"), _frame("000003")]

    def _shrinking_pool(pass_: str, rater: str) -> list[FrameRef]:
        return remaining

    monkeypatch.setattr(tool_mod, "_pending_frames", _shrinking_pool)

    seen = []
    while True:
        picked = next_frame(pass_="primary", rater="R1")
        if picked is None:
            break
        seen.append(picked)
        remaining.remove(picked)
        assert len(seen) <= 3, "must terminate once pool is exhausted"

    assert len(seen) == 3
    assert {f.frame_id for f in seen} == {f.frame_id for f in [_frame("000001"), _frame("000002"), _frame("000003")]}


def test_next_frame_deterministic_for_same_rater_pass_seed(monkeypatch: pytest.MonkeyPatch) -> None:
    pool = [_frame("000001"), _frame("000002"), _frame("000003"), _frame("000004")]
    monkeypatch.setattr(tool_mod, "_pending_frames", lambda pass_, rater: pool)

    first = next_frame(pass_="primary", rater="R1")
    second = next_frame(pass_="primary", rater="R1")

    assert first is not None
    assert second is not None
    assert first.frame_id == second.frame_id


# --- import hygiene -----------------------------------------------------------------------


def test_tool_module_never_imports_vernier_judges() -> None:
    assert tool_mod.__file__ is not None
    import_lines = [
        line
        for line in Path(tool_mod.__file__).read_text().splitlines()
        if line.startswith("import ") or line.startswith("from ")
    ]
    assert not any("judges" in line for line in import_lines)


# --- _pending_frames: real membership + real HumanLabelStore, no mocks ----------------------


def _eval_frame(sample: str, uid: str) -> FrameRef:
    return FrameRef(
        frame_id=f"uuid-{sample}-{uid}",
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


def test_pending_frames_primary_pass_pools_all_three_g200_sets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vernier.sampling.membership import write_membership

    monkeypatch.setattr(tool_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(tool_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")

    write_membership("G200-ego", [_eval_frame("G200-ego", "0")], tmp_path / "membership")
    write_membership("G200-ego4d", [_eval_frame("G200-ego4d", "0")], tmp_path / "membership")
    write_membership("G200-epic", [_eval_frame("G200-epic", "0")], tmp_path / "membership")
    write_membership("R100", [_eval_frame("R100", "0")], tmp_path / "membership")

    pending = tool_mod._pending_frames("primary", rater="R1")

    assert {f.frame_id for f in pending} == {
        "uuid-G200-ego-0",
        "uuid-G200-ego4d-0",
        "uuid-G200-epic-0",
    }


def test_pending_frames_retest_pass_pools_only_r100(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vernier.sampling.membership import write_membership

    monkeypatch.setattr(tool_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(tool_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")

    write_membership("G200-ego", [_eval_frame("G200-ego", "0")], tmp_path / "membership")
    write_membership("R100", [_eval_frame("R100", "0")], tmp_path / "membership")

    pending = tool_mod._pending_frames("retest", rater="R1")

    assert {f.frame_id for f in pending} == {"uuid-R100-0"}


def test_pending_frames_excludes_already_labelled_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vernier.sampling.membership import write_membership

    monkeypatch.setattr(tool_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(tool_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")

    write_membership(
        "G200-ego",
        [_eval_frame("G200-ego", "0"), _eval_frame("G200-ego", "1")],
        tmp_path / "membership",
    )
    write_membership("G200-ego4d", [], tmp_path / "membership")
    write_membership("G200-epic", [], tmp_path / "membership")

    label = record_label(
        frame=_eval_frame("G200-ego", "0"),
        rater="R1",
        pass_="primary",
        rubric_rev="1.2.0",
        hands_visible=1,
        manipulation=False,
        edge_case=[],
        difficulty="easy",
        note="",
        seconds_spent=10,
    )
    tool_mod._label_store("R1").write(label)

    pending = tool_mod._pending_frames("primary", rater="R1")

    assert {f.frame_id for f in pending} == {"uuid-G200-ego-1"}


def test_pending_frames_scopes_labels_by_rater(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from vernier.sampling.membership import write_membership

    monkeypatch.setattr(tool_mod, "_MEMBERSHIP_ROOT", tmp_path / "membership")
    monkeypatch.setattr(tool_mod, "_LABEL_STORE_ROOT", tmp_path / "labels")

    write_membership("G200-ego", [_eval_frame("G200-ego", "0")], tmp_path / "membership")
    write_membership("G200-ego4d", [], tmp_path / "membership")
    write_membership("G200-epic", [], tmp_path / "membership")

    label = record_label(
        frame=_eval_frame("G200-ego", "0"),
        rater="R1",
        pass_="primary",
        rubric_rev="1.2.0",
        hands_visible=1,
        manipulation=False,
        edge_case=[],
        difficulty="easy",
        note="",
        seconds_spent=10,
    )
    tool_mod._label_store("R1").write(label)

    # R1's own pool is empty (already labelled); a different rater's pool is untouched -- each
    # rater gets their own HumanLabelStore, per store.py's own "one store per rater" contract.
    assert tool_mod._pending_frames("primary", rater="R1") == []
    assert len(tool_mod._pending_frames("primary", rater="R2")) == 1
