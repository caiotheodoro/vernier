"""Judge test-retest (`docs/REVIEW.md` R4): does the live judge agree with itself?

The project measures a human's self-consistency (`R100`, intra-rater AC1) and had no analogue
for the machine. Post-training iron law 8: a served model is not deterministic across batch
compositions without batch-invariant inference, even at temperature 0 -- and
`judges/qwen3vl.py`'s `_call_qwen3vl` does not even set `temperature` explicitly, so the
server's own default sampling applies. Real stochastic variation across repeated identical
calls is expected; this measures how much.

**Smoke-scale, not R4's full form.** R4's natural target is the 600 gold frames (Wave 3, not
yet collected) -- this runs on a small, already-real, fixed frame set instead, same self-
authorized smoke-test discretion as `scripts/e2_replication.py`/`scripts/e5_prompt_sweep.py`.
Re-run against the real 600 once Wave 3 exists for the full R4 result.

Requires `QWEN3VL_BASE_URL` pointed at a live, warm deployment (`cloud/modal_qwen3vl.py`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vernier.judges.base import JudgeAdapter
from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.models import FrameRef
from vernier.sampling.draw import draw_sample

# Real completion-call settings this test-retest result is scoped to -- if any of these change,
# this result no longer describes the same judge configuration. `_call_qwen3vl` sets none of
# these explicitly beyond max_tokens/logprobs, so "temperature" here is genuinely "whatever the
# server defaults to," not a value this project chose -- itself part of the finding.
_JUDGE_CONFIG_NOTE = (
    "model=Qwen/Qwen3-VL-8B-Instruct-FP8 (FP8, Modal L4); vllm serve --max-model-len 8192, "
    "tensor-parallel-size 1; completion call sets max_tokens=64, logprobs=True; temperature, "
    "top_p, and seed are NOT set by this project's own client code, so the server's own default "
    "sampling behavior applies -- unpinned, and itself part of what this measures."
)


def _run_retest(frames: list[FrameRef], repeats: int, judge: JudgeAdapter) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for frame in frames:
        hand_counts = []
        manipulations = []
        statuses = []
        for _ in range(repeats):
            resp = judge.judge_frame(frame, "P0b")
            statuses.append(resp.status)
            hand_counts.append(resp.hands_visible)
            manipulations.append(resp.manipulation)
        results.append(
            {
                "frame_id": frame.frame_id,
                "statuses": statuses,
                "hand_counts": hand_counts,
                "manipulations": manipulations,
                "hand_count_unanimous": len(set(hand_counts)) == 1,
                "manipulation_unanimous": len(set(manipulations)) == 1,
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20, help="number of frames to test-retest")
    parser.add_argument("--repeats", type=int, default=3, help="calls per frame")
    parser.add_argument("--out", type=Path, default=Path("data/judge_test_retest.json"))
    args = parser.parse_args(argv)

    frames = draw_sample("E10k-ego")[: args.n]
    judge = Qwen3VLJudge()

    results = _run_retest(frames, args.repeats, judge)

    n_hand_unanimous = sum(1 for r in results if r["hand_count_unanimous"])
    n_manip_unanimous = sum(1 for r in results if r["manipulation_unanimous"])
    real_judge_rev = judge.judge_rev()

    output = {
        "n_frames": len(results),
        "repeats_per_frame": args.repeats,
        "judge_config": _JUDGE_CONFIG_NOTE,
        "judge_rev": real_judge_rev,
        "hand_count_self_agreement_rate": n_hand_unanimous / len(results) if results else 0.0,
        "manipulation_self_agreement_rate": n_manip_unanimous / len(results) if results else 0.0,
        "per_frame": results,
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2))
    print(json.dumps({k: v for k, v in output.items() if k != "per_frame"}, indent=2))
    print(f"\nwrote full per-frame detail to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
