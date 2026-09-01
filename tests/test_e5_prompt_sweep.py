"""Behavioural tests for `scripts/e5_prompt_sweep.py`'s pure aggregation/IPR-PAR logic.

Same convention as `tests/test_e2_replication.py`: exercised against a fake `JudgeAdapter`
returning canned, per-`(frame_id, prompt_variant)` responses, never a live server.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from e5_prompt_sweep import _ipr_par, _rates_per_variant  # noqa: E402

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


def _response(
    frame_id: str, prompt_variant: PromptVariant, *, status: str = "ok", hands_visible: int = 1
) -> JudgeResponse:
    ok = status == "ok"
    return JudgeResponse(
        frame_id=frame_id,
        judge="fake",
        judge_rev="fake-rev",
        prompt_variant=prompt_variant,
        hands_visible=hands_visible if ok else None,  # type: ignore[arg-type]
        manipulation=False if ok else None,
        confidence=Confidence(kind="none", value=None),
        raw="raw",
        status=status,  # type: ignore[arg-type]
        latency_ms=10,
        cost_usd=0.0001,
    )


class _FakeJudge(JudgeAdapter):
    """Keyed by (frame_id, prompt_variant) -- `_rates_per_variant` calls `judge_frame` once per
    (frame, variant) pair, in no particular guaranteed order, so a dict lookup (not an
    iterator) is the right shape here, unlike `test_e2_replication.py`'s single-variant-at-a-
    time `_FakeJudge`."""

    judge = "fake"

    def __init__(self, responses: dict[tuple[str, str], JudgeResponse]) -> None:
        self._responses = responses

    def judge_rev(self) -> str:
        return "fake-rev"

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        return self._responses[(frame.frame_id, prompt_variant)]


def test_rates_per_variant_computes_positive_rate_per_variant() -> None:
    frames = [_frame("f0"), _frame("f1")]
    responses = {
        ("f0", "P0b"): _response("f0", "P0b", hands_visible=1),
        ("f0", "P1"): _response("f0", "P1", hands_visible=0),
        ("f1", "P0b"): _response("f1", "P0b", hands_visible=1),
        ("f1", "P1"): _response("f1", "P1", hands_visible=1),
    }
    judge = _FakeJudge(responses)

    rates, _ = _rates_per_variant(
        frames,
        ("P0b", "P1"),
        judge,
        answer=lambda resp: resp.hands_visible is not None and resp.hands_visible >= 1,
    )

    assert rates == {"P0b": 1.0, "P1": 0.5}


def test_rates_per_variant_excludes_non_ok_from_denominator() -> None:
    frames = [_frame("f0"), _frame("f1")]
    responses = {
        ("f0", "P0b"): _response("f0", "P0b", status="unparseable"),
        ("f1", "P0b"): _response("f1", "P0b", hands_visible=1),
    }
    judge = _FakeJudge(responses)

    rates, _ = _rates_per_variant(
        frames,
        ("P0b",),
        judge,
        answer=lambda resp: resp.hands_visible is not None and resp.hands_visible >= 1,
    )

    assert rates == {"P0b": 1.0}  # only f1 counted; f0's unparseable response is excluded


def test_ipr_par_full_unanimity_gives_ipr_one() -> None:
    per_frame_answers = {
        "f0": {"P0b": True, "P1": True, "P2": True},
        "f1": {"P0b": False, "P1": False, "P2": False},
    }

    result = _ipr_par(per_frame_answers, ("P0b", "P1", "P2"))

    assert result["ipr"] == pytest.approx(1.0)
    assert result["par"] == pytest.approx(1.0)
    assert result["n_frames_with_all_variants_ok"] == 2


def test_ipr_par_partial_disagreement() -> None:
    # f0: all three agree (True). f1: P0b/P1 agree (False), P2 disagrees (True) -- 2 of 3 pairs
    # agree ((P0b,P1) agree; (P0b,P2) and (P1,P2) disagree) -> pairwise rate 1/3 for f1.
    per_frame_answers = {
        "f0": {"P0b": True, "P1": True, "P2": True},
        "f1": {"P0b": False, "P1": False, "P2": True},
    }

    result = _ipr_par(per_frame_answers, ("P0b", "P1", "P2"))

    assert result["ipr"] == pytest.approx(0.5)  # only f0 is unanimous
    assert result["par"] == pytest.approx((1.0 + 1 / 3) / 2)


def test_ipr_par_excludes_frames_missing_a_swept_variant() -> None:
    per_frame_answers = {
        "f0": {"P0b": True, "P1": True},  # missing P2 (e.g. that call wasn't "ok")
        "f1": {"P0b": True, "P1": True, "P2": True},
    }

    result = _ipr_par(per_frame_answers, ("P0b", "P1", "P2"))

    assert result["n_frames_with_all_variants_ok"] == 1
    assert result["ipr"] == pytest.approx(1.0)


def test_ipr_par_no_complete_frames_returns_none() -> None:
    per_frame_answers = {"f0": {"P0b": True}}

    result = _ipr_par(per_frame_answers, ("P0b", "P1"))

    assert result == {"ipr": None, "par": None, "n_frames_with_all_variants_ok": 0}
