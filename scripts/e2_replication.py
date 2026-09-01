"""E2 replication runner (`docs/WAVES.md` Wave 2): the real H1/H1b comparison.

Per `docs/DECISIONS.md` D042, H1 is no longer a live replication of `gemini-2.5-flash` (that
model is deprecated for new API keys) -- it is a comparison between Build AI's own published,
per-frame labels (recorded directly in the evaluation parquet, F9) and a live call to the sole
self-hosted judge, `Qwen3VLJudge`, on the identical `E10k-ego` frames, under both P0 prompt arms.

`docs/PRE-REGISTRATION.md`'s three published headline figures for Egocentric-10K are
`>=1 hand` (96.42%), `2 hands` (76.34%), and `active manipulation` (91.66%). H1 asks whether
the live judge's own aggregate rates land within +-2pp of each; H1b asks whether P0a and P0b
disagree by >=1pp on the manipulation figure.

**Smoke-test discipline is load-bearing, not decorative**: `--n` defaults small. Do not pass a
value anywhere near the pre-registered N (10,000) without a separate, explicit decision from
Caio -- the approved reframe plan scoped this session to "deploy, smoke-test, report real
cost/latency," not a production run (`docs/HANDOFF.md`).

Requires `QWEN3VL_BASE_URL` pointed at a live, warm deployment (`cloud/modal_qwen3vl.py`).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.models import FrameRef
from vernier.sampling.draw import draw_sample
from vernier.sampling.revisions import PINNED_REVISIONS

_EVAL_HF_REPO = "builddotai/Egocentric-10K-Evaluation"

# docs/PRE-REGISTRATION.md's headline table, Egocentric-10K row.
_PUBLISHED = {
    "hand_ge1_rate": 0.9642,
    "hand_eq2_rate": 0.7634,
    "active_manipulation_rate": 0.9166,
}
_H1_TOLERANCE_PP = 2.0
_H1B_TOLERANCE_PP = 1.0


def _published_labels(frame_ids: set[str]) -> dict[str, tuple[int, bool]]:
    """Build AI's own recorded `hand_count`/`active_labor` for each real `frame_id`, read
    straight from the pinned evaluation parquet -- what H1 compares the live judge against,
    never treated as ground truth (a judge never decides ground truth, `CONTRACTS.md`)."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(
        repo_id=_EVAL_HF_REPO,
        repo_type="dataset",
        revision=PINNED_REVISIONS[_EVAL_HF_REPO],
        filename="egocentric_10k.parquet",
    )
    table = pq.read_table(path, columns=["frame_id", "hand_count", "active_labor"])
    out: dict[str, tuple[int, bool]] = {}
    for fid, hc, al in zip(
        table.column("frame_id").to_pylist(),
        table.column("hand_count").to_pylist(),
        table.column("active_labor").to_pylist(),
        strict=True,
    ):
        if fid in frame_ids:
            out[fid] = (hc, al == "yes")
    return out


def _run_variant(
    frames: list[FrameRef],
    variant: PromptVariant,
    judge: JudgeAdapter,
    published: dict[str, tuple[int, bool]],
) -> dict[str, Any]:
    n_ok = 0
    hand_ge1 = hand_eq2 = active_yes = 0
    hand_count_agree = active_labor_agree = 0
    n_comparable = 0  # ok AND a published label exists for this frame_id
    total_cost_usd = 0.0
    total_latency_ms = 0
    status_counts: dict[str, int] = {}

    for frame in frames:
        resp = judge.judge_frame(frame, variant)
        total_cost_usd += resp.cost_usd
        total_latency_ms += resp.latency_ms
        status_counts[resp.status] = status_counts.get(resp.status, 0) + 1
        if resp.status != "ok":
            continue
        n_ok += 1
        if resp.hands_visible is not None and resp.hands_visible >= 1:
            hand_ge1 += 1
        if resp.hands_visible == 2:
            hand_eq2 += 1
        if resp.manipulation:
            active_yes += 1

        label = published.get(frame.frame_id)
        if label is None:
            continue
        n_comparable += 1
        published_hand_count, published_active = label
        if resp.hands_visible == published_hand_count:
            hand_count_agree += 1
        if resp.manipulation == published_active:
            active_labor_agree += 1

    denom = n_ok or 1  # denominator excludes non-ok responses (CONTRACTS.md rule 2: absence
    # is explicit); n_ok == 0 makes every rate below vacuously 0.0, not a division error.
    comparable_denom = n_comparable or 1
    return {
        "n_total": len(frames),
        "n_ok": n_ok,
        "status_counts": status_counts,
        "hand_ge1_rate": hand_ge1 / denom,
        "hand_eq2_rate": hand_eq2 / denom,
        "active_manipulation_rate": active_yes / denom,
        # Per-frame agreement against Build AI's own published gemini-2.5-flash labels for the
        # identical frames -- a real, direct signal beyond H1's aggregate-level comparison,
        # not itself a hypothesis test (no pre-registered tolerance band exists for it).
        "n_comparable_to_published": n_comparable,
        "hand_count_exact_agreement_rate": hand_count_agree / comparable_denom,
        "active_labor_agreement_rate": active_labor_agree / comparable_denom,
        "total_cost_usd": total_cost_usd,
        "total_latency_ms": total_latency_ms,
    }


def _h1(results_p0a: dict[str, Any]) -> dict[str, Any]:
    h1: dict[str, Any] = {}
    for key, published in _PUBLISHED.items():
        observed = results_p0a[key]
        diff_pp = abs(observed - published) * 100
        h1[key] = {
            "published": published,
            "observed_P0a": observed,
            "diff_pp": diff_pp,
            "within_2pp_tolerance": diff_pp <= _H1_TOLERANCE_PP,
        }
    return h1


def _h1b(results_p0a: dict[str, Any], results_p0b: dict[str, Any]) -> dict[str, Any]:
    p0a_rate = results_p0a["active_manipulation_rate"]
    p0b_rate = results_p0b["active_manipulation_rate"]
    diff_pp = abs(p0a_rate - p0b_rate) * 100
    return {
        "p0a_active_manipulation_rate": p0a_rate,
        "p0b_active_manipulation_rate": p0b_rate,
        "diff_pp": diff_pp,
        "p0_variants_disagree": diff_pp >= _H1B_TOLERANCE_PP,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=20,
        help=(
            "number of E10k-ego frames to run (default 20, a smoke test). Do NOT pass "
            "anything near the pre-registered N=10,000 without a separate, explicit decision "
            "from Caio."
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("data/e2_results.json"))
    args = parser.parse_args(argv)

    frames = draw_sample("E10k-ego")[: args.n]
    published = _published_labels({f.frame_id for f in frames})
    judge = Qwen3VLJudge()

    results = {
        "P0a": _run_variant(frames, "P0a", judge, published),
        "P0b": _run_variant(frames, "P0b", judge, published),
    }

    output = {
        "n_frames_requested": args.n,
        "n_frames_drawn": len(frames),
        "n_published_labels_matched": len(published),
        "per_variant": results,
        "H1": _h1(results["P0a"]),
        "H1b": _h1b(results["P0a"], results["P0b"]),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
