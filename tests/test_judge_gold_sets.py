"""Behavioural tests for `scripts/judge_gold_sets.py`'s checkpoint/resume logic.

`Qwen3VLJudge.judge_frame` is monkeypatched -- no live server call is made or possible here;
this only exercises the resume/checkpoint-writing behaviour around it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from judge_gold_sets import _judge_sample  # noqa: E402

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
        sample="G200-ego",
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


def test_judge_sample_writes_a_real_record_per_frame(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frames = [_frame(str(i)) for i in range(5)]
    monkeypatch.setattr("judge_gold_sets.draw_sample", lambda sample: frames)
    checkpoint_path = tmp_path / "ckpt.json"

    result = _judge_sample("G200-ego", _FakeJudge(), checkpoint_path=checkpoint_path, checkpoint_every=2)

    assert len(result) == 5
    assert {r["frame_id"] for r in result} == {f.frame_id for f in frames}
    on_disk = json.loads(checkpoint_path.read_text())
    assert len(on_disk) == 5


def test_judge_sample_resumes_from_existing_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frames = [_frame(str(i)) for i in range(3)]
    monkeypatch.setattr("judge_gold_sets.draw_sample", lambda sample: frames)
    checkpoint_path = tmp_path / "ckpt.json"
    checkpoint_path.write_text(
        json.dumps(
            [
                JudgeResponse(
                    frame_id=frames[0].frame_id,
                    judge="fake",
                    judge_rev="fake-rev",
                    prompt_variant="P0b",
                    hands_visible=2,
                    manipulation=False,
                    confidence=Confidence(kind="none", value=None),
                    raw="raw",
                    status="ok",
                    latency_ms=10,
                    cost_usd=0.0001,
                ).model_dump(mode="json")
            ]
        )
    )

    calls: list[str] = []

    class _RecordingJudge(_FakeJudge):
        def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
            calls.append(frame.frame_id)
            return super().judge_frame(frame, prompt_variant)

    result = _judge_sample("G200-ego", _RecordingJudge(), checkpoint_path=checkpoint_path)

    assert frames[0].frame_id not in calls  # already checkpointed -- not re-judged
    assert len(result) == 3
    # the pre-existing record's real values survive resume, not overwritten with the fake judge's
    preserved = next(r for r in result if r["frame_id"] == frames[0].frame_id)
    assert preserved["hands_visible"] == 2
    assert preserved["manipulation"] is False


def test_judge_sample_checkpoints_at_the_configured_interval(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    frames = [_frame(str(i)) for i in range(4)]
    monkeypatch.setattr("judge_gold_sets.draw_sample", lambda sample: frames)
    checkpoint_path = tmp_path / "ckpt.json"
    seen_sizes: list[int] = []

    class _RecordingJudge(_FakeJudge):
        def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
            resp = super().judge_frame(frame, prompt_variant)
            if checkpoint_path.is_file():
                seen_sizes.append(len(json.loads(checkpoint_path.read_text())))
            return resp

    _judge_sample("G200-ego", _RecordingJudge(), checkpoint_path=checkpoint_path, checkpoint_every=2)

    assert 2 in seen_sizes  # a checkpoint existed partway through, not only at the end
