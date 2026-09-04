"""H2: the design effect over `worker_id`, measured on `S10k-U` and `S10k-S`.

`docs/PRE-REGISTRATION.md`: *"H2 -- Design effect >= 2, measured on `S10k-U` and `S10k-S`.
Cluster-bootstrap intervals over `worker_id` are at least twice the width of the corresponding
iid intervals."* This is the runner for that, and the first thing in the project ever to call
`estimation.bootstrap.cluster_bootstrap_ci` with a non-`None` `cluster_ids` -- every interval
in `MEASUREMENT_CARD.json` today is `method="iid"` because no arm had a grouping variable.
D071's adapter is what supplies one.

**Not `scripts/e2_replication.py`.** That runner compares the judge against Build AI's own
published labels, and `S10k-*` frames have none -- they are vernier's own draw from the raw
corpus, deliberately outside the evaluation release. H2 does not need published labels: the
design effect is a property of how the judge's answers cluster by worker, whatever those
answers are. Running this through E2 would have forced a comparison that does not exist.

**What a null result means here.** ~10,000 frames over ~2,144 workers is ~4.7 frames per
worker, so `deff ~= 1 + (m - 1) * ICC` needs an ICC around 0.27 to clear the pre-registered
threshold of 2 -- except cluster sizes are highly unequal (workers differ in recorded hours by
orders of magnitude), which inflates `deff` on its own. Both effects are real and neither is
known in advance. A `deff` below 2 is a real, reportable negative, and per `AGENTS.md` rule 1
it is reported as one and not investigated until it goes away. `cluster_size_summary` is
emitted alongside every figure precisely so the number can be read rather than just quoted.

Usage:
    python3 scripts/h2_design_effect.py --sample S10k-U --n 20     # smoke, the default
    python3 scripts/h2_design_effect.py --sample S10k-U --n 10000  # only on an explicit call
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

from vernier.estimation.bootstrap import (
    CLUSTER_BOOTSTRAP_B,
    CLUSTER_BOOTSTRAP_SEED,
    cluster_bootstrap_ci,
    design_effect,
)
from vernier.models import FrameRef, JudgeResponse

# The three published headline figures, in the same shape `scripts/e2_replication.py` uses so
# the two runners cannot silently disagree about what "the 2-hands figure" means.
HEADLINE_TASKS = ("hand_ge1", "hand_eq2", "active_manipulation")

# H2's pre-registered threshold. Kept as a named constant so the comparison is one place and
# the card cannot drift from the runner.
H2_THRESHOLD = 2.0


def outcomes_from_responses(
    responses: list[JudgeResponse],
) -> tuple[dict[str, list[float]], list[str]]:
    """Per-frame 0/1 outcomes for each headline task, plus the `frame_id`s kept.

    Only `status == "ok"` responses contribute. A refusal counted as a negative would inflate
    every rate here, which is precisely the class of error `CONTRACTS.md` rule 2 exists to
    forbid ("silently dropping it inflates agreement, and that is exactly the class of error
    vernier exists to catch"). The caller aligns cluster ids to `kept`, never to `responses`.
    """
    outcomes: dict[str, list[float]] = {task: [] for task in HEADLINE_TASKS}
    kept: list[str] = []
    for response in responses:
        if response.status != "ok" or response.hands_visible is None:
            continue
        if response.manipulation is None:
            continue
        kept.append(response.frame_id)
        outcomes["hand_ge1"].append(float(response.hands_visible >= 1))
        outcomes["hand_eq2"].append(float(response.hands_visible == 2))
        outcomes["active_manipulation"].append(float(response.manipulation))
    return outcomes, kept


def cluster_size_summary(cluster_ids: list[str]) -> dict[str, Any]:
    """Shape of the clustering, which a design effect cannot be read without.

    Unequal cluster sizes inflate `deff` independently of the intra-cluster correlation, so a
    `deff` quoted without the size spread is not interpretable -- it could be a real
    within-worker correlation or just a few workers dominating the sample.
    """
    sizes: dict[str, int] = {}
    for cluster in cluster_ids:
        sizes[cluster] = sizes.get(cluster, 0) + 1
    if not sizes:
        return {
            "n_clusters": 0,
            "n_observations": 0,
            "mean_cluster_size": None,
            "min_cluster_size": None,
            "max_cluster_size": None,
        }
    counts = list(sizes.values())
    return {
        "n_clusters": len(counts),
        "n_observations": sum(counts),
        "mean_cluster_size": sum(counts) / len(counts),
        "min_cluster_size": min(counts),
        "max_cluster_size": max(counts),
    }


def design_effects(
    outcomes: dict[str, list[float]],
    cluster_ids: list[str],
    *,
    B: int = CLUSTER_BOOTSTRAP_B,
    seed: int = CLUSTER_BOOTSTRAP_SEED,
) -> dict[str, dict[str, Any]]:
    """Both intervals and their ratio, per task.

    The iid arm is computed and kept, never discarded: `CONTRACTS.md` requires it be shown
    beside the clustered one and labelled a lower bound on width, which is also the only way
    the design effect is visible rather than merely asserted.
    """
    results: dict[str, dict[str, Any]] = {}
    for task, values in outcomes.items():
        if not values or not cluster_ids:
            results[task] = {
                "iid": None,
                "cluster": None,
                "design_effect": None,
                "why_absent": "no ok-status judge responses for this task",
            }
            continue
        iid = cluster_bootstrap_ci(values, None, B=B, seed=seed)
        clustered = cluster_bootstrap_ci(values, cluster_ids, B=B, seed=seed)
        results[task] = {
            "point_estimate": sum(values) / len(values),
            "iid": iid.model_dump(mode="json"),
            "cluster": clustered.model_dump(mode="json"),
            "design_effect": design_effect(clustered, iid),
            "why_absent": None,
        }
    return results


def _judge_all(
    frames: list[FrameRef], responses_path: Path, checkpoint_every: int = 25
) -> list[JudgeResponse]:
    """Judge every frame under `P0a`, appending each response as it lands.

    Resumable by the same reasoning as D069: the run is hours long and the frames it judges
    each cost a real video decode as well as a real judge call, so losing the lot to an
    interruption means re-spending both.
    """
    from judge_responses_io import append_response, read_responses

    from vernier.judges.qwen3vl import Qwen3VLJudge

    responses = read_responses(responses_path)
    done = {r.frame_id for r in responses}
    if done:
        print(f"  resuming: {len(done)} frames already judged", flush=True)

    judge = Qwen3VLJudge()
    started = time.time()
    pending = [f for f in frames if f.frame_id not in done]
    # Appended open, flushed per line by `append_response`: a crash loses at most the call in
    # flight, and every frame here cost a real video decode as well as a real judge call.
    with responses_path.open("a") as handle:
        for i, frame in enumerate(pending, start=1):
            response = judge.judge_frame(frame, "P0a")
            append_response(handle, response)
            responses.append(response)
            if i % checkpoint_every != 0:
                continue
            rate = i / max(time.time() - started, 1e-9)
            print(
                f"  {i}/{len(pending)} judged, {rate:.2f} frames/s, "
                f"~{(len(pending) - i) / max(rate, 1e-9) / 60:.0f} min left",
                flush=True,
            )
    return responses


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", default="S10k-U", choices=["S10k-U", "S10k-S"])
    parser.add_argument(
        "--n",
        type=int,
        default=20,
        help="frames to judge; small by default on purpose. The pre-registered N is 10,000 per "
        "arm -- passing it is a separate, explicit decision, and the smoke run is what has "
        "twice caught real bugs in this repo (D066, D067).",
    )
    parser.add_argument("--out", type=Path, default=Path("data/h2_design_effect.json"))
    parser.add_argument("--B", type=int, default=CLUSTER_BOOTSTRAP_B)
    args = parser.parse_args(argv)

    from vernier.sampling.draw import draw_sample

    frames = draw_sample(args.sample)[: args.n]
    by_id = {f.frame_id: f for f in frames}
    print(f"{args.sample}: {len(frames)} frames, {len({f.worker_id for f in frames})} workers", flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    responses_path = args.out.with_suffix(f".{args.sample}.responses.jsonl")
    responses = _judge_all(frames, responses_path)

    outcomes, kept = outcomes_from_responses(responses)
    # Cluster ids are aligned to `kept`, not to `frames`: a refused response drops its frame
    # from every task, and a misaligned cluster id would attribute an outcome to the wrong
    # worker -- silently, and in the direction that changes the answer.
    cluster_ids = [str(by_id[fid].worker_id) for fid in kept]

    result: dict[str, Any] = {
        "sample": args.sample,
        "prompt_variant": "P0a",
        "n_frames_drawn": len(frames),
        "n_responses": len(responses),
        "n_ok": len(kept),
        "B": args.B,
        "seed": CLUSTER_BOOTSTRAP_SEED,
        "cluster_by": "worker_id",
        "clusters": cluster_size_summary(cluster_ids),
        "h2_threshold": H2_THRESHOLD,
        "tasks": design_effects(outcomes, cluster_ids, B=args.B, seed=CLUSTER_BOOTSTRAP_SEED),
    }
    effects = [t["design_effect"] for t in result["tasks"].values() if t["design_effect"] is not None]
    # H2 is a claim about the design effect being >= 2. Recorded as computed, whichever way it
    # lands -- AGENTS.md rule 1: a result is reported, not investigated until it goes away.
    result["h2_holds"] = bool(effects) and all(e >= H2_THRESHOLD for e in effects)
    result["design_effect_min"] = min(effects) if effects else None
    result["design_effect_max"] = max(effects) if effects else None

    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "tasks"}, indent=2))
    for task, block in result["tasks"].items():
        print(f"  {task}: deff={block['design_effect']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
