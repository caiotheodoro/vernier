"""Generate live Qwen3-VL comparison-judge labels over a real frame pool.

**Not the rung-1 distillation teacher** -- that is `scripts/generate_rung1_labels.py`, which
reads Build AI's own stored `gemini-2.5-flash` labels for free (`docs/review.md` R1,
`docs/DECISIONS.md` D047). This script exists for the OTHER real use of a live Qwen3-VL call at
scale: judge-vs-judge agreement (E4) and cross-corpus domain-bias (E6) need the live judge's
own answers on the same frames the stored labels cover, as a second, independent judge arm --
`docs/review.md`'s point 2: "the panel is two judges, not one... Qwen3-VL is the live comparison
judge."

Uses `scripts/judge_concurrency.py` for real wall-clock feasibility at scale: a sequential loop
at the per-frame latency observed in `scripts/e2_replication.py`'s smoke runs would take hours
for a training-pool-sized run. Real smoke testing this session found naive client-side
concurrency does NOT help throughput on this deployment (single-GPU contention dominates over
short bursts; `max_workers=1` was the empirically fastest tested option) -- `--max-workers`
defaults to 1 for that reason. Raise it only with real evidence it helps for the run size
attempted; see `docs/HANDOFF.md` for the concurrency smoke-test data.

**This is real spend, not a smoke test** at any N beyond a few frames -- `--n` exists to
smoke-test the path itself at small N; running at scale needs a separate, explicit decision,
same discipline as `scripts/e2_replication.py`/`scripts/e5_prompt_sweep.py`.

Requires `QWEN3VL_BASE_URL` pointed at a live, warm deployment (`cloud/modal_qwen3vl.py`).
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from pydantic import TypeAdapter

from judge_concurrency import judge_frames_concurrent

from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.models import FrameRef, JudgeResponse
from vernier.sampling.membership import load_membership

_MEMBERSHIP_ROOT = Path("data/membership")  # matches sampling/draw.py's own root; re-declared
# per D033's no-shared-file-edits convention, same as every other script this session.

_RESPONSE_LIST_ADAPTER = TypeAdapter(list[JudgeResponse])


def _frame_pool(sample: str, n: int | None) -> list[FrameRef]:
    frames = load_membership(sample, _MEMBERSHIP_ROOT)  # type: ignore[arg-type]
    return frames[:n] if n is not None else frames


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--sample",
        default="E10k-ego",
        choices=["E10k-ego", "E10k-ego4d", "E10k-epic"],
        help="which real, already-drawn sample to pull frames from",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=None,
        help="cap the pool to the first N frames (smoke-testing). Omit to run the full sample.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=1,
        help="real smoke data this session found >1 hurts throughput on this deployment; see module docstring",
    )
    parser.add_argument("--out", type=Path, default=Path("data/qwen_comparison_labels.json"))
    args = parser.parse_args(argv)

    pool = _frame_pool(args.sample, args.n)
    judge = Qwen3VLJudge()

    print(f"running {len(pool)} frames from {args.sample}, max_workers={args.max_workers}")
    start = time.monotonic()

    def _progress(done: int, total: int) -> None:
        if done % 50 == 0 or done == total:
            print(f"  {done}/{total} ({time.monotonic() - start:.0f}s elapsed)")

    responses = judge_frames_concurrent(
        pool, "P0b", judge, max_workers=args.max_workers, on_progress=_progress
    )
    elapsed_s = time.monotonic() - start

    status_counts: dict[str, int] = {}
    total_cost_usd = 0.0
    for r in responses:
        status_counts[r.status] = status_counts.get(r.status, 0) + 1
        total_cost_usd += r.cost_usd

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(_RESPONSE_LIST_ADAPTER.dump_json(responses))

    print(f"\nwrote {len(responses)} responses to {args.out}")
    print(f"status_counts: {status_counts}")
    print(f"total_cost_usd: {total_cost_usd:.4f}")
    print(f"wall_clock_s: {elapsed_s:.0f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
