"""E5 prompt-sweep runner (`docs/WAVES.md` Wave 2): H3, prompt sensitivity.

`docs/PRE-REGISTRATION.md` H3: the spread of the active-manipulation figure across its prompt
variant set (`P0b`, `P5`, `P6`) is `>=5pp`, and exceeds the spread of the `>=1 hand` figure
across its own variant set (`P0b`, `P1`, `P2`, `P3`, `P4`) -- reported as IPR/PAR (2604.16413).
Also checked: "P3 (gloves) alone moves the >=1-hand figure by >=2pp" against `P0b`.

`P7` (the confidence-schema addition) is excluded from both sweeps -- it doesn't reword the
task definition, it changes the output schema, so it isn't a "semantically equivalent but
linguistically varied" rewording in the sense H3/IPR-PAR mean.

**IPR/PAR here is a faithful-but-not-pinned construction**, the same flagged-not-guaranteed
treatment this project already gives P3/P4's prompt wording (`docs/PRE-REGISTRATION.md`'s own
table): `docs/SURVEY.md` excerpts the source paper (2604.16413) as "IPR = stability across
semantically equivalent but linguistically varied prompts; PAR its pairwise rate", without the
paper's exact formula in hand. Implemented here as, per frame with every swept variant `"ok"`:
IPR = 1 iff all variants agree (full-unanimity rate, averaged over frames); PAR = the fraction
of variant *pairs* that agree (averaged over frames) -- a stricter and a softer reliability
statistic respectively. Flagged in the output itself, not presented as a verified reproduction.

**Smoke-test discipline is load-bearing, not decorative** (see `scripts/e2_replication.py`):
`--n` defaults small. Do not pass a value anywhere near the pre-registered N without a
separate, explicit decision from Caio.

Requires `QWEN3VL_BASE_URL` pointed at a live, warm deployment (`cloud/modal_qwen3vl.py`).
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any, TextIO

from judge_responses_io import append_response, read_responses

from vernier.judges.base import JudgeAdapter
from vernier.judges.prompts import PromptVariant
from vernier.judges.qwen3vl import Qwen3VLJudge
from vernier.models import FrameRef
from vernier.sampling.draw import draw_sample

_HAND_COUNT_VARIANTS: tuple[PromptVariant, ...] = ("P0b", "P1", "P2", "P3", "P4")
_MANIPULATION_VARIANTS: tuple[PromptVariant, ...] = ("P0b", "P5", "P6")
_H3_SPREAD_TOLERANCE_PP = 5.0
_P3_GLOVE_TOLERANCE_PP = 2.0


def _rates_per_variant(
    frames: list[FrameRef],
    variants: tuple[PromptVariant, ...],
    judge: JudgeAdapter,
    *,
    answer: Any,
    checkpoint_path: Path | None = None,
    resume: bool = False,
    responses_path: Path | None = None,
) -> tuple[dict[str, float], dict[str, dict[str, Any]]]:
    """Run every variant against every frame; return (per-variant positive rate, per-frame
    per-variant answer -- the latter feeds `_ipr_par`, kept only for `"ok"` responses).

    Cost note: `judge_frame` always makes two real calls (hand_count + manipulation, combined
    into one `JudgeResponse` by design). Each sweep here only uses one task's half of that --
    real, known double-cost, not a bug -- so `len(frames) * len(variants)` calls to
    `judge_frame` here means `2x` that many real HTTP calls to the judge server.

    `checkpoint_path`, if given, is rewritten after each *variant* finishes with that variant's
    rate and per-frame answers. `resume=True` loads it first and skips any variant already
    recorded -- so a crash mid-sweep costs one variant's calls, not all of them (D054). The
    default (`None`) leaves the old behaviour and the old callers byte-for-byte unchanged.

    `responses_path`, if given, receives every `JudgeResponse` as one JSON line, appended
    before the `status != "ok"` guard below so refusals and unparseable answers are kept
    verbatim, never dropped (CONTRACTS.md rule 2; D069). The checkpoint above is per-variant,
    so on resume the file is rewritten to keep only lines whose `prompt_variant` is already in
    the checkpoint -- a partial variant's lines from the crashed attempt are discarded, since
    that variant is about to be re-judged in full -- and then appended to. A fresh run opens
    it with `"w"`.
    """
    rates: dict[str, float] = {}
    per_frame_answers: dict[str, dict[str, Any]] = {f.frame_id: {} for f in frames}

    saved: dict[str, dict[str, Any]] = {}
    if resume and checkpoint_path is not None and checkpoint_path.is_file():
        saved = json.loads(checkpoint_path.read_text())["variants"]
        for name, entry in saved.items():
            rates[name] = entry["rate"]
            for frame_id, value in entry["answers"].items():
                if frame_id in per_frame_answers:
                    per_frame_answers[frame_id][name] = value
        if saved:
            print(f"[e5] resuming: {sorted(saved)} already done, skipping", flush=True)

    fh: TextIO | None = None
    if responses_path is not None:
        if saved:
            kept = [r for r in read_responses(responses_path) if r.prompt_variant in saved]
            with responses_path.open("w") as rewrite:
                for r in kept:
                    append_response(rewrite, r)
            fh = responses_path.open("a")
        else:
            fh = responses_path.open("w")

    try:
        for variant in variants:
            if variant in saved:
                continue
            n_ok = 0
            n_positive = 0
            for frame in frames:
                resp = judge.judge_frame(frame, variant)
                if fh is not None:
                    append_response(fh, resp)
                if resp.status != "ok":
                    continue
                n_ok += 1
                value = answer(resp)
                if value:
                    n_positive += 1
                per_frame_answers[frame.frame_id][variant] = value
            rates[variant] = n_positive / n_ok if n_ok else 0.0

            if checkpoint_path is not None:
                saved[variant] = {
                    "rate": rates[variant],
                    "answers": {
                        fid: ans[variant] for fid, ans in per_frame_answers.items() if variant in ans
                    },
                }
                checkpoint_path.write_text(json.dumps({"variants": saved}, indent=2))
                print(f"[e5] {variant} done ({rates[variant]:.3f}), checkpointed", flush=True)
    finally:
        if fh is not None:
            fh.close()

    return rates, per_frame_answers


def _ipr_par(
    per_frame_answers: dict[str, dict[str, Any]], variants: tuple[PromptVariant, ...]
) -> dict[str, Any]:
    """See module docstring for the exact (flagged, not-pinned) operationalization."""
    complete_frames = [
        answers
        for answers in per_frame_answers.values()
        if all(v in answers for v in variants)
    ]
    if not complete_frames:
        return {"ipr": None, "par": None, "n_frames_with_all_variants_ok": 0}

    n_unanimous = 0
    pair_agreement_sum = 0.0
    pairs = list(itertools.combinations(variants, 2))
    for answers in complete_frames:
        values = [answers[v] for v in variants]
        n_unanimous += int(len(set(values)) == 1)
        agreeing_pairs = sum(1 for a, b in pairs if answers[a] == answers[b])
        pair_agreement_sum += agreeing_pairs / len(pairs)

    n = len(complete_frames)
    return {
        "ipr": n_unanimous / n,
        "par": pair_agreement_sum / n,
        "n_frames_with_all_variants_ok": n,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--n",
        type=int,
        default=5,
        help=(
            "number of E10k-ego frames to run (default 5, a smoke test -- each frame costs "
            "(len(hand-count variants) + len(manipulation variants)) x 2 real HTTP calls, so "
            "this multiplies faster than e2_replication.py's --n). Do NOT pass anything near "
            "the pre-registered N without a separate, explicit decision from Caio."
        ),
    )
    parser.add_argument("--out", type=Path, default=Path("data/e5_results.json"))
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip any prompt variant already recorded in the checkpoints next to --out (D054)",
    )
    args = parser.parse_args(argv)

    frames = draw_sample("E10k-ego")[: args.n]
    judge = Qwen3VLJudge()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    hand_ckpt = args.out.parent / f"{args.out.stem}.hand.checkpoint.json"
    manip_ckpt = args.out.parent / f"{args.out.stem}.manip.checkpoint.json"
    # D069: every per-frame JudgeResponse of each sweep lands next to its checkpoint, one JSON
    # line per call, so the rates below are re-derivable later without re-spending the calls.
    hand_responses = args.out.parent / f"{args.out.stem}.hand.responses.jsonl"
    manip_responses = args.out.parent / f"{args.out.stem}.manip.responses.jsonl"

    hand_rates, hand_answers = _rates_per_variant(
        frames,
        _HAND_COUNT_VARIANTS,
        judge,
        answer=lambda resp: resp.hands_visible is not None and resp.hands_visible >= 1,
        checkpoint_path=hand_ckpt,
        resume=args.resume,
        responses_path=hand_responses,
    )
    manip_rates, manip_answers = _rates_per_variant(
        frames,
        _MANIPULATION_VARIANTS,
        judge,
        answer=lambda resp: bool(resp.manipulation),
        checkpoint_path=manip_ckpt,
        resume=args.resume,
        responses_path=manip_responses,
    )

    hand_spread_pp = (max(hand_rates.values()) - min(hand_rates.values())) * 100
    manip_spread_pp = (max(manip_rates.values()) - min(manip_rates.values())) * 100
    p3_glove_diff_pp = abs(hand_rates["P3"] - hand_rates["P0b"]) * 100

    h3 = {
        "hand_count_spread_pp": hand_spread_pp,
        "manipulation_spread_pp": manip_spread_pp,
        "manipulation_spread_at_least_5pp": manip_spread_pp >= _H3_SPREAD_TOLERANCE_PP,
        "manipulation_spread_exceeds_hand_count_spread": manip_spread_pp > hand_spread_pp,
        "p3_glove_diff_pp": p3_glove_diff_pp,
        "p3_glove_moves_hand_count_by_at_least_2pp": p3_glove_diff_pp >= _P3_GLOVE_TOLERANCE_PP,
    }

    output = {
        "n_frames_requested": args.n,
        "n_frames_drawn": len(frames),
        "hand_count_rates_by_variant": hand_rates,
        "manipulation_rates_by_variant": manip_rates,
        "hand_count_ipr_par": _ipr_par(hand_answers, _HAND_COUNT_VARIANTS),
        "manipulation_ipr_par": _ipr_par(manip_answers, _MANIPULATION_VARIANTS),
        "H3": h3,
        "responses_paths": {"hand": str(hand_responses), "manip": str(manip_responses)},
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
