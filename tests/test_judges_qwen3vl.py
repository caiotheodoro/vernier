"""Behavioural tests for `Qwen3VLJudge.judge_frame`/`judge_rev`.

`_call_qwen3vl` (the Wave 2/4 seam: real local-or-Modal inference call) is monkeypatched with
synthetic `(raw_response_text, latency_ms, cost_usd, token_logprob)` quadruples -- this unit
does not touch live weights. `judge_frame` calls `_call_qwen3vl` twice per frame (once per
task, hand-count then manipulation), so monkeypatches use a `side_effect` list to hand back one
quadruple per call, in that order.

Unlike the closed judges retired in `docs/DECISIONS.md` D042, the seam here can expose a
per-token logprob-derived confidence directly, so `Confidence(kind="logprob", ...)` is built by
this adapter itself, bypassing `base.build_confidence` (which explicitly does not handle
`kind="logprob"` -- see its docstring).
"""

from __future__ import annotations

import pytest

from vernier.judges.qwen3vl import Qwen3VLJudge
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


def _patch_calls(
    monkeypatch: pytest.MonkeyPatch, responses: list[tuple[str, int, float, float | None]]
) -> None:
    calls = iter(responses)

    def fake_call(
        self: Qwen3VLJudge, frame: FrameRef, prompt_text: str
    ) -> tuple[str, int, float, float | None]:
        return next(calls)

    monkeypatch.setattr(Qwen3VLJudge, "_call_qwen3vl", fake_call)


# --- judge_rev --------------------------------------------------------------------------------


def test_judge_rev_returns_placeholder_sentinel() -> None:
    judge = Qwen3VLJudge()
    rev = judge.judge_rev()
    assert isinstance(rev, str)
    assert rev  # non-empty


# --- judge_frame: both tasks ok, logprob present -----------------------------------------------


def test_both_tasks_ok_with_logprob_combines_to_ok_with_logprob_confidence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 2}', 100, 0.0, 0.83),
            ('{"answer": "yes"}', 150, 0.0, 0.91),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "ok"
    assert result.hands_visible == 2
    assert result.manipulation is True
    assert result.latency_ms == 250
    assert result.cost_usd == pytest.approx(0.0)
    assert result.judge == "qwen3-vl"
    assert result.frame_id == _frame().frame_id
    assert result.prompt_variant == "P0a"
    # Confidence sources from the hand-count call's token_logprob (documented convention).
    assert result.confidence == Confidence(kind="logprob", value=0.83)


def test_confidence_round_trips_through_real_pydantic_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression guard: kind="logprob" must actually validate against the real Confidence
    model, not just against a hand-rolled expectation."""
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.0, 0.5),
            ('{"answer": "no"}', 100, 0.0, 0.5),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    # Constructing it again independently must not raise -- proves the adapter's value is a
    # legitimate Confidence(kind="logprob", ...), not something that only survived by accident.
    Confidence(kind=result.confidence.kind, value=result.confidence.value)
    assert result.confidence.kind == "logprob"
    assert result.confidence.value == pytest.approx(0.5)


# --- judge_frame: logprob absent ---------------------------------------------------------------


def test_hand_count_logprob_none_falls_back_to_manipulation_logprob(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.0, None),
            ('{"answer": "yes"}', 100, 0.0, 0.77),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="logprob", value=0.77)


def test_both_logprobs_none_falls_back_to_kind_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.0, None),
            ('{"answer": "yes"}', 100, 0.0, None),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="none", value=None)


def test_logprob_out_of_range_falls_back_to_kind_none_without_raising(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.0, 1.5),
            ('{"answer": "yes"}', 100, 0.0, -0.2),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="none", value=None)


# --- judge_frame: one task fails ----------------------------------------------------------------


def test_hand_count_ok_manipulation_refused_combines_to_refused_both_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ('{"hand_count": 1}', 100, 0.0, 0.6),
            ("I'm sorry, I cannot help with that.", 100, 0.0, None),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "refused"
    assert result.hands_visible is None
    assert result.manipulation is None
    assert result.latency_ms == 200
    assert result.cost_usd == pytest.approx(0.0)


def test_hand_count_unparseable_manipulation_ok_combines_to_unparseable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_calls(
        monkeypatch,
        [
            ("not json at all", 100, 0.0, None),
            ('{"answer": "yes"}', 100, 0.0, 0.5),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")

    assert result.status == "unparseable"
    assert result.hands_visible is None
    assert result.manipulation is None


def test_worse_status_wins_error_beats_refused() -> None:
    # Severity order documented on qwen3vl._combine_status: error > timeout > refused >
    # unparseable > ok.
    from vernier.judges.qwen3vl import _combine_status

    assert _combine_status("error", "refused") == "error"
    assert _combine_status("refused", "error") == "error"
    assert _combine_status("timeout", "refused") == "timeout"
    assert _combine_status("refused", "unparseable") == "refused"
    assert _combine_status("unparseable", "ok") == "unparseable"
    assert _combine_status("ok", "ok") == "ok"


# --- judge_frame: never raises -------------------------------------------------------------------


def test_judge_frame_never_raises_on_garbage_input(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ("\x00\x01 garbage bytes not even text", 5, 0.0, None),
            ("", 5, 0.0, None),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0b")
    assert result.status in ("unparseable", "refused", "error", "timeout")
    assert result.hands_visible is None
    assert result.manipulation is None


def test_judge_frame_never_raises_on_garbage_logprob_type(monkeypatch: pytest.MonkeyPatch) -> None:
    garbage_responses: list[tuple[str, int, float, float | None]] = [
        ('{"hand_count": 1}', 100, 0.0, "not-a-float"),  # type: ignore[list-item]
        ('{"answer": "yes"}', 100, 0.0, None),
    ]
    _patch_calls(monkeypatch, garbage_responses)
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="none", value=None)
