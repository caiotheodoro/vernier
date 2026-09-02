"""`e2_replication` resume-decision logic: how `main()` treats an existing per-variant
checkpoint when `--resume` is passed (docs/DECISIONS.md D054).

Three cases: no checkpoint -> run fresh; a complete checkpoint (`n_processed == n_total`) ->
reconstruct the result without any judge calls; a partial checkpoint -> hand it to
`_run_variant` as `resume_state`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from e2_replication import _resume_decision  # noqa: E402


def _write(path: Path, **fields: object) -> None:
    base = {
        "n_processed": 0,
        "n_total": 100,
        "n_ok": 0,
        "status_counts": {"ok": 0},
        "hand_ge1_rate": 0.0,
        "hand_eq2_rate": 0.0,
        "active_manipulation_rate": 0.0,
        "total_cost_usd": 0.0,
        "total_latency_ms": 0,
    }
    base.update(fields)
    path.write_text(json.dumps(base))


def test_no_checkpoint_means_run_fresh(tmp_path: Path) -> None:
    kind, payload = _resume_decision(tmp_path / "missing.json", n_frames=100)
    assert kind == "fresh"
    assert payload is None


def test_partial_checkpoint_is_handed_back_as_resume_state(tmp_path: Path) -> None:
    ckpt = tmp_path / "P0b.checkpoint.json"
    _write(ckpt, n_processed=2800, n_total=10000, n_ok=2800, total_cost_usd=1.24)

    kind, payload = _resume_decision(ckpt, n_frames=10000)

    assert kind == "resume"
    assert payload is not None and payload["n_processed"] == 2800


def test_complete_checkpoint_is_reconstructed_without_judge_calls(tmp_path: Path) -> None:
    ckpt = tmp_path / "P0a.checkpoint.json"
    _write(
        ckpt,
        n_processed=10000,
        n_total=10000,
        n_ok=9999,
        status_counts={"ok": 9999, "unparseable": 1},
        hand_ge1_rate=0.9544954495449545,
        hand_eq2_rate=0.8265826582658266,
        active_manipulation_rate=0.9127912791279128,
        total_cost_usd=4.4708462222222245,
        total_latency_ms=20118808,
    )

    kind, result = _resume_decision(ckpt, n_frames=10000)

    assert kind == "done"
    assert result is not None
    assert result["n_ok"] == 9999
    assert result["status_counts"] == {"ok": 9999, "unparseable": 1}
    assert result["hand_eq2_rate"] == pytest.approx(0.8265826582658266)
    # The 3 per-published-label agreement fields were never checkpointed -- lost, not faked.
    assert result["n_comparable_to_published"] is None
    assert result["hand_count_exact_agreement_rate"] is None
    assert result["active_labor_agreement_rate"] is None
    assert result["reconstructed_from_checkpoint"] is True


def test_checkpoint_for_a_different_n_is_rejected(tmp_path: Path) -> None:
    ckpt = tmp_path / "P0b.checkpoint.json"
    _write(ckpt, n_processed=500, n_total=10000)

    with pytest.raises(SystemExit):
        _resume_decision(ckpt, n_frames=20)
