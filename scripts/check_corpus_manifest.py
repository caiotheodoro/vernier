"""Reconcile `data/corpus_manifest_10k.jsonl` against Build AI's own published corpus figures.

`docs/ETHICS.md`, from the vendor's dataset cards: *"10,000 hours of egocentric video from
2,153 workers across 85 factories (Egocentric-10K)"*. The manifest D071's scan builds is the
sampling frame `S10k-U`/`S10k-S` draw from, so if it disagrees with those numbers, either the
scan is incomplete, the scan is wrong, or the published figure is -- and each of those needs a
different response.

The same shape as `scripts/check_eval_parquets.py` (D016): a real, cheap check against a real
artifact, wired into a `make` target, run before anything downstream trusts the file.

**A mismatch here is a finding, not automatically a bug.** `docs/UPSTREAM-FINDINGS.md` already
records F9/F10, two places where the released artifacts disagree with their own documentation.
If the worker or factory count is off, that goes there with the real numbers on both sides --
it does not get quietly reconciled by adjusting what this script expects.

Exit status is 1 on any mismatch so `make` fails loudly rather than printing into a scroll.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# From docs/ETHICS.md, which sources them from the vendor's own dataset cards. Not derived
# from the manifest -- that would make this check vacuous.
PUBLISHED_WORKERS = 2153
PUBLISHED_FACTORIES = 85
PUBLISHED_HOURS = 10_000

# The scan's own denominator, live-resolved at scan time and recorded in
# docs/upstream/PROVENANCE-10k-raw.json.
EXPECTED_SHARDS = 19_495


def summarize(manifest: list[dict[str, Any]]) -> dict[str, Any]:
    """Counts the published figures can be compared against.

    Workers are counted as `(factory_id, worker_id)` pairs, never bare `worker_id`: the corpus
    numbers workers within a factory, so `worker_001` exists in all 85 of them and the bare
    count is meaningless (D071 -- the same collision that would have inflated H2's design
    effect had it reached the cluster ids).
    """
    workers = {(c["factory_id"], c["worker_id"]) for c in manifest}
    return {
        "clips": len(manifest),
        "shards": len({c["shard"] for c in manifest}),
        "factories": len({c["factory_id"] for c in manifest}),
        "workers": len(workers),
        "recorded_hours": sum(float(c["duration_sec"]) for c in manifest) / 3600.0,
    }


def compare(summary: dict[str, Any]) -> list[str]:
    """Every disagreement with the published figures, as human-readable lines. Empty is a pass."""
    problems: list[str] = []
    if summary["factories"] != PUBLISHED_FACTORIES:
        problems.append(
            f"factories: manifest {summary['factories']}, published {PUBLISHED_FACTORIES}"
        )
    if summary["workers"] != PUBLISHED_WORKERS:
        problems.append(f"workers: manifest {summary['workers']}, published {PUBLISHED_WORKERS}")
    if summary["shards"] != EXPECTED_SHARDS:
        problems.append(
            f"shards with at least one clip: {summary['shards']}, repo holds {EXPECTED_SHARDS} "
            "(a shard contributing no clip means its sidecar was missing or unparsed)"
        )
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("data/corpus_manifest_10k.jsonl"))
    args = parser.parse_args(argv)

    if not args.manifest.exists():
        print(
            f"check-corpus-manifest: {args.manifest} not built yet -- "
            "`python3 scripts/build_corpus_manifest.py --limit 0`",
            file=sys.stderr,
        )
        return 1

    with args.manifest.open() as handle:
        manifest = [json.loads(line) for line in handle if line.strip()]

    summary = summarize(manifest)
    print(json.dumps(summary, indent=2))
    print(
        f"published (docs/ETHICS.md): {PUBLISHED_WORKERS} workers, "
        f"{PUBLISHED_FACTORIES} factories, ~{PUBLISHED_HOURS} hours"
    )

    problems = compare(summary)
    if problems:
        print("\ncheck-corpus-manifest: MISMATCH against the published figures:", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nIf the scan is complete, this is an upstream finding and belongs in "
            "docs/UPSTREAM-FINDINGS.md with both numbers -- not a reason to change what this "
            "script expects.",
            file=sys.stderr,
        )
        return 1

    print("\ncheck-corpus-manifest: manifest agrees with the published corpus figures")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
