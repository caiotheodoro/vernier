"""Behavioural tests for `scripts/judge_test_retest.py`'s pure aggregation logic.

Same convention as `tests/test_e2_replication.py`: a fake `JudgeAdapter` returns canned
responses per call, in order, never a live server.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from judge_test_retest import _run_retest  # noqa: E402

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.models import Confidence, FrameRef, JudgeResponse


def _frame(uid: str) -> FrameRef:
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
        sample="E10k-ego",
        stratum="unstratified",
        why_no_provenance="test fixture",
    )


def _response(hands_visible: int, manipulation: bool) -> JudgeResponse:
    return JudgeResponse(
        frame_id="ignored",
        judge="fake",
        judge_rev="fake-rev",
        prompt_variant="P0b",
        hands_visible=hands_visible,  # type: ignore[arg-type]
        manipulation=manipulation,
        confidence=Confidence(kind="none", value=None),
        raw="raw",
        status="ok",
        latency_ms=10,
        cost_usd=0.0001,
    )


class _FakeJudge(JudgeAdapter):
    """One canned-response list per frame_id, consumed in call order."""

    judge = "fake"

    def __init__(self, by_frame: dict[str, list[JudgeResponse]]) -> None:
        self._by_frame = {k: iter(v) for k, v in by_frame.items()}

    def judge_rev(self) -> str:
        return "fake-rev"

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        return next(self._by_frame[frame.frame_id])


def test_unanimous_frame_is_flagged_agreement() -> None:
    frame = _frame("f0")
    judge = _FakeJudge({"uuid-f0": [_response(2, True), _response(2, True), _response(2, True)]})

    results = _run_retest([frame], repeats=3, judge=judge)

    assert results[0]["hand_count_unanimous"] is True
    assert results[0]["manipulation_unanimous"] is True
    assert results[0]["hand_counts"] == [2, 2, 2]


def test_disagreeing_frame_is_flagged_not_unanimous() -> None:
    frame = _frame("f1")
    judge = _FakeJudge(
        {"uuid-f1": [_response(2, True), _response(1, True), _response(2, False)]}
    )

    results = _run_retest([frame], repeats=3, judge=judge)

    assert results[0]["hand_count_unanimous"] is False
    assert results[0]["manipulation_unanimous"] is False


def test_calls_judge_frame_repeats_times_per_frame() -> None:
    frame = _frame("f2")
    judge = _FakeJudge({"uuid-f2": [_response(0, False) for _ in range(5)]})

    results = _run_retest([frame], repeats=5, judge=judge)

    assert len(results[0]["hand_counts"]) == 5
    assert len(results[0]["statuses"]) == 5
