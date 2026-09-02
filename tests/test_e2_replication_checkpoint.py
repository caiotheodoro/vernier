"""Behavioural tests for `e2_replication._run_variant`'s checkpointing -- real insurance for a
many-hour full-scale run, added alongside the D054 full-N authorization.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from e2_replication import _run_variant  # noqa: E402

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


class _FakeJudge(JudgeAdapter):
    judge = "fake"

    def judge_rev(self) -> str:
        return "fake-rev"

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        return JudgeResponse(
            frame_id=frame.frame_id,
            judge="fake",
            judge_rev="fake-rev",
            prompt_variant=prompt_variant,
            hands_visible=1,
            manipulation=True,
            confidence=Confidence(kind="none", value=None),
            raw="raw",
            status="ok",
            latency_ms=10,
            cost_usd=0.0001,
        )


def test_checkpoint_written_at_the_configured_interval(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(10)]
    checkpoint_path = tmp_path / "ckpt.json"

    _run_variant(
        frames,
        "P0a",
        _FakeJudge(),
        published={},
        checkpoint_path=checkpoint_path,
        checkpoint_every=3,
    )

    checkpoint = json.loads(checkpoint_path.read_text())
    # Final write happens at i == len(frames) regardless of the modulo, so the last checkpoint
    # reflects all 10 frames, not just the last multiple-of-3.
    assert checkpoint["n_processed"] == 10
    assert checkpoint["n_total"] == 10
    assert checkpoint["n_ok"] == 10


def test_no_checkpoint_path_means_no_file_written(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(5)]

    result = _run_variant(frames, "P0a", _FakeJudge(), published={})

    assert result["n_ok"] == 5
    assert list(tmp_path.iterdir()) == []


def test_checkpoint_reflects_running_totals_mid_run(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(6)]
    checkpoint_path = tmp_path / "ckpt.json"
    seen_checkpoints = []

    class _RecordingJudge(_FakeJudge):
        def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
            resp = super().judge_frame(frame, prompt_variant)
            if checkpoint_path.is_file():
                seen_checkpoints.append(json.loads(checkpoint_path.read_text())["n_processed"])
            return resp

    _run_variant(
        frames,
        "P0a",
        _RecordingJudge(),
        published={},
        checkpoint_path=checkpoint_path,
        checkpoint_every=2,
    )

    # Checkpoints exist from partway through the run, not only after it finished.
    assert 2 in seen_checkpoints or 4 in seen_checkpoints


# --- resume_state: continue a crashed run from its last checkpoint ------------------------------
#
# Real need, not speculative (docs/DECISIONS.md D054): the full-N P0b run died at 2,800/10,000
# on a transient 503 with no retry logic, and re-running the first 2,800 frames from scratch
# would silently re-spend judge calls already paid for and already counted.


class _PatternJudge(_FakeJudge):
    """Deterministic per-frame answers keyed off the frame's `uuid-<n>` suffix, so a resumed
    run and a fresh full run are comparing the *same* frame-level judgments."""

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        n = int(frame.frame_id.rsplit("-", 1)[1])
        resp = super().judge_frame(frame, prompt_variant)
        return resp.model_copy(update={"hands_visible": 2 if n % 3 == 0 else 1, "manipulation": n % 2 == 0})


def _checkpoint_after(frames: list[FrameRef], upto: int) -> dict[str, object]:
    """Run the first `upto` frames and return the checkpoint dict `_run_variant` would have
    written at that point -- the real resume input."""
    result = _run_variant(frames[:upto], "P0b", _PatternJudge(), published={})
    return {
        "n_processed": upto,
        "n_total": len(frames),
        "n_ok": result["n_ok"],
        "status_counts": result["status_counts"],
        "hand_ge1_rate": result["hand_ge1_rate"],
        "hand_eq2_rate": result["hand_eq2_rate"],
        "active_manipulation_rate": result["active_manipulation_rate"],
        "total_cost_usd": result["total_cost_usd"],
        "total_latency_ms": result["total_latency_ms"],
    }


def test_resume_state_only_processes_the_unprocessed_tail() -> None:
    frames = [_frame(str(i)) for i in range(10)]
    resume_state = _checkpoint_after(frames, 6)

    calls: list[str] = []

    class _CountingJudge(_PatternJudge):
        def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
            calls.append(frame.frame_id)
            return super().judge_frame(frame, prompt_variant)

    _run_variant(frames, "P0b", _CountingJudge(), published={}, resume_state=resume_state)

    assert calls == [f"uuid-{i}" for i in range(6, 10)]  # frames 0..5 not re-judged


def test_resume_state_final_rates_match_a_fresh_full_run() -> None:
    frames = [_frame(str(i)) for i in range(10)]
    fresh = _run_variant(frames, "P0b", _PatternJudge(), published={})

    resumed = _run_variant(
        frames, "P0b", _PatternJudge(), published={}, resume_state=_checkpoint_after(frames, 5)
    )

    assert resumed["n_ok"] == fresh["n_ok"] == 10
    for key in ("hand_ge1_rate", "hand_eq2_rate", "active_manipulation_rate"):
        assert resumed[key] == pytest.approx(fresh[key], abs=1e-9)


def test_resume_state_carries_forward_cost_and_status_counts() -> None:
    frames = [_frame(str(i)) for i in range(10)]
    resume_state = _checkpoint_after(frames, 6)

    resumed = _run_variant(
        frames, "P0b", _PatternJudge(), published={}, resume_state=resume_state
    )

    assert resumed["status_counts"] == {"ok": 10}
    # cost accumulates on top of what the checkpoint already spent, not from zero.
    assert resumed["total_cost_usd"] > resume_state["total_cost_usd"]
