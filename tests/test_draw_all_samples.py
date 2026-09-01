"""Behavioural tests for `scripts/draw_all_samples.py`'s real orchestration logic.

`draw_sample` itself is monkeypatched (a synthetic in-memory DAG, same convention as
`tests/test_sampling_draw.py`) -- this file tests the *ordering and persistence* logic, not
`draw_sample`'s own sampling behaviour, which already has its own test suite.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import draw_all_samples as das_mod  # noqa: E402
from draw_all_samples import draw_and_persist_all  # noqa: E402

from vernier.models import FrameRef
from vernier.sampling.membership import load_membership


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


def test_draws_every_sample_in_order_and_persists_each(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    draw_calls: list[str] = []

    def _fake_draw_sample(sample: str, seed: int = 777) -> list[FrameRef]:
        draw_calls.append(sample)
        return [_frame(sample, "0"), _frame(sample, "1")]

    monkeypatch.setattr(das_mod, "draw_sample", _fake_draw_sample)

    results = draw_and_persist_all(root=tmp_path)

    assert draw_calls == list(das_mod._DRAW_ORDER)
    assert results == {sample: 2 for sample in das_mod._DRAW_ORDER}
    # Actually persisted -- readable back via the real load_membership, not just claimed.
    for sample in das_mod._DRAW_ORDER:
        loaded = load_membership(sample, tmp_path)
        assert len(loaded) == 2


def test_a_not_implemented_sample_is_skipped_not_fatal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _fake_draw_sample(sample: str, seed: int = 777) -> list[FrameRef]:
        if sample in ("S10k-U", "S10k-S"):
            raise NotImplementedError(f"{sample} needs the raw corpus adapter")
        return [_frame(sample, "0")]

    monkeypatch.setattr(das_mod, "draw_sample", _fake_draw_sample)

    results = draw_and_persist_all(root=tmp_path)

    assert results["S10k-U"] == "skipped: S10k-U needs the raw corpus adapter"
    assert results["S10k-S"] == "skipped: S10k-S needs the raw corpus adapter"
    # Every other sample still drew and persisted despite the two skips.
    assert results["E10k-ego"] == 1
    assert results["R100"] == 1


def test_draw_order_puts_every_parent_before_its_dependents() -> None:
    order = das_mod._DRAW_ORDER
    assert order.index("E10k-ego") < order.index("P2k")
    assert order.index("P2k") < order.index("G200-ego")
    assert order.index("E10k-ego4d") < order.index("G200-ego4d")
    assert order.index("E10k-epic") < order.index("G200-epic")
    for parent in ("G200-ego", "G200-ego4d", "G200-epic"):
        assert order.index(parent) < order.index("R100")
