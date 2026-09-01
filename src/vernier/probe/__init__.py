"""Result 2. Matched frozen-feature probes across corpora.

Matching on frame count, cluster count and training budget is enforced in code, not left to
the caller, because an unmatched comparison silently measures the sampling.

Kill-gate: a timeboxed spike at entry. If a matched three-corpus probe is not runnable within
the compute budget, Result 2 is dropped and Result 1 ships alone.
"""

from __future__ import annotations

from typing import Any, NamedTuple

from vernier.models import ProbeResult

MATCHED_ON = ("n_frames", "n_clusters", "training_steps")


class MatchedSpec(NamedTuple):
    n_frames: int
    n_clusters: int
    training_steps: int


def match_corpora(corpora: list[str]) -> MatchedSpec:
    """Compute the frame/cluster/training-step budget usable across all `corpora` simultaneously."""
    raise NotImplementedError


def kill_gate_check(spec: MatchedSpec, compute_budget: Any) -> bool:
    """Timeboxed spike: True iff a matched three-corpus probe is runnable within budget."""
    raise NotImplementedError


def run_probe(
    source_corpus: str,
    backbone: str,
    downstream: str,
    metric: str,
    spec: MatchedSpec,
    *,
    seed: int = 777,
) -> ProbeResult:
    raise NotImplementedError
