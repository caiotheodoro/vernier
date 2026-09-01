"""Behavioural tests for `scripts/judge_concurrency.py`.

The fake judge here is dict-keyed by `frame_id` (thread-safe for concurrent reads, unlike an
`iter()`-based fake) and sleeps briefly to make real concurrency observable -- a purely
sequential implementation would take `n * sleep` seconds; a concurrent one takes roughly
`sleep` seconds regardless of `n`, bounded by `max_workers`.
"""

from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from judge_concurrency import judge_frames_concurrent, run_concurrent  # noqa: E402

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


def _response(frame_id: str) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="fake",
        judge_rev="fake-rev",
        prompt_variant="P0a",
        hands_visible=1,
        manipulation=False,
        confidence=Confidence(kind="none", value=None),
        raw="raw",
        status="ok",
        latency_ms=10,
        cost_usd=0.0001,
    )


class _SlowFakeJudge(JudgeAdapter):
    """Sleeps `delay_s` per call and records concurrently-active-call count, so tests can
    assert real overlap happened, not just that results came back correct."""

    judge = "fake"

    def __init__(self, delay_s: float) -> None:
        self._delay_s = delay_s
        self._lock = threading.Lock()
        self._active = 0
        self.max_observed_concurrency = 0

    def judge_rev(self) -> str:
        return "fake-rev"

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        with self._lock:
            self._active += 1
            self.max_observed_concurrency = max(self.max_observed_concurrency, self._active)
        time.sleep(self._delay_s)
        with self._lock:
            self._active -= 1
        return _response(frame.frame_id)


def test_run_concurrent_preserves_input_order_regardless_of_completion_order() -> None:
    # Item "2" finishes fastest, "0" slowest -- output must still match input order.
    delays = {"0": 0.06, "1": 0.03, "2": 0.0}

    def _fn(item: str) -> JudgeResponse:
        time.sleep(delays[item])
        return _response(item)

    results = run_concurrent(["0", "1", "2"], _fn, max_workers=3)

    assert [r.frame_id for r in results] == ["0", "1", "2"]


def test_run_concurrent_reports_progress_for_every_item() -> None:
    progress_calls: list[tuple[int, int]] = []
    run_concurrent(
        ["a", "b", "c"],
        lambda item: _response(item),
        max_workers=3,
        on_progress=lambda done, total: progress_calls.append((done, total)),
    )

    assert len(progress_calls) == 3
    assert progress_calls[-1] == (3, 3)
    assert all(total == 3 for _done, total in progress_calls)


def test_judge_frames_concurrent_achieves_real_overlap() -> None:
    judge = _SlowFakeJudge(delay_s=0.05)
    frames = [_frame(str(i)) for i in range(6)]

    start = time.monotonic()
    results = judge_frames_concurrent(frames, "P0a", judge, max_workers=6)
    elapsed = time.monotonic() - start

    assert [r.frame_id for r in results] == [f.frame_id for f in frames]
    # Real concurrency: more than one call was active at once (would be 1 if sequential).
    assert judge.max_observed_concurrency > 1
    # Real speedup: 6 calls x 0.05s would take >=0.3s sequential; concurrent should be well
    # under that (generous bound to avoid flaking on a loaded CI machine).
    assert elapsed < 0.25


def test_judge_frames_concurrent_respects_max_workers_as_a_ceiling() -> None:
    judge = _SlowFakeJudge(delay_s=0.05)
    frames = [_frame(str(i)) for i in range(6)]

    judge_frames_concurrent(frames, "P0a", judge, max_workers=2)

    assert judge.max_observed_concurrency <= 2
