"""Real live-judge run over the three `G200-*` gold sets (Wave 4 prerequisite).

E2 (`e2_replication.py`) and E5 (`e5_prompt_sweep.py`) never judged `G200-ego`/`G200-ego4d`/
`G200-epic` themselves -- E2 covered only `E10k-ego`, E5 only `P2k`. `G200-ego4d`/`G200-epic`
are subsets of `E10k-ego4d`/`E10k-epic`, neither of which any prior run touched at all; even
`G200-ego` (a subset of `P2k`) can't reuse E5's checkpoints, since those only ever stored a
derived boolean per task, not the full `hands_visible` integer H4/PPI need.

This script judges all three `G200-*` sets (200 frames each, 600 total) under `P0b`, persisting
one real, complete `JudgeResponse` per frame -- not just aggregates, unlike `e2_replication.py`
-- since Wave 4's AC1/PPI computation needs the actual per-frame predictions. `R100` needs no
separate run: it's drawn from the union of the three `G200-*` sets (`PRE-REGISTRATION.md`), so
judging all 600 already covers every possible `R100` frame.

Real, cheap, and fast relative to E2/E5's full-N runs: 600 frames x 2 calls each x ~0.9s/call
(the observed E2 rate) is ~18 minutes, ~$0.05. D054/D055's retry/backoff and checkpoint/resume
hardening applies unchanged (same `Qwen3VLJudge`).

Requires `QWEN3VL_BASE_URL` pointed at a live, warm deployment (`cloud/modal_qwen3vl.py`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.sampling.draw import SampleName, draw_sample

_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")
_VARIANT: PromptVariant = "P0b"


def _judge_sample(
    sample: SampleName,
    judge: JudgeAdapter,
    *,
    checkpoint_path: Path,
    checkpoint_every: int = 25,
) -> list[dict[str, Any]]:
    """Judge every frame in `sample` under `_VARIANT`, returning one real `JudgeResponse.model_dump`
    per frame. Resumes from `checkpoint_path` if it already holds real records for this sample."""
    frames = draw_sample(sample)
    done: dict[str, dict[str, Any]] = {}
    if checkpoint_path.is_file():
        for record in json.loads(checkpoint_path.read_text()):
            done[record["frame_id"]] = record

    for i, frame in enumerate(frames, start=1):
        if frame.frame_id in done:
            continue
        response = judge.judge_frame(frame, _VARIANT)
        done[frame.frame_id] = response.model_dump(mode="json")
        if i % checkpoint_every == 0 or i == len(frames):
            checkpoint_path.write_text(json.dumps(list(done.values()), indent=2))
            print(f"[{sample}] {i}/{len(frames)} checkpointed", flush=True)

    return list(done.values())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=Path("data/gold_judged"))
    args = parser.parse_args(argv)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    judge = Qwen3VLJudge()

    output: dict[str, list[dict[str, Any]]] = {}
    for sample in _SAMPLES:
        checkpoint_path = args.out_dir / f"{sample}.P0b.json"
        output[sample] = _judge_sample(sample, judge, checkpoint_path=checkpoint_path)

    print(json.dumps({s: len(r) for s, r in output.items()}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
