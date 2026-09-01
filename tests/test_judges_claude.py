"""Behavioural tests for `ClaudeJudge.judge_frame`/`judge_rev`/`_call_claude`.

Most tests here monkeypatch `_call_claude` itself with synthetic `(raw_response_text,
latency_ms, cost_usd)` triples -- `judge_frame` calls it twice per frame (once per task), so
monkeypatches use a `side_effect`-style iterator to hand back one triple per call. The tests
near the bottom instead exercise `_call_claude`'s own real `anthropic` SDK wiring by mocking at
the client boundary and constructing actual `anthropic.types.Message` instances -- no live API
call is made or possible without an `ANTHROPIC_API_KEY`, but the request/response shape is
checked against the real, installed SDK's own types. `_image_bytes_for` (resolving a `FrameRef`
to real image bytes) is the one seam still unwired, pending the evaluation-parquet adapter.
"""

from __future__ import annotations

import anthropic
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


# --- _image_bytes_for is the one seam still unwired (needs the evaluation-parquet adapter) -


def test_image_bytes_for_seam_unwired_raises_not_implemented() -> None:
    judge = ClaudeJudge()
    with pytest.raises(NotImplementedError):
        judge._image_bytes_for(_frame())


def test_call_claude_propagates_the_unwired_image_seam() -> None:
    judge = ClaudeJudge()
    with pytest.raises(NotImplementedError, match="_image_bytes_for"):
        judge._call_claude(_frame(), "some prompt text")


# --- _call_claude: real SDK wiring, mocked at the client boundary --------------------------
#
# These construct actual `anthropic.types.Message` instances (the real SDK's own response
# type) so a mismatch between this test's assumptions and the real SDK's shape would surface as
# a pydantic validation error in the fixture itself, not a false-positive passing test.


def _fake_message(
    text: str, *, input_tokens: int, output_tokens: int, model: str = "claude-sonnet-5"
) -> anthropic.types.Message:
    return anthropic.types.Message(
        id="msg_test",
        type="message",
        role="assistant",
        model=model,
        content=[anthropic.types.TextBlock(type="text", text=text)],
        stop_reason="end_turn",
        stop_sequence=None,
        usage=anthropic.types.Usage(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def test_call_claude_extracts_text_latency_and_cost_from_a_real_response_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    judge = ClaudeJudge()
    monkeypatch.setattr(judge, "_image_bytes_for", lambda frame: b"\xff\xd8\xff fake jpeg")
    message = _fake_message('{"hand_count": 2}', input_tokens=900, output_tokens=12)

    class _FakeMessages:
        def create(self, **kwargs: object) -> anthropic.types.Message:
            assert kwargs["model"] == "claude-sonnet-5"
            return message

    monkeypatch.setattr(judge, "_client", type("FakeClient", (), {"messages": _FakeMessages()})())

    raw, latency_ms, cost_usd = judge._call_claude(_frame(), "count the hands")

    assert raw == '{"hand_count": 2}'
    assert latency_ms >= 0
    assert cost_usd == pytest.approx(900 * 2.00 / 1_000_000 + 12 * 10.00 / 1_000_000)


def test_call_claude_updates_judge_rev_from_the_real_response(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = ClaudeJudge()
    monkeypatch.setattr(judge, "_image_bytes_for", lambda frame: b"\xff\xd8\xff fake jpeg")
    message = _fake_message('{"answer": "yes"}', input_tokens=500, output_tokens=5)

    class _FakeMessages:
        def create(self, **kwargs: object) -> anthropic.types.Message:
            return message

    monkeypatch.setattr(judge, "_client", type("FakeClient", (), {"messages": _FakeMessages()})())

    assert judge.judge_rev() != "claude-sonnet-5"  # unresolved before any call, per the sentinel
    judge._call_claude(_frame(), "did they touch it")
    assert judge.judge_rev() == "claude-sonnet-5"
