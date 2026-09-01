"""Behavioural tests for `scripts/generate_rung1_labels.py`'s pure logic.

`published_labels_for_sample` (real parquet reads) is monkeypatched with a synthetic in-memory
dict -- this file tests the leak-exclusion (train minus eval-holdout, across all three corpora)
and the stored-label-to-`JudgeResponse` shape, not the real parquet I/O
(`tests/test_e2_replication.py`/manual live checks already cover that helper's real behaviour).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import generate_rung1_labels as rung1_mod  # noqa: E402

from vernier.models import Confidence, FrameRef
from vernier.sampling.draw import SampleName
from vernier.sampling.membership import write_membership


def _frame(sample: str, uid: str) -> FrameRef:
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
        sample=sample,
        stratum="unstratified",
        why_no_provenance="test fixture",
    )


def test_stored_label_response_shape() -> None:
    resp = rung1_mod._stored_label_response("uuid-0", 2, True)

    assert resp.judge == "gemini-2.5-flash"
    assert resp.prompt_variant == "P0b"
    assert resp.hands_visible == 2
    assert resp.manipulation is True
    assert resp.confidence == Confidence(kind="none", value=None)
    assert resp.status == "ok"
    assert resp.latency_ms == 0
    assert resp.cost_usd == 0.0
    assert resp.raw == "2\n---\nyes"


def test_generate_labels_excludes_each_corpus_own_g200_holdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rung1_mod, "_MEMBERSHIP_ROOT", tmp_path)

    all_ego = [_frame("E10k-ego", f"ego{i}") for i in range(5)]
    eval_ego = [all_ego[1], all_ego[3]]
    write_membership("E10k-ego", all_ego, tmp_path)
    write_membership("G200-ego", eval_ego, tmp_path)
    write_membership("E10k-ego4d", [], tmp_path)
    write_membership("G200-ego4d", [], tmp_path)
    write_membership("E10k-epic", [], tmp_path)
    write_membership("G200-epic", [], tmp_path)

    fake_store = {
        "E10k-ego": {f.frame_id: (1, False) for f in all_ego},
    }
    monkeypatch.setattr(
        rung1_mod,
        "published_labels_for_sample",
        lambda sample, frame_ids: {
            fid: v for fid, v in fake_store.get(sample, {}).items() if fid in frame_ids
        },
    )

    responses = rung1_mod.generate_labels()

    response_ids = {r.frame_id for r in responses}
    eval_ids = {f.frame_id for f in eval_ego}
    assert len(responses) == 3  # 5 total minus 2 held out for evaluation
    assert response_ids.isdisjoint(eval_ids)


def test_generate_labels_covers_all_three_corpora(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(rung1_mod, "_MEMBERSHIP_ROOT", tmp_path)

    pools: dict[SampleName, list[FrameRef]] = {
        "E10k-ego": [_frame("E10k-ego", "e0")],
        "E10k-ego4d": [_frame("E10k-ego4d", "e4d0")],
        "E10k-epic": [_frame("E10k-epic", "epic0")],
    }
    for sample, frames in pools.items():
        write_membership(sample, frames, tmp_path)
    write_membership("G200-ego", [], tmp_path)
    write_membership("G200-ego4d", [], tmp_path)
    write_membership("G200-epic", [], tmp_path)

    monkeypatch.setattr(
        rung1_mod,
        "published_labels_for_sample",
        lambda sample, frame_ids: {fid: (0, False) for fid in frame_ids},
    )

    responses = rung1_mod.generate_labels()

    assert {r.frame_id for r in responses} == {"uuid-e0", "uuid-e4d0", "uuid-epic0"}
