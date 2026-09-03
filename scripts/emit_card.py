"""Emit vernier's real `MeasurementCard` for its current actual state.

This is not a demo or a synthetic fixture: every `Claim` and `UncheckedItem` here reflects
what has and has not actually been run, as of this commit. H8 is pre-registered as
"computable from public participant counts before a single frame is labelled, and reported
first for that reason" (`PRE-REGISTRATION.md`) -- it is the one hypothesis with a real claim
today.

**Refreshed post-full-N-run (`docs/DECISIONS.md` D054/D055)** -- `scripts/e2_replication.py`
(H1/H1b) and `scripts/e5_prompt_sweep.py` (H3) have now both completed for real at the
pre-registered scale (N=10,000 and N=2,000/8 prompt-variant-passes respectively), against the
live, deployed Qwen3-VL judge. H1, H1b, and H3 are therefore real, checked findings now --
`_h1_h1b_claims()`/`_h3_claim()` below, sourced directly from `data/e2_full_n10000.json` and
`data/e5_full_n2000.json` (gitignored, real artifacts). Neither hypothesis is claimed as a
`PrevalenceEstimate` record: both are pre-registered as bare point-estimate comparisons against
either a published figure or another prompt variant's own point estimate, with no confidence
interval in their pre-registered definition (`PRE-REGISTRATION.md`'s own H1/H1b/H3 text), so
`record_type` here is a descriptive tag, not `"PrevalenceEstimate"` -- `_derive_verdict` never
tries to match these against `prevalence_estimates` (still `[]`; that machinery is real Wave 4
work, gated on Wave 3's human labels for the PPI-corrected estimates this project actually
intends to publish).

H2, H4, H5, H6, H7, and Result 2 all remain named as unmet, each with a `"BLOCKER:"`-prefixed
reason (`docs/DECISIONS.md` D038) describing the REAL current blocker, not a stale one --
ensuring `_derive_verdict` returns `NOT_VERIFIED`, not a vacuous `VERIFIED` from having zero
prevalence estimates to fail to claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from vernier.card import build_card, emit_card, verify_and_exit
from vernier.estimation.disparity import participant_count_disparity
from vernier.models import Claim, UncheckedItem

_ROOT = Path(__file__).resolve().parent.parent
_E2_RESULTS_PATH = _ROOT / "data" / "e2_full_n10000.json"
_E5_RESULTS_PATH = _ROOT / "data" / "e5_full_n2000.json"
_E2_RESULTS_REF = "data/e2_full_n10000.json"
_E5_RESULTS_REF = "data/e5_full_n2000.json"

# docs/BENCHMARK.md R0 / docs/DECISIONS.md D024's corrected counts.
_REAL_PARTICIPANT_COUNTS = {
    "egocentric-10k": 2153,
    "ego4d": 923,
    "epic-kitchens-100": 37,
}


def _h8_claim() -> Claim:
    disparity = participant_count_disparity(_REAL_PARTICIPANT_COUNTS)
    spread = max(disparity.values()) / min(disparity.values())
    return Claim(
        statement=(
            f"H8: participant counts differ by {spread:.1f}x across the three corpora "
            f"({disparity}) -- 'equal frame counts' does not mean equal precision. Computable "
            "from public participant counts alone, per PRE-REGISTRATION.md."
        ),
        record_type="ParticipantCountDisparity",
        record_ref="estimation.disparity.participant_count_disparity(2153/923/37)",
    )


def _h1_h1b_claims() -> list[Claim]:
    """Real, checked findings from the full-N (10,000) `e2_replication.py` run (D054/D055).

    Both hypotheses are pre-registered as bare point-estimate comparisons -- H1 against Build
    AI's own published figures, H1b between the two P0 prompt arms -- with no confidence
    interval in their pre-registered definition, so these are reported as-is, not wrapped in a
    `PrevalenceEstimate`. H1's pre-registered criterion is that ALL three figures land within
    +/-2pp; the honest reading of a 2-of-3 result is that the hypothesis as stated does not
    hold, not that it "mostly" holds -- PRE-REGISTRATION.md's own words: "Outside that band is
    a replication failure, reported as one."
    """
    e2 = json.loads(_E2_RESULTS_PATH.read_text())
    h1 = e2["H1"]
    h1b = e2["H1b"]
    all_within_tolerance = all(v["within_2pp_tolerance"] for v in h1.values())
    failing = [k for k, v in h1.items() if not v["within_2pp_tolerance"]]
    h1_statement = (
        "H1 (D042 reframe: live Qwen3-VL judge vs. Build AI's own published figures, "
        f"P0a, N={e2['per_variant']['P0a']['n_total']}): "
        + "; ".join(
            f"{k} observed {v['observed_P0a']:.4f} vs published {v['published']:.4f} "
            f"(diff {v['diff_pp']:.2f}pp, {'within' if v['within_2pp_tolerance'] else 'OUTSIDE'} "
            "+/-2pp)"
            for k, v in h1.items()
        )
        + f". Pre-registered criterion is ALL THREE within tolerance; {len(failing)}/3 is not "
        + f"({', '.join(failing)}). Per PRE-REGISTRATION.md's own rule, H1 as stated does "
        + ("hold." if all_within_tolerance else "NOT hold: this is a replication failure.")
    )
    h1b_statement = (
        f"H1b (N={e2['per_variant']['P0b']['n_total']} each arm): P0a active-manipulation rate "
        f"{h1b['p0a_active_manipulation_rate']:.4f} vs P0b {h1b['p0b_active_manipulation_rate']:.4f}, "
        f"diff {h1b['diff_pp']:.2f}pp. Pre-registered threshold is >=1pp disagreement; "
        f"{'met' if h1b['p0_variants_disagree'] else 'not met'} -- H1b is "
        + ("real: the prompt variants disagree." if h1b["p0_variants_disagree"] else "null.")
    )
    return [
        Claim(statement=h1_statement, record_type="E2Comparison", record_ref=f"{_E2_RESULTS_REF}#H1"),
        Claim(statement=h1b_statement, record_type="E2Comparison", record_ref=f"{_E2_RESULTS_REF}#H1b"),
    ]


def _h3_claim() -> Claim:
    """Real, checked finding from the full-N (2,000/8 variant-passes) `e5_prompt_sweep.py` run
    (D054/D055). Pre-registered as a bare spread comparison, no confidence interval, so reported
    as-is rather than as a `PrevalenceEstimate`."""
    e5 = json.loads(_E5_RESULTS_PATH.read_text())
    h3 = e5["H3"]
    spread_met = h3["manipulation_spread_at_least_5pp"]
    exceeds = h3["manipulation_spread_exceeds_hand_count_spread"]
    prediction_supported = spread_met and exceeds
    magnitude_clause = (
        f"clears the pre-registered floor ({h3['manipulation_spread_pp']:.2f}pp >= 5pp)"
        if spread_met
        else f"does not clear the pre-registered floor ({h3['manipulation_spread_pp']:.2f}pp < 5pp)"
    )
    direction_clause = (
        f"holds ({h3['manipulation_spread_pp']:.2f}pp > {h3['hand_count_spread_pp']:.2f}pp)"
        if exceeds
        else f"does not hold ({h3['manipulation_spread_pp']:.2f}pp <= {h3['hand_count_spread_pp']:.2f}pp)"
    )
    statement = (
        f"H3 (N={e5['n_frames_drawn']} per variant): hand-count spread across 5 prompt variants "
        f"{h3['hand_count_spread_pp']:.2f}pp; manipulation spread across 3 variants "
        f"{h3['manipulation_spread_pp']:.2f}pp. Pre-registered criterion is manipulation spread "
        f">=5pp AND exceeding the hand-count spread. The direction {direction_clause}; the "
        f"magnitude {magnitude_clause} -- H3's headline prediction is "
        + ("supported" if prediction_supported else "not supported")
        + " at this judge/prompt set. "
        f"Also checked: P3 (gloves) alone moves the hand-count figure by "
        f"{h3['p3_glove_diff_pp']:.2f}pp against a pre-registered >=2pp threshold -- "
        + ("met." if h3["p3_glove_moves_hand_count_by_at_least_2pp"] else "not met.")
    )
    return Claim(statement=statement, record_type="E5PromptSweep", record_ref=f"{_E5_RESULTS_REF}#H3")


def _unmet_claims() -> list[UncheckedItem]:
    # H2/Result 2's blocker is no longer "credentials not configured" -- HF_TOKEN *is*
    # configured and does authenticate; the account is simply not on the gated dataset's
    # authorized list (docs/DECISIONS.md D044), a real, checked, outstanding access gap, and
    # the corpus turned out to be WebDataset tar shards, not a parquet -- a materially bigger
    # adapter to build even once access exists.
    gated_corpus = (
        "BLOCKER: requires the raw, gated Egocentric-10K corpus (S10k-U/S10k-S). HF_TOKEN is "
        "configured and authenticates, but this account is confirmed NOT authorized for this "
        "specific gated dataset (docs/DECISIONS.md D044, live 403 GatedRepoError) -- Caio "
        "needs to request/confirm access, or say this arm is out of scope. The corpus is also "
        "WebDataset tar shards, not a parquet -- its real adapter is unwired regardless"
    )
    # H4/H5/H6/H7's blocker is now purely the human labelling itself -- the tool that will
    # produce it is real and ready (labels/tool.py's _pending_frames, docs/HANDOFF.md), and the
    # frame pools it draws from (G200-ego/G200-ego4d/G200-epic, R100) are already drawn and
    # persisted (scripts/draw_all_samples.py). Nothing left to build; only labelling to do.
    human_gold = (
        "BLOCKER: requires the 600 primary + 100 retest human labels (Wave 3), not yet "
        "collected. The labelling tool itself is real and ready -- next_frame()/record_label() "
        "wired against real, already-drawn sample membership -- this is purely Caio's own "
        "manual labelling work remaining, not an engineering gap"
    )
    return [
        UncheckedItem(
            item="H2 -- cluster-bootstrap design effect >=2 on S10k-U/S10k-S",
            reason=gated_corpus,
        ),
        UncheckedItem(
            item="H4 -- AC1(judge, human) higher for hand-count than manipulation",
            reason=human_gold,
        ),
        UncheckedItem(
            item="H5 -- domain-bias judge error rate differs >=5pp, Egocentric vs EPIC-KITCHENS-100",
            reason=human_gold,
        ),
        UncheckedItem(
            item="H6 -- distilled instrument holds >=0.80 agreement floor at >=0.70 coverage",
            reason=f"{human_gold} (training targets are judge labels; evaluation is human gold)",
        ),
        UncheckedItem(
            item="H7 -- calibration (ECE, J/deltaJ) under the P7 confidence-schema variant",
            reason=(
                "BLOCKER: no live P7 calls have been made at all -- scripts/e2_replication.py "
                "covers only P0a/P0b, scripts/e5_prompt_sweep.py only P0b/P1-P6; P7 (the "
                "confidence-schema addition) is real and available in judges/prompts.py but "
                "has not been exercised against the live judge, live or otherwise"
            ),
        ),
        UncheckedItem(
            item="Result 2 -- matched three-corpus transfer probe",
            reason=(
                f"{gated_corpus}; also kill-gated pending a compute-budget spike (D008) not yet run"
            ),
        ),
    ]


def main() -> int:
    card = build_card(
        claims=[_h8_claim(), *_h1_h1b_claims(), _h3_claim()],
        what_could_not_be_checked=_unmet_claims(),
        sample_definition=(
            "E10k-ego/E10k-ego4d/E10k-epic (10,000 each), P2k (2,000), "
            "G200-ego/G200-ego4d/G200-epic (200 each), and R100 (100) are drawn and persisted "
            "(scripts/draw_all_samples.py, docs/DECISIONS.md D045). E10k-ego (N=10,000, both "
            "P0a/P0b) and P2k (N=2,000, 8 prompt-variant-passes) have real, complete live-judge "
            "runs behind the H1/H1b/H3 claims above (docs/DECISIONS.md D054/D055) -- but no "
            "`PrevalenceEstimate`/PPI-corrected estimate has been computed from any sample yet; "
            "that needs Wave 3's human labels (see H2/H4-H7/Result 2's reasons below). "
            "S10k-U/S10k-S are not drawn: the raw Egocentric-10K corpus this account has "
            "confirmed access to read metadata for but not download (docs/DECISIONS.md D044). "
            "H8 needs no sample at all -- public participant counts only."
        ),
        rubric_rev="1.2.0",
        judge_revisions={},
        agreement_results=[],
        prevalence_estimates=[],
    )

    out_path = Path(__file__).resolve().parent.parent / "MEASUREMENT_CARD.json"
    emit_card(card, out_path)
    print(f"wrote {out_path}")
    print(f"verdict: {card.verdict}")
    print(f"claims: {len(card.claims)}, what_could_not_be_checked: {len(card.what_could_not_be_checked)}")
    return verify_and_exit(card)


if __name__ == "__main__":
    sys.exit(main())
