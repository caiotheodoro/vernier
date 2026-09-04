"""Behavioural tests for `scripts/check_corpus_manifest.py`.

Pure: a manifest list in, a summary and a list of disagreements out. The real reconciliation
against the live artifact is `make check-corpus-manifest`, not duplicated here.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_corpus_manifest import (  # noqa: E402
    EXPECTED_SHARDS,
    PUBLISHED_FACTORIES,
    PUBLISHED_WORKERS,
    compare,
    summarize,
)


def _clip(factory: str, worker: str, shard: str, duration: float = 3600.0) -> dict[str, Any]:
    return {
        "shard": shard,
        "clip_id": f"{factory}_{worker}_{shard}",
        "factory_id": factory,
        "worker_id": worker,
        "duration_sec": duration,
    }


def test_workers_are_counted_as_factory_worker_pairs_not_bare_ids() -> None:
    """The corpus numbers workers within a factory, so `worker_001` exists in all 85. Counting
    bare ids would report 1 worker here instead of 2 -- the same collision that would have
    inflated H2's design effect had it reached the cluster ids (D071)."""
    manifest = [
        _clip("factory_001", "worker_001", "a.tar"),
        _clip("factory_002", "worker_001", "b.tar"),
    ]

    assert summarize(manifest)["workers"] == 2


def test_recorded_hours_sum_the_real_durations() -> None:
    manifest = [
        _clip("factory_001", "worker_001", "a.tar", duration=1800.0),
        _clip("factory_001", "worker_002", "b.tar", duration=5400.0),
    ]

    assert summarize(manifest)["recorded_hours"] == 2.0


def test_a_partial_scan_is_reported_as_a_mismatch_not_a_pass() -> None:
    """The failure mode this script exists to prevent: a half-built sampling frame silently
    treated as the corpus, which would make every S10k draw a draw from the alphabetically
    first factories only."""
    manifest = [_clip("factory_001", "worker_001", "a.tar")]

    problems = compare(summarize(manifest))

    assert any("workers" in p for p in problems)
    assert any("factories" in p for p in problems)
    assert any("shards" in p for p in problems)


def test_a_complete_manifest_reports_no_problems() -> None:
    # Built to exactly the published shape rather than approximated, so a pass here means the
    # comparison is satisfiable and not just permanently red.
    manifest: list[dict[str, Any]] = []
    worker_n = 0
    shard_n = 0
    for f in range(PUBLISHED_FACTORIES):
        for _ in range(PUBLISHED_WORKERS // PUBLISHED_FACTORIES):
            worker_n += 1
            shard_n += 1
            manifest.append(_clip(f"factory_{f:03d}", f"worker_{worker_n:04d}", f"s{shard_n}.tar"))
    while len({(c["factory_id"], c["worker_id"]) for c in manifest}) < PUBLISHED_WORKERS:
        worker_n += 1
        shard_n += 1
        manifest.append(_clip("factory_000", f"worker_{worker_n:04d}", f"s{shard_n}.tar"))
    while len({c["shard"] for c in manifest}) < EXPECTED_SHARDS:
        shard_n += 1
        manifest.append(_clip("factory_000", "worker_0001", f"s{shard_n}.tar"))

    assert compare(summarize(manifest)) == []
