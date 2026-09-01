"""Behavioural tests for `Qwen3VLJudge.judge_frame`/`judge_rev`/`_call_qwen3vl`.

Most tests here monkeypatch `_call_qwen3vl` itself with synthetic `(raw_response_text,
latency_ms, cost_usd, token_logprob)` quadruples, exercising only the merge/parse/status logic
`judge_frame` owns. `judge_frame` calls `_call_qwen3vl` twice per frame (once per task,
hand-count then manipulation), so monkeypatches use a `side_effect`-style iterator to hand back
one quadruple per call, in that order. The tests near the bottom instead exercise
`_call_qwen3vl`'s own real `openai`-client wiring against the self-hosted vLLM server by mocking
at the client boundary and constructing actual `openai.types.chat.ChatCompletion` instances --
no live server call is made or possible without `QWEN3VL_BASE_URL` pointing at a real deployment,
but the request/response shape is checked against the real, installed SDK's own types.
`_image_bytes_for` (resolving a `FrameRef` to real image bytes) is the one seam still unwired,
pending the evaluation-parquet adapter.

Unlike the closed judges retired in `docs/DECISIONS.md` D042, the seam here can expose a
per-token logprob-derived confidence directly, so `Confidence(kind="logprob", ...)` is built by
this adapter itself, bypassing `base.build_confidence` (which explicitly does not handle
`kind="logprob"` -- see its docstring).
"""

from __future__ import annotations

import pytest
from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice, ChoiceLogprobs
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_token_logprob import ChatCompletionTokenLogprob

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
            ("2", 100, 0.0, 0.83),
            ("yes", 150, 0.0, 0.91),
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
            ("1", 100, 0.0, 0.5),
            ("no", 100, 0.0, 0.5),
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
            ("1", 100, 0.0, None),
            ("yes", 100, 0.0, 0.77),
        ],
    )
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="logprob", value=0.77)


def test_both_logprobs_none_falls_back_to_kind_none(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_calls(
        monkeypatch,
        [
            ("1", 100, 0.0, None),
            ("yes", 100, 0.0, None),
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
            ("1", 100, 0.0, 1.5),
            ("yes", 100, 0.0, -0.2),
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
            ("1", 100, 0.0, 0.6),
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
            ("not a recognizable answer", 100, 0.0, None),
            ("yes", 100, 0.0, 0.5),
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
        ("1", 100, 0.0, "not-a-float"),  # type: ignore[list-item]
        ("yes", 100, 0.0, None),
    ]
    _patch_calls(monkeypatch, garbage_responses)
    judge = Qwen3VLJudge()
    result = judge.judge_frame(_frame(), "P0a")
    assert result.confidence == Confidence(kind="none", value=None)


# --- _image_bytes_for: real for E10k-*, still unwired for S10k-U/S10k-S --------------------
#
# `_frame()` (the shared fixture above) is an `S10k-U` frame -- real image_bytes_for wiring for
# that family needs the raw, contact-gated Egocentric-10K corpus adapter, not yet inspected
# (docs/HANDOFF.md), so these two tests exercise the still-real "raises" path. Real E10k-*
# wiring itself is `sampling.draw.image_bytes_for`'s own job and is tested there
# (`tests/test_sampling_draw.py`); `Qwen3VLJudge._image_bytes_for` is a one-line delegation to
# it, verified below.


def test_image_bytes_for_seam_unwired_for_s10k_raises_not_implemented() -> None:
    judge = Qwen3VLJudge()
    with pytest.raises(NotImplementedError):
        judge._image_bytes_for(_frame())


def test_call_qwen3vl_propagates_the_unwired_image_seam_for_s10k() -> None:
    # _call_qwen3vl itself is real (wired to the openai client against the self-hosted vLLM
    # server); it still raises here only because it calls the still-unwired S10k-U image seam
    # before ever touching the network.
    judge = Qwen3VLJudge()
    with pytest.raises(NotImplementedError):
        judge._call_qwen3vl(_frame(), "some prompt text")


def test_image_bytes_for_delegates_to_the_real_sampling_seam(monkeypatch: pytest.MonkeyPatch) -> None:
    import vernier.judges.qwen3vl as qwen3vl_mod

    calls: list[FrameRef] = []

    def _fake_image_bytes_for(frame: FrameRef) -> bytes:
        calls.append(frame)
        return b"\xff\xd8\xff real-looking jpeg bytes"

    monkeypatch.setattr(qwen3vl_mod, "image_bytes_for", _fake_image_bytes_for)

    judge = Qwen3VLJudge()
    frame = _frame()
    result = judge._image_bytes_for(frame)

    assert result == b"\xff\xd8\xff real-looking jpeg bytes"
    assert calls == [frame]


# --- _call_qwen3vl: real SDK wiring, mocked at the client boundary -------------------------
#
# These construct actual `openai.types.chat.ChatCompletion` instances (the real SDK's own
# response type) so a mismatch between this test's assumptions and the real SDK/vLLM's shape
# would surface as a pydantic validation error in the fixture itself, not a false-positive pass.


def _fake_completion(
    text: str,
    *,
    token_logprobs: list[float] | None,
    model: str = "Qwen/Qwen3-VL-8B-Instruct-FP8",
) -> ChatCompletion:
    logprobs = None
    if token_logprobs is not None:
        logprobs = ChoiceLogprobs(
            content=[
                ChatCompletionTokenLogprob(token=f"t{i}", logprob=lp, bytes=None, top_logprobs=[])
                for i, lp in enumerate(token_logprobs)
            ]
        )
    return ChatCompletion(
        id="chatcmpl-test",
        object="chat.completion",
        created=0,
        model=model,
        choices=[
            Choice(
                index=0,
                finish_reason="stop",
                message=ChatCompletionMessage(role="assistant", content=text),
                logprobs=logprobs,
            )
        ],
    )


def test_call_qwen3vl_extracts_text_latency_and_mean_token_probability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import math

    judge = Qwen3VLJudge()
    monkeypatch.setattr(judge, "_image_bytes_for", lambda frame: b"\xff\xd8\xff fake jpeg")
    completion = _fake_completion("2", token_logprobs=[-0.1, -0.05])

    class _FakeCompletions:
        def create(self, **kwargs: object) -> ChatCompletion:
            assert kwargs["model"] == "Qwen/Qwen3-VL-8B-Instruct-FP8"
            assert kwargs["logprobs"] is True
            return completion

    fake_client = type("FakeClient", (), {"chat": type("Chat", (), {"completions": _FakeCompletions()})()})()
    monkeypatch.setattr(Qwen3VLJudge, "_client", property(lambda self: fake_client))

    raw, latency_ms, cost_usd, token_logprob = judge._call_qwen3vl(_frame(), "count the hands")

    assert raw == "2"
    assert latency_ms >= 0
    assert cost_usd >= 0
    assert token_logprob == pytest.approx(math.exp((-0.1 + -0.05) / 2))


def test_call_qwen3vl_returns_none_logprob_when_server_omits_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    judge = Qwen3VLJudge()
    monkeypatch.setattr(judge, "_image_bytes_for", lambda frame: b"\xff\xd8\xff fake jpeg")
    completion = _fake_completion("yes", token_logprobs=None)

    class _FakeCompletions:
        def create(self, **kwargs: object) -> ChatCompletion:
            return completion

    fake_client = type("FakeClient", (), {"chat": type("Chat", (), {"completions": _FakeCompletions()})()})()
    monkeypatch.setattr(Qwen3VLJudge, "_client", property(lambda self: fake_client))

    _, _, _, token_logprob = judge._call_qwen3vl(_frame(), "did they touch it")
    assert token_logprob is None


def test_client_base_url_appends_v1_for_vlllms_openai_compatible_routes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caught by a real 404 against the live deployed server, not by any prior test here: every
    other test in this file monkeypatches the `_client` property itself, so none of them
    exercise its real construction. `openai.OpenAI()`'s own default base_url already ends in
    "/v1" -- the client never appends it for a custom base_url, so a bare Modal server root URL
    404s on every real call unless "/v1" is appended here."""
    monkeypatch.setenv("QWEN3VL_BASE_URL", "https://example.modal.direct")
    judge = Qwen3VLJudge()
    assert str(judge._client.base_url) == "https://example.modal.direct/v1/"


def test_client_base_url_handles_a_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QWEN3VL_BASE_URL", "https://example.modal.direct/")
    judge = Qwen3VLJudge()
    assert str(judge._client.base_url) == "https://example.modal.direct/v1/"


def test_call_qwen3vl_updates_judge_rev_from_the_real_response(monkeypatch: pytest.MonkeyPatch) -> None:
    judge = Qwen3VLJudge()
    monkeypatch.setattr(judge, "_image_bytes_for", lambda frame: b"\xff\xd8\xff fake jpeg")
    completion = _fake_completion(
        "0", token_logprobs=[-0.02], model="Qwen/Qwen3-VL-8B-Instruct-FP8"
    )

    class _FakeCompletions:
        def create(self, **kwargs: object) -> ChatCompletion:
            return completion

    fake_client = type("FakeClient", (), {"chat": type("Chat", (), {"completions": _FakeCompletions()})()})()
    monkeypatch.setattr(Qwen3VLJudge, "_client", property(lambda self: fake_client))

    assert judge.judge_rev() != "Qwen/Qwen3-VL-8B-Instruct-FP8"  # unresolved before any call
    judge._call_qwen3vl(_frame(), "count the hands")
    assert judge.judge_rev() == "Qwen/Qwen3-VL-8B-Instruct-FP8"
