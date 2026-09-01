"""Behavioural tests for `GeminiJudge.judge_frame`/`judge_rev`.

Wave 1 is offline: no real Gemini call happens. `_call_gemini` is the seam Wave 2 wires to the
live API; here it is monkeypatched to return synthetic `(raw_text, latency_ms, cost_usd)`
tuples so these tests exercise only the merge/parse/status logic this file owns.

Resolution of the one-call-per-task-vs-both-fields ambiguity (see task brief): `models.py`'s
`JudgeResponse._hands_visible_and_manipulation_null_iff_unparseable_or_worse` validator requires
BOTH `hands_visible` and `manipulation` non-null when `status == "ok"`, and BOTH null otherwise
-- a response with exactly one of the two populated is illegal at any status. Since
`judges.prompts.load_prompt` only ever returns one task's prompt per call, `judge_frame` calls
the `_call_gemini` seam twice (once per task) and merges the two parses into a single
`JudgeResponse`, matching `CONTRACTS.md`'s `JudgeResponse` example, which shows both fields set
from what is presented as one logical judge call.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from tests.fixtures import make_frame_ref
from vernier.judges.gemini import GeminiJudge
from vernier.models import Confidence

FRAME = make_frame_ref()


def _mock_call_gemini(responses: dict[str, tuple[str, int, float]]) -> object:
    """Return a stand-in for `_call_gemini` that returns the hand_count synthetic response on
    the first call and the manipulation one on the second -- `judge_frame` is expected to call
    the seam once per task, hand_count first, matching `load_prompt`'s task order below."""
    calls: list[str] = []

    def fake(self: GeminiJudge, frame: object, prompt_text: str) -> tuple[str, int, float]:
        order = ("hand_count", "manipulation")
        task = order[len(calls)]
        calls.append(task)
        return responses[task]

    return fake


# --- judge_rev ---------------------------------------------------------------------------


def test_judge_rev_returns_placeholder_sentinel_without_raising() -> None:
    judge = GeminiJudge()
    rev = judge.judge_rev()
    assert isinstance(rev, str)
    assert rev  # non-empty
    assert "wave" in rev.lower() or "unresolved" in rev.lower()


# --- judge_frame: both tasks ok ----------------------------------------------------------


def test_judge_frame_merges_both_tasks_when_both_ok() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ('{"hand_count": 2}', 100, 0.0001),
        "manipulation": ('{"answer": "yes"}', 150, 0.0002),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "ok"
    assert result.hands_visible == 2
    assert result.manipulation is True
    assert result.confidence == Confidence(kind="none", value=None)
    assert result.latency_ms == 250
    assert result.cost_usd == pytest.approx(0.0003)
    assert result.judge == "gemini-2.5-flash"
    assert result.prompt_variant == "P0b"
    assert result.frame_id == FRAME.frame_id


def test_judge_frame_hand_count_zero_is_ok() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ('{"hand_count": 0}', 90, 0.0001),
        "manipulation": ('{"answer": "no"}', 90, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "ok"
    assert result.hands_visible == 0
    assert result.manipulation is False


# --- judge_frame: refusal ------------------------------------------------------------------


def test_judge_frame_refusal_on_hand_count_yields_refused_status_and_null_fields() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ("I'm sorry, but I cannot analyze this image.", 80, 0.0001),
        "manipulation": ('{"answer": "yes"}', 80, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "refused"
    assert result.hands_visible is None
    assert result.manipulation is None


# --- judge_frame: unparseable ---------------------------------------------------------------


def test_judge_frame_unparseable_manipulation_yields_unparseable_status_and_null_fields() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ('{"hand_count": 1}', 80, 0.0001),
        "manipulation": ('{"answer": "maybe"}', 80, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "unparseable"
    assert result.hands_visible is None
    assert result.manipulation is None


def test_judge_frame_garbage_text_never_raises() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ("the image shows a workbench", 80, 0.0001),
        "manipulation": ("gibberish nonsense text", 80, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "unparseable"
    assert result.hands_visible is None
    assert result.manipulation is None


# --- judge_frame: refused takes precedence over unparseable when mixed ---------------------


def test_judge_frame_refused_beats_unparseable_when_mixed() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ("garbled text, no json, no refusal marker", 80, 0.0001),
        "manipulation": ("I cannot help with that request.", 80, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P0b")

    assert result.status == "refused"
    assert result.hands_visible is None
    assert result.manipulation is None


# --- judge_frame: P7 verbalized confidence --------------------------------------------------


def test_judge_frame_p7_attaches_verbalized_confidence() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ('{"hand_count": 1, "confidence": 0.75}', 100, 0.0001),
        "manipulation": ('{"answer": "no", "confidence": 0.4}', 100, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P7")

    assert result.status == "ok"
    assert result.confidence.kind == "verbalized"
    assert result.confidence.value == pytest.approx(0.75)


def test_judge_frame_p7_no_confidence_field_falls_back_to_none_kind() -> None:
    judge = GeminiJudge()
    responses = {
        "hand_count": ('{"hand_count": 1}', 100, 0.0001),
        "manipulation": ('{"answer": "no"}', 100, 0.0001),
    }
    with patch.object(GeminiJudge, "_call_gemini", _mock_call_gemini(responses)):
        result = judge.judge_frame(FRAME, "P7")

    assert result.confidence == Confidence(kind="none", value=None)


# --- judge attribute -------------------------------------------------------------------------


def test_judge_class_attribute_is_frozen_model_name() -> None:
    assert GeminiJudge.judge == "gemini-2.5-flash"


# --- _call_gemini seam raises NotImplementedError until Wave 2 -----------------------------


def test_call_gemini_seam_unwired_raises_not_implemented() -> None:
    judge = GeminiJudge()
    with pytest.raises(NotImplementedError):
        judge._call_gemini(FRAME, "some prompt text")
