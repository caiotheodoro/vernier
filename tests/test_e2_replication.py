"""Behavioural tests for `scripts/e2_replication.py`'s pure aggregation/hypothesis logic.

`_run_variant` is exercised against a fake `Qwen3VLJudge`-shaped judge (a real `JudgeAdapter`
subclass returning canned `JudgeResponse`s), not a live server -- the real network/HF parts
(`_published_labels`, `draw_sample`) are exactly the kind of real-I/O seam this project never
unit-tests directly (see `tests/test_check_eval_parquets.py`'s own convention).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from e2_replication import _h1, _h1b, _run_variant  # noqa: E402

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.models import Confidence, FrameRef, JudgeResponse


def _frame(frame_id: str) -> FrameRef:
    return FrameRef(
        frame_id=frame_id,
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


class _FakeJudge(JudgeAdapter):
    """Returns one canned `JudgeResponse` per call, in order, regardless of the frame passed --
    `_run_variant` calls `judge_frame` once per frame, so the canned sequence's length must
    match the frame list length."""

    judge = "fake"

    def __init__(self, responses: list[JudgeResponse]) -> None:
        self._responses = iter(responses)

    def judge_rev(self) -> str:
        return "fake-rev"

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        return next(self._responses)


def _ok_response(frame_id: str, hands_visible: int, manipulation: bool) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="fake",
        judge_rev="fake-rev",
        prompt_variant="P0a",
        hands_visible=hands_visible,  # type: ignore[arg-type]
        manipulation=manipulation,
        confidence=Confidence(kind="none", value=None),
        raw="raw",
        status="ok",
        latency_ms=100,
        cost_usd=0.001,
    )


def _unparseable_response(frame_id: str) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="fake",
        judge_rev="fake-rev",
        prompt_variant="P0a",
        hands_visible=None,
        manipulation=None,
        confidence=Confidence(kind="none", value=None),
        raw="garbage",
        status="unparseable",
        latency_ms=50,
        cost_usd=0.0005,
    )


def test_run_variant_computes_aggregate_rates_over_ok_responses_only() -> None:
    frames = [_frame("f0"), _frame("f1"), _frame("f2")]
    responses = [
        _ok_response("f0", hands_visible=2, manipulation=True),
        _ok_response("f1", hands_visible=0, manipulation=False),
        _unparseable_response("f2"),
    ]
    judge = _FakeJudge(responses)

    result = _run_variant(frames, "P0a", judge, published={})

    assert result["n_total"] == 3
    assert result["n_ok"] == 2
    assert result["status_counts"] == {"ok": 2, "unparseable": 1}
    # 1 of 2 ok responses has hands_visible >= 1.
    assert result["hand_ge1_rate"] == pytest.approx(0.5)
    assert result["hand_eq2_rate"] == pytest.approx(0.5)
    assert result["active_manipulation_rate"] == pytest.approx(0.5)


def test_run_variant_all_non_ok_gives_zero_rates_not_a_division_error() -> None:
    frames = [_frame("f0")]
    judge = _FakeJudge([_unparseable_response("f0")])

    result = _run_variant(frames, "P0a", judge, published={})

    assert result["n_ok"] == 0
    assert result["hand_ge1_rate"] == 0.0
    assert result["active_manipulation_rate"] == 0.0


def test_run_variant_tracks_cost_and_latency() -> None:
    frames = [_frame("f0"), _frame("f1")]
    judge = _FakeJudge(
        [
            _ok_response("f0", hands_visible=1, manipulation=False),
            _ok_response("f1", hands_visible=1, manipulation=False),
        ]
    )

    result = _run_variant(frames, "P0a", judge, published={})

    assert result["total_cost_usd"] == pytest.approx(0.002)
    assert result["total_latency_ms"] == 200


def test_run_variant_computes_agreement_against_published_labels_when_present() -> None:
    frames = [_frame("f0"), _frame("f1")]
    judge = _FakeJudge(
        [
            _ok_response("f0", hands_visible=2, manipulation=True),  # agrees with published
            _ok_response("f1", hands_visible=0, manipulation=True),  # disagrees on both
        ]
    )
    published = {"f0": (2, True), "f1": (1, False)}

    result = _run_variant(frames, "P0a", judge, published)

    assert result["n_comparable_to_published"] == 2
    assert result["hand_count_exact_agreement_rate"] == pytest.approx(0.5)
    assert result["active_labor_agreement_rate"] == pytest.approx(0.5)


def test_run_variant_frame_with_no_published_label_is_excluded_from_agreement() -> None:
    frames = [_frame("f0")]
    judge = _FakeJudge([_ok_response("f0", hands_visible=1, manipulation=True)])

    result = _run_variant(frames, "P0a", judge, published={})

    assert result["n_comparable_to_published"] == 0
    assert result["hand_count_exact_agreement_rate"] == 0.0


def test_h1_flags_within_and_outside_tolerance() -> None:
    results_p0a = {
        "hand_ge1_rate": 0.9642,  # exactly the published figure -> 0pp diff
        "hand_eq2_rate": 0.90,  # published 0.7634 -> ~13.7pp diff, outside tolerance
        "active_manipulation_rate": 0.9066,  # published 0.9166 -> exactly 1pp diff, within
    }

    h1 = _h1(results_p0a)

    assert h1["hand_ge1_rate"]["diff_pp"] == pytest.approx(0.0, abs=1e-9)
    assert h1["hand_ge1_rate"]["within_2pp_tolerance"] is True
    assert h1["hand_eq2_rate"]["within_2pp_tolerance"] is False
    assert h1["active_manipulation_rate"]["within_2pp_tolerance"] is True


def test_h1b_flags_disagreement_at_the_one_pp_boundary() -> None:
    results_p0a = {"active_manipulation_rate": 0.90}
    results_p0b_disagreeing = {"active_manipulation_rate": 0.89}  # exactly 1pp
    results_p0b_agreeing = {"active_manipulation_rate": 0.895}  # 0.5pp

    disagreeing = _h1b(results_p0a, results_p0b_disagreeing)
    agreeing = _h1b(results_p0a, results_p0b_agreeing)

    assert disagreeing["p0_variants_disagree"] is True
    assert agreeing["p0_variants_disagree"] is False
