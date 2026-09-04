"""`e5_prompt_sweep._rates_per_variant` checkpoint + resume -- crash insurance for the H3
sweep, which makes more real judge calls per frame than `e2_replication` does and, before
D054, had none (docs/DECISIONS.md D054).

Checkpointing is per-variant: a completed variant's positive rate and per-frame answers are
written to disk, and `--resume` skips any variant already recorded. A crash mid-variant loses
only that one variant's calls, not the whole sweep.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from e5_prompt_sweep import _rates_per_variant  # noqa: E402

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
        n = int(frame.frame_id.rsplit("-", 1)[1])
        return JudgeResponse(
            frame_id=frame.frame_id,
            judge="fake",
            judge_rev="fake-rev",
            prompt_variant=prompt_variant,
            hands_visible=1 if n % 2 == 0 else 0,
            manipulation=n % 2 == 0,
            confidence=Confidence(kind="none", value=None),
            raw="raw",
            status="ok",
            latency_ms=10,
            cost_usd=0.0001,
        )


_VARIANTS: tuple[PromptVariant, ...] = ("P0b", "P1", "P2")


def _answer(resp: JudgeResponse) -> bool:
    return resp.hands_visible is not None and resp.hands_visible >= 1


def test_checkpoint_records_each_variant_as_it_finishes(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(6)]
    ckpt = tmp_path / "e5.hand.checkpoint.json"

    _rates_per_variant(frames, _VARIANTS, _FakeJudge(), answer=_answer, checkpoint_path=ckpt)

    saved = json.loads(ckpt.read_text())
    assert set(saved["variants"]) == {"P0b", "P1", "P2"}
    assert saved["variants"]["P0b"]["rate"] == 0.5  # frames 0,2,4 have a hand; 6 frames total


def test_resume_skips_variants_already_in_the_checkpoint(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(6)]
    ckpt = tmp_path / "e5.hand.checkpoint.json"
    ckpt.write_text(
        json.dumps(
            {
                "variants": {
                    "P0b": {
                        "rate": 0.5,
                        "answers": {f"uuid-{i}": (i % 2 == 0) for i in range(6)},
                    }
                }
            }
        )
    )

    judged: list[str] = []

    class _CountingJudge(_FakeJudge):
        def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
            judged.append(prompt_variant)
            return super().judge_frame(frame, prompt_variant)

    rates, answers = _rates_per_variant(
        frames, _VARIANTS, _CountingJudge(), answer=_answer, checkpoint_path=ckpt, resume=True
    )

    assert "P0b" not in judged  # already done -- not re-judged
    assert set(judged) == {"P1", "P2"}
    assert rates["P0b"] == 0.5  # carried forward from the checkpoint
    assert answers["uuid-0"]["P0b"] is True


def test_resumed_result_matches_a_fresh_run(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(6)]
    fresh_rates, fresh_answers = _rates_per_variant(
        frames, _VARIANTS, _FakeJudge(), answer=_answer
    )

    ckpt = tmp_path / "e5.hand.checkpoint.json"
    _rates_per_variant(
        frames, ("P0b",), _FakeJudge(), answer=_answer, checkpoint_path=ckpt
    )
    resumed_rates, resumed_answers = _rates_per_variant(
        frames, _VARIANTS, _FakeJudge(), answer=_answer, checkpoint_path=ckpt, resume=True
    )

    assert resumed_rates == fresh_rates
    assert resumed_answers == fresh_answers


def test_no_checkpoint_path_keeps_the_old_signature_working(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(4)]
    rates, answers = _rates_per_variant(frames, _VARIANTS, _FakeJudge(), answer=_answer)
    assert set(rates) == {"P0b", "P1", "P2"}
    assert list(tmp_path.iterdir()) == []

# --- D069: per-frame JudgeResponse persistence alongside the checkpoint ---------------------

from judge_responses_io import append_response, read_responses  # noqa: E402

_HAND_VARIANTS: tuple[PromptVariant, ...] = ("P0b", "P1", "P2", "P3", "P4")

class _UnparseableOnFrameOne(_FakeJudge):
    """Frame `uuid-1` comes back non-ok under every variant -- the record the sweep's own
    `status != "ok"` guard drops from its rates but the jsonl must keep verbatim."""

    def judge_frame(self, frame: FrameRef, prompt_variant: PromptVariant) -> JudgeResponse:
        resp = super().judge_frame(frame, prompt_variant)
        if frame.frame_id == "uuid-1":
            return resp.model_copy(
                update={"status": "unparseable", "hands_visible": None, "manipulation": None}
            )
        return resp

def test_responses_path_keeps_non_ok_responses(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(4)]
    responses_path = tmp_path / "r.jsonl"

    rates, _ = _rates_per_variant(
        frames,
        _HAND_VARIANTS,
        _UnparseableOnFrameOne(),
        answer=_answer,
        responses_path=responses_path,
    )

    lines = responses_path.read_text().splitlines()
    assert len(lines) == 20  # 4 frames x 5 variants, the unparseable ones included
    parsed = [JudgeResponse.model_validate(json.loads(line)) for line in lines]
    non_ok = [r for r in parsed if r.status != "ok"]
    assert len(non_ok) == 5 and {r.frame_id for r in non_ok} == {"uuid-1"}
    assert {r.prompt_variant for r in parsed} == set(_HAND_VARIANTS)
    assert rates["P0b"] == 2 / 3  # frames 0, 2 of the 3 ok frames -- uuid-1 is out of the denominator

def test_resume_keeps_saved_variants_lines_and_drops_the_partial_one(tmp_path: Path) -> None:
    frames = [_frame(str(i)) for i in range(6)]
    ckpt = tmp_path / "e5.hand.checkpoint.json"
    responses_path = tmp_path / "r.jsonl"
    ckpt.write_text(
        json.dumps(
            {
                "variants": {
                    "P0b": {
                        "rate": 0.5,
                        "answers": {f"uuid-{i}": (i % 2 == 0) for i in range(6)},
                    }
                }
            }
        )
    )
    # The crashed attempt's jsonl: P0b complete, then P1 died after its first frame.
    with responses_path.open("w") as fh:
        for frame in frames:
            append_response(fh, _FakeJudge().judge_frame(frame, "P0b"))
        append_response(fh, _FakeJudge().judge_frame(frames[0], "P1"))
    p0b_lines_before = responses_path.read_text().splitlines()[:6]

    _rates_per_variant(
        frames,
        _VARIANTS,
        _FakeJudge(),
        answer=_answer,
        checkpoint_path=ckpt,
        resume=True,
        responses_path=responses_path,
    )

    lines = responses_path.read_text().splitlines()
    assert lines[:6] == p0b_lines_before  # the saved variant's records are untouched
    assert len(lines) == 18  # 6 frames x 3 variants; the stray partial P1 line is gone
    parsed = read_responses(responses_path)
    keys = [(r.frame_id, r.prompt_variant) for r in parsed]
    assert len(keys) == len(set(keys)) == 18
    assert {v for _, v in keys} == set(_VARIANTS)
