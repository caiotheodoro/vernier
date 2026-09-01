"""Behavioural tests for `ClaudeJudge.judge_frame`/`judge_rev`.

`_call_claude` (the Wave 2 seam: real Anthropic API call) is monkeypatched with synthetic
`(raw_response_text, latency_ms, cost_usd)` triples -- this unit does not touch a live API.
`judge_frame` calls `_call_claude` twice per frame (once per task), so monkeypatches use a
`side_effect` list to hand back one triple per call.
"""

from __future__ import annotations

from typing import Iterator

import pytest

from vernier.judges.claude import ClaudeJudge
from vernier.models import Confidence, FrameRef


def _frame() -> FrameRef:
    return FrameRef(
        frame_id="ego10k/f0051/w00243/v0007/000418",
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


def _patch_calls(monkeypatch: pytest.MonkeyPatch, responses: list[tuple[str, int, float]]) -> None:
    calls = iter(responses)

    def fake_call(self: ClaudeJudge, frame: FrameRef, prompt_text: str) -> tuple[str, int, float]:
        return next(calls)

    monkeypatch.setattr(ClaudeJudge, "_call_claude", fake_call)


# --- judge_rev ------------------------------------------------------------------------------


def test_judge_rev_returns_placeholder_sentinel() -> None:
    judge = ClaudeJudge()
    rev = judge.judge_rev()
    assert isinstance(rev, str)
    assert rev  # non-empty


# --- judge_frame: both tasks ok --------------------------------------------------------------


def test_both_tasks_ok_combines_to_ok_with_both_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 2}', 100, 0.01),
            ('{"answer": "yes"}', 150, 0.02),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "ok"
    assert result.hands_visible == 2
    assert result.manipulation is True
    assert result.latency_ms == 250
    assert result.cost_usd == pytest.approx(0.03)
    assert result.judge == "claude"
    assert result.frame_id == _frame().frame_id
    assert result.prompt_variant == "P0a"


def test_both_tasks_ok_confidence_none_kind_under_p0a(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 0}', 100, 0.01),
            ('{"answer": "no"}', 100, 0.01),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="none", value=None)


# --- judge_frame: one task fails --------------------------------------------------------------


def test_hand_count_ok_manipulation_refused_combines_to_refused_both_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.01),
            ("I'm sorry, I cannot help with that.", 100, 0.01),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "refused"
    assert result.hands_visible is None
    assert result.manipulation is None
    assert result.latency_ms == 200
    assert result.cost_usd == pytest.approx(0.02)


def test_hand_count_unparseable_manipulation_ok_combines_to_unparseable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ("not json at all", 100, 0.01),
            ('{"answer": "yes"}', 100, 0.01),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "unparseable"
    assert result.hands_visible is None
    assert result.manipulation is None


def test_worse_status_wins_error_beats_refused() -> None:
    # Severity order documented on ClaudeJudge._combine_status: error > timeout > refused >
    # unparseable > ok. Exercised directly since _call_claude never itself returns
    # "error"/"timeout" (those are Wave 2 exception-handling concerns, not parse outcomes).
    from vernier.judges.claude import _combine_status

    assert _combine_status("error", "refused") == "error"
    assert _combine_status("refused", "error") == "error"
    assert _combine_status("timeout", "refused") == "timeout"
    assert _combine_status("refused", "unparseable") == "refused"
    assert _combine_status("unparseable", "ok") == "unparseable"
    assert _combine_status("ok", "ok") == "ok"


# --- judge_frame: P7 confidence ---------------------------------------------------------------


def test_p7_confidence_uses_hand_count_calls_value(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1, "confidence": 0.42}', 100, 0.01),
            ('{"answer": "yes", "confidence": 0.99}', 100, 0.01),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P7")
    assert result.confidence == Confidence(kind="verbalized", value=0.42)


# --- judge_frame: never raises -----------------------------------------------------------------


def test_judge_frame_never_raises_on_garbage_input(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ("\x00\x01 garbage bytes not even text", 5, 0.0),
            ("", 5, 0.0),
        ],
    )
    judge = ClaudeJudge()
    result = judge.judge_frame(_frame(), "P0b")
    assert result.status in ("unparseable", "refused", "error", "timeout")
    assert result.hands_visible is None
    assert result.manipulation is None
