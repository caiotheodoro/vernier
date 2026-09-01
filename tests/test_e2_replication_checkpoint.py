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
