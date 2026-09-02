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

from published_labels import published_labels_for_sample

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.models import FrameRef
from vernier.sampling.draw import draw_sample

# docs/PRE-REGISTRATION.md's headline table, Egocentric-10K row.
_PUBLISHED = {
    "hand_ge1_rate": 0.9642,
    "hand_eq2_rate": 0.7634,
    "active_manipulation_rate": 0.9166,
}
_H1_TOLERANCE_PP = 2.0
_H1B_TOLERANCE_PP = 1.0


def _run_variant(
    frames: list[FrameRef],
    variant: PromptVariant,
    judge: JudgeAdapter,
    published: dict[str, tuple[int, bool]],
    *,
    checkpoint_path: Path | None = None,
    checkpoint_every: int = 100,
    resume_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """`checkpoint_path`, if given, is overwritten with the running aggregate every
    `checkpoint_every` frames -- real insurance for a real, many-hour run: without it, an
    interruption anywhere before the loop's own final line loses every call made so far, since
    nothing here was written to disk until now. `None` (the default) keeps existing callers
    (smoke-scale runs, tests) byte-for-byte unchanged.

    `resume_state`, if given, is a prior checkpoint dict (as written by this function) to resume
    from: `frames` is skipped up to `resume_state["n_processed"]` and every running total starts
    from the checkpoint's own aggregates rather than zero. Real need, not speculative: D054's
    full-scale P0b run died at 2,800/10,000 on a transient server error, and re-running the first
    2,800 frames from scratch would silently re-spend real judge calls already paid for and
    already counted. Aggregate-only checkpoints cannot restore `n_comparable_to_published`,
    `hand_count_exact_agreement_rate`, or `active_labor_agreement_rate` exactly (those weren't
    part of the periodic checkpoint payload) -- resuming re-derives them from that point forward
    only, which is flagged in the final result via `resumed_from`.
    """
    n_ok = 0
    hand_ge1 = hand_eq2 = active_yes = 0
    hand_count_agree = active_labor_agree = 0
    n_comparable = 0  # ok AND a published label exists for this frame_id
    total_cost_usd = 0.0
    total_latency_ms = 0
    status_counts: dict[str, int] = {}
    start_index = 0

    if resume_state is not None:
        start_index = resume_state["n_processed"]
        n_ok = resume_state["n_ok"]
        status_counts = dict(resume_state["status_counts"])
        hand_ge1 = round(resume_state["hand_ge1_rate"] * (n_ok or 1))
        hand_eq2 = round(resume_state["hand_eq2_rate"] * (n_ok or 1))
        active_yes = round(resume_state["active_manipulation_rate"] * (n_ok or 1))
        total_cost_usd = resume_state["total_cost_usd"]
        total_latency_ms = resume_state["total_latency_ms"]
        print(
            f"[{variant}] resuming from checkpoint at {start_index}/{len(frames)} "
            f"(n_ok={n_ok}, cost so far=${total_cost_usd:.2f})",
            flush=True,
        )

    for i, frame in enumerate(frames[start_index:], start=start_index + 1):
        resp = judge.judge_frame(frame, variant)
        total_cost_usd += resp.cost_usd
        total_latency_ms += resp.latency_ms
        status_counts[resp.status] = status_counts.get(resp.status, 0) + 1
        if resp.status == "ok":
            n_ok += 1
            if resp.hands_visible is not None and resp.hands_visible >= 1:
                hand_ge1 += 1
            if resp.hands_visible == 2:
                hand_eq2 += 1
            if resp.manipulation:
                active_yes += 1

            label = published.get(frame.frame_id)
            if label is not None:
                n_comparable += 1
                published_hand_count, published_active = label
                if resp.hands_visible == published_hand_count:
                    hand_count_agree += 1
                if resp.manipulation == published_active:
                    active_labor_agree += 1

        if checkpoint_path is not None and (i % checkpoint_every == 0 or i == len(frames)):
            denom = n_ok or 1
            comparable_denom = n_comparable or 1
            checkpoint_path.write_text(
                json.dumps(
                    {
                        "n_processed": i,
                        "n_total": len(frames),
                        "n_ok": n_ok,
                        "status_counts": status_counts,
                        "hand_ge1_rate": hand_ge1 / denom,
                        "hand_eq2_rate": hand_eq2 / denom,
                        "active_manipulation_rate": active_yes / denom,
                        "total_cost_usd": total_cost_usd,
                        "total_latency_ms": total_latency_ms,
                    },
                    indent=2,
                )
            )
            print(f"[{variant}] {i}/{len(frames)} checkpointed", flush=True)

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


def _resume_decision(
    checkpoint_path: Path, n_frames: int
) -> tuple[str, dict[str, Any] | None]:
    """Given a per-variant checkpoint path and the frame count the current run is scoped to,
    decide how `main()` should treat it under `--resume`:

    - `("fresh", None)` -- no checkpoint on disk, run the variant from zero.
    - `("resume", <checkpoint dict>)` -- a partial checkpoint; hand it to `_run_variant` as
      `resume_state` so only `frames[n_processed:]` are judged.
    - `("done", <reconstructed result dict>)` -- a complete checkpoint (`n_processed >=
      n_total`); rebuild the result with no judge calls at all. The 3 per-published-label
      agreement fields were never part of the periodic checkpoint payload, so they come back
      `None` with a `reconstructed_from_checkpoint` marker -- lost, not fabricated (D054).

    Exits nonzero if the checkpoint was written for a different `n_total` than this run's
    `n_frames` -- resuming a 10,000-frame run as a 20-frame smoke test (or vice versa) would
    silently mean something other than what the operator asked for.
    """
    if not checkpoint_path.is_file():
        return "fresh", None

    ckpt = json.loads(checkpoint_path.read_text())
    if ckpt["n_total"] != n_frames:
        sys.exit(
            f"{checkpoint_path.name}: checkpoint is for n_total={ckpt['n_total']}, but this "
            f"run is scoped to --n {n_frames}. Refusing to resume across a different frame count."
        )

    if ckpt["n_processed"] >= ckpt["n_total"]:
        return "done", {
            "n_total": ckpt["n_total"],
            "n_ok": ckpt["n_ok"],
            "status_counts": ckpt["status_counts"],
            "hand_ge1_rate": ckpt["hand_ge1_rate"],
            "hand_eq2_rate": ckpt["hand_eq2_rate"],
            "active_manipulation_rate": ckpt["active_manipulation_rate"],
            "n_comparable_to_published": None,
            "hand_count_exact_agreement_rate": None,
            "active_labor_agreement_rate": None,
            "total_cost_usd": ckpt["total_cost_usd"],
            "total_latency_ms": ckpt["total_latency_ms"],
            "reconstructed_from_checkpoint": True,
        }

    return "resume", ckpt


def _variant_result(
    frames: list[FrameRef],
    variant: PromptVariant,
    judge: JudgeAdapter,
    published: dict[str, tuple[int, bool]],
    *,
    checkpoint_path: Path,
    checkpoint_every: int,
    resume: bool,
) -> dict[str, Any]:
    """Run (or resume, or reconstruct) one prompt variant. Without `--resume` this is a plain
    `_run_variant` call; with it, `_resume_decision` picks the path."""
    if resume:
        kind, payload = _resume_decision(checkpoint_path, len(frames))
        if kind == "done":
            assert payload is not None
            print(f"[{variant}] complete checkpoint found -- reconstructed, no judge calls", flush=True)
            return payload
        resume_state = payload if kind == "resume" else None
    else:
        resume_state = None

    return _run_variant(
        frames,
        variant,
        judge,
        published,
        checkpoint_path=checkpoint_path,
        checkpoint_every=checkpoint_every,
        resume_state=resume_state,
    )


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
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=100,
        help="write a running-aggregate checkpoint every N frames (real insurance for a long run)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "continue from any per-variant checkpoints next to --out: a complete one is "
            "reconstructed with no judge calls, a partial one resumes from its last frame "
            "(docs/DECISIONS.md D054)."
        ),
    )
    args = parser.parse_args(argv)

    frames = draw_sample("E10k-ego")[: args.n]
    published = published_labels_for_sample("E10k-ego", {f.frame_id for f in frames})
    judge = Qwen3VLJudge()

    checkpoint_dir = args.out.parent
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    variants: tuple[PromptVariant, ...] = ("P0a", "P0b")
    results = {
        variant: _variant_result(
            frames,
            variant,
            judge,
            published,
            checkpoint_path=checkpoint_dir / f"{args.out.stem}.{variant}.checkpoint.json",
            checkpoint_every=args.checkpoint_every,
            resume=args.resume,
        )
        for variant in variants
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
