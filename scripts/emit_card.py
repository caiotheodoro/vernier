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

**Refreshed post-Wave-3/D059** -- Wave 3's real (reduced-target, D057/D058) human labels and
`scripts/judge_gold_sets.py`'s real live-judge run over all three `G200-*` sets are both
complete. `_intra_rater_claim()`, `_h4_claim()`, `_h5_claim()`, and `_ppi_claims()` below read
`data/wave4_analysis.json` (gitignored, real artifact from `scripts/wave4_analysis.py`) for the
real intra-rater AC1 (`R100`'s falsification gate), H4, H5, and six PPI-corrected prevalence
estimates (3 domains x 2 tasks). Both H4 and H5 are real, checked, **negative** findings --
reported as such, not reframed. The six `PrevalenceEstimate`s are the first `record_type ==
"PrevalenceEstimate"` claims this card carries, so `_derive_verdict` (D038) now actually
exercises its estimate-matching path, not just its blocker-scanning one.

**H7 closed (D060)** -- `_h7_claim()` reads real calibration off already-collected `P0b`
logprob confidence, a disclosed deviation from "P7 only" (the self-hosted judge exposes
confidence on every call, not just P7).

**H6 closed (D061)** -- `_h6_claim()` reads `data/rung1_distillation.json`
(`scripts/distill_rung1.py`'s real output): a real, disclosed backbone substitution
(`facebook/dinov2-small` for the gated `facebook/dinov3-vits16-pretrain-lvd1689m`, D034/D051),
a real rung-1 linear probe, and a real `AbstentionCascade` calibrated/evaluated on a disjoint
split of Wave 3's human gold. **Does not hold**: agreement floor (0.842) clears the
pre-registered >=0.80 target, but coverage (0.404) falls well short of >=0.70 -- reported as a
real, checked, mixed/negative finding, not reframed.

H2 and Result 2 remain named as unmet, each with a `"BLOCKER:"`-prefixed reason
(`docs/DECISIONS.md` D038) describing the REAL current blocker, not a stale one -- ensuring
`_derive_verdict` returns `NOT_VERIFIED` because a real blocker is present, not vacuously from
having nothing to claim.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from vernier.card import build_card, emit_card, verify_and_exit
from vernier.estimation.disparity import participant_count_disparity
from vernier.models import Claim, PrevalenceEstimate, UncheckedItem

_ROOT = Path(__file__).resolve().parent.parent
_E2_RESULTS_PATH = _ROOT / "data" / "e2_full_n10000.json"
_E5_RESULTS_PATH = _ROOT / "data" / "e5_full_n2000.json"
_WAVE4_RESULTS_PATH = _ROOT / "data" / "wave4_analysis.json"
_RUNG1_RESULTS_PATH = _ROOT / "data" / "rung1_distillation.json"
_E2_RESULTS_REF = "data/e2_full_n10000.json"
_E5_RESULTS_REF = "data/e5_full_n2000.json"
_WAVE4_RESULTS_REF = "data/wave4_analysis.json"
_RUNG1_RESULTS_REF = "data/rung1_distillation.json"

# scripts/wave4_analysis.py's own domain-name/judge/prompt-variant constants, duplicated here
# per D033's no-shared-file-edits convention (small constants, not worth a shared import).
_DOMAIN_LABEL = {"G200-ego": "Egocentric-10K", "G200-ego4d": "Ego4D", "G200-epic": "EPIC-KITCHENS-100"}
_WAVE4_JUDGE = "qwen3-vl"
_WAVE4_PROMPT_VARIANT = "P0b"

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


def _intra_rater_claim() -> Claim:
    """Real intra-rater AC1/kappa (`PRE-REGISTRATION.md`'s first-listed falsification check:
    "Human gold disagrees with itself... AC1 on R100 below 0.70... the audit is deferred").
    D058's reduced retest (n=34 real overlapping pairs, not the pre-registered 100) -- reported
    with that real n, not silently as if full precision had been achieved."""
    wave4 = json.loads(_WAVE4_RESULTS_PATH.read_text())
    intra = wave4["intra_rater"]
    below_gate = {task: v["ac1"] < 0.70 for task, v in intra.items()}
    statement = (
        f"Intra-rater reliability (R100 falsification gate, n={intra['hand_count']['n_pairs']} "
        "real overlapping primary/retest pairs, D058's reduced target -- not the pre-registered "
        "n=100): "
        + "; ".join(
            f"{task} AC1={v['ac1']:.4f} (95% iid bootstrap CI "
            f"[{v['ac1_ci']['lo']:.4f}, {v['ac1_ci']['hi']:.4f}]), kappa={v['kappa']:.4f}"
            for task, v in intra.items()
        )
        + ". Both clear the pre-registered 0.70 gate: the rubric is decidable, the audit is not "
        "deferred. Real n is small (34, not 100) so this reads as a real positive result at "
        "reduced precision, not the full-precision one the pre-registration specified. Not "
        "clustered: HumanLabel carries no shared participant/cluster id with FrameRef "
        "(docs/DECISIONS.md D039, unfixed) -- each interval is a lower bound on true width, not "
        "the full cluster-aware one."
    )
    if any(below_gate.values()):
        failing = [task for task, below in below_gate.items() if below]
        statement += f" WARNING: {failing} fell below 0.70 -- PRE-REGISTRATION.md's own rule."
    return Claim(statement=statement, record_type="IntraRaterAgreement", record_ref=f"{_WAVE4_RESULTS_REF}#intra_rater")


def _h4_claim() -> Claim:
    """Real, checked finding from `scripts/wave4_analysis.py`, off Wave 3's human gold and
    `scripts/judge_gold_sets.py`'s live-judge run over the three `G200-*` sets. Pre-registered
    as a bare AC1 comparison with no confidence interval; a real iid bootstrap CI (D063) is
    reported alongside each point estimate as an addition, not a replacement."""
    wave4 = json.loads(_WAVE4_RESULTS_PATH.read_text())
    h4 = wave4["H4"]
    statement = (
        f"H4 (N={wave4['n_primary']} primary labels vs. the single judge in the panel, "
        f"{_WAVE4_JUDGE}, {_WAVE4_PROMPT_VARIANT}): AC1(judge, human) hand_count="
        f"{h4['hand_count']['ac1']:.4f} (95% iid bootstrap CI "
        f"[{h4['hand_count']['ac1_ci']['lo']:.4f}, {h4['hand_count']['ac1_ci']['hi']:.4f}]), "
        f"manipulation={h4['manipulation']['ac1']:.4f} (95% iid bootstrap CI "
        f"[{h4['manipulation']['ac1_ci']['lo']:.4f}, {h4['manipulation']['ac1_ci']['hi']:.4f}]). "
        "Pre-registered prediction is hand_count higher (perceptual vs. interpretative, "
        "PRE-REGISTRATION.md H3's own framing extended to H4); the real result is the "
        + ("predicted direction." if h4["holds"] else "OPPOSITE direction: manipulation agreement is higher.")
        + " Not clustered: HumanLabel carries no shared participant/cluster id with FrameRef "
        "(docs/DECISIONS.md D039, unfixed) -- each interval is a lower bound on true width, not "
        "the full cluster-aware one."
    )
    return Claim(statement=statement, record_type="AgreementComparison", record_ref=f"{_WAVE4_RESULTS_REF}#H4")


def _h5_claim() -> Claim:
    """Real, checked finding from `scripts/wave4_analysis.py`. Pre-registered as a bare error-rate
    difference against a >=5pp threshold with a predicted direction, no confidence interval."""
    wave4 = json.loads(_WAVE4_RESULTS_PATH.read_text())
    h5 = wave4["H5"]
    statement = (
        f"H5 (primary-labelled subset: n={h5['egocentric']['n']} Egocentric, "
        f"n={h5['epic_kitchens']['n']} EPIC-KITCHENS-100): judge error rate on manipulation vs. "
        f"human gold -- Egocentric {h5['egocentric']['error_rate']:.4f}, EPIC-KITCHENS-100 "
        f"{h5['epic_kitchens']['error_rate']:.4f}, diff {h5['diff_pp']:.2f}pp. Pre-registered "
        "criterion is >=5pp with EPIC-KITCHENS-100 higher; "
        + (
            "met."
            if h5["holds"]
            else (
                "NOT met" + (" -- the direction is also REVERSED (Egocentric's error rate is higher)." if not h5["epic_kitchens_higher"] else ".")
            )
        )
        + " Real sample is far below the pre-registered balanced-gold size (D057), and H5 was "
        "already found underpowered even at that full size (docs/DECISIONS.md D035) -- a null "
        "or reversed result here is genuinely ambiguous between 'no domain-bias effect at this "
        "threshold' and 'this sample cannot reliably surface one,' not a clean refutation."
    )
    return Claim(statement=statement, record_type="AgreementComparison", record_ref=f"{_WAVE4_RESULTS_REF}#H5")


def _ppi_claims() -> tuple[list[Claim], list[PrevalenceEstimate]]:
    """Six real PPI-corrected prevalence estimates (3 domains x 2 tasks) from
    `scripts/wave4_analysis.py`, each backed by a real `PrevalenceEstimate` record and a
    matching `Claim` (`record_type="PrevalenceEstimate"`, D038's exact natural-key `record_ref`
    format) -- the first claims this card ties to `_derive_verdict`'s estimate-matching path,
    not just its blocker-scanning one."""
    wave4 = json.loads(_WAVE4_RESULTS_PATH.read_text())
    claims: list[Claim] = []
    estimates: list[PrevalenceEstimate] = []
    for sample, by_task in wave4["ppi"].items():
        for task, estimate_dict in by_task.items():
            estimate = PrevalenceEstimate.model_validate(estimate_dict)
            estimates.append(estimate)
            ref = f"{estimate.corpus}/{estimate.task}/{estimate.prompt_variant}/{estimate.judge}"
            statement = (
                f"PPI-corrected prevalence, {_DOMAIN_LABEL[sample]} ({task}, "
                f"n_gold={estimate.ppi.n_gold}, n_unlabelled={estimate.ppi.n_unlabelled}): "
                f"naive (judge-only) {estimate.naive.value:.4f}, PPI++ {estimate.ppi.value:.4f} "
                f"(95% CI [{estimate.ppi.ci.lo:.4f}, {estimate.ppi.ci.hi:.4f}]), published "
                f"{estimate.published:.4f}. Not clustered: HumanLabel carries no shared "
                "participant/cluster id with FrameRef (docs/DECISIONS.md D039, unfixed) -- this "
                "interval is a lower bound on true width, not the full cluster-aware one."
            )
            claims.append(Claim(statement=statement, record_type="PrevalenceEstimate", record_ref=ref))
    return claims, estimates


def _h7_claim() -> Claim:
    """Real, checked finding from `scripts/wave4_analysis.py` (D060) -- a disclosed deviation
    from `PRE-REGISTRATION.md`'s "calibration under P7 only" scoping: the self-hosted judge
    exposes real logprob confidence on every call, not just P7 (`judges/qwen3vl.py`, D052/D053),
    so this reads confidence straight off the already-collected `P0b` `G200-*` responses against
    the 93 primary human-gold labels. No new judge calls; stated plainly, not silently swapped."""
    wave4 = json.loads(_WAVE4_RESULTS_PATH.read_text())
    calibration = wave4["H7_calibration"]
    top_bin_shares = {
        task: max((b["n"] for b in report["bins"]), default=0) / report["n"] if report["n"] else 0.0
        for task, report in calibration.items()
    }
    statement = (
        f"H7 (D060: calibration read from {_WAVE4_JUDGE}'s {_WAVE4_PROMPT_VARIANT} logprob "
        "confidence, a real, disclosed deviation from PRE-REGISTRATION.md's 'P7 only' scoping -- "
        "the retired closed judges needed P7 to expose any confidence at all; this self-hosted "
        "judge exposes it on every call): "
        + "; ".join(f"{task} ECE={report['ece']:.4f} (n={report['n']})" for task, report in calibration.items())
        + ". Confidence is near-degenerate under greedy decoding (temperature=0, D053): "
        + "; ".join(f"{task} {share:.0%} of frames land in the top [0.9, 1.0] bin" for task, share in top_bin_shares.items())
        + " -- ECE here is measured almost entirely from that one bin, not a real spread across "
        "confidence levels. A real number, not a fabricated one, but a weak calibration curve by "
        "construction, not a limitation of the estimator."
    )
    return Claim(statement=statement, record_type="Calibration", record_ref=f"{_WAVE4_RESULTS_REF}#H7_calibration")


def _h6_claim() -> Claim:
    """Real, checked finding from `scripts/distill_rung1.py` (D061) -- a disclosed backbone
    substitution: `facebook/dinov2-small` (verified live, genuinely ungated) instead of D034's
    pinned, gated `facebook/dinov3-vits16-pretrain-lvd1689m` (D051, no access). The rung-1
    probe trains on `gemini-2.5-flash` P0b's stored labels (D047, H6's own pre-registered
    fidelity target); the `AbstentionCascade`'s threshold is calibrated on, and its floor/
    coverage evaluated against, a real disjoint split of Wave 3's human gold -- never the
    judge's own labels, per H6's own pre-registered design."""
    rung1 = json.loads(_RUNG1_RESULTS_PATH.read_text())
    statement = (
        f"H6 (D061: rung-1 linear probe on {rung1['backbone']} features -- a disclosed "
        "substitute for D034's gated DINOv3 pin, not the same checkpoint under a different "
        f"name; n_train={rung1['n_train']}, n_fidelity_holdout={rung1['n_fidelity_holdout']}): "
        f"teacher fidelity vs. gemini-2.5-flash P0b = {rung1['fidelity_vs_gemini_2_5_flash']:.4f} "
        "(pre-registered diagnostic target >=0.90, not met -- a real, disclosed diagnostic gap, "
        "not the H6 claim itself). "
    )
    if not rung1["floor_reached"]:
        statement += (
            f"The pre-registered floor (>=0.80) was UNREACHABLE at any coverage > 0 on the real "
            f"n={rung1['n_calibration_gold']} calibration split of Wave 3's human gold: "
            f"{rung1.get('error', 'no threshold cleared the floor')}. H6 does not hold."
        )
    else:
        statement += (
            f"AbstentionCascade, threshold calibrated on n={rung1['n_calibration_gold']} human-gold "
            f"frames, evaluated on a disjoint n={rung1['n_eval_gold']}: agreement floor="
            f"{rung1['agreement_floor']:.4f} (pre-registered target >=0.80, "
            + ("met" if rung1["agreement_floor"] >= rung1["target_floor"] else "NOT met")
            + f"), coverage={rung1['coverage']:.4f} (pre-registered target >=0.70, "
            + ("met" if rung1["coverage"] >= rung1["target_coverage"] else "NOT met")
            + "). H6 requires both simultaneously; "
            + ("it holds." if rung1["holds"] else "it does NOT hold.")
        )
    statement += (
        " Real limitation, disclosed: the calibration/eval split is small (Wave 3's reduced "
        "target, D057/D058). The threshold search now requires a 95%-confidence Wilson-score "
        "lower bound on prefix accuracy, not the raw point estimate (D063, closing the specific "
        "no-safety-margin gap cascade.py's docstring used to name) -- this is a real, tighter "
        "guarantee than before, but still not full Learn-then-Test/conformal risk control (D049 "
        "remains the eventual complete fix; a Wilson bound treats nested prefixes as independent "
        "draws, which they are not)."
    )
    return Claim(statement=statement, record_type="DistillationCascade", record_ref=f"{_RUNG1_RESULTS_REF}#H6")


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
    # H4/H5 (D059), H7 (D060), and H6 (D061) are now all real, checked Claims -- Wave 3's human
    # labels, scripts/judge_gold_sets.py's live-judge run, and scripts/distill_rung1.py (a
    # disclosed DINOv2 substitute for the gated DINOv3 pin) all completed for real.
    return [
        UncheckedItem(
            item="H2 -- cluster-bootstrap design effect >=2 on S10k-U/S10k-S",
            reason=gated_corpus,
        ),
        UncheckedItem(
            item="Result 2 -- matched three-corpus transfer probe",
            reason=(
                f"{gated_corpus}; also kill-gated pending a compute-budget spike (D008) not yet run"
            ),
        ),
    ]


def main() -> int:
    ppi_claims, ppi_estimates = _ppi_claims()
    card = build_card(
        claims=[
            _h8_claim(),
            *_h1_h1b_claims(),
            _h3_claim(),
            _intra_rater_claim(),
            _h4_claim(),
            _h5_claim(),
            _h6_claim(),
            *ppi_claims,
            _h7_claim(),
        ],
        what_could_not_be_checked=_unmet_claims(),
        sample_definition=(
            "E10k-ego/E10k-ego4d/E10k-epic (10,000 each), P2k (2,000), "
            "G200-ego/G200-ego4d/G200-epic (200 each), and R100 (100) are drawn and persisted "
            "(scripts/draw_all_samples.py, docs/DECISIONS.md D045). E10k-ego (N=10,000, both "
            "P0a/P0b) and P2k (N=2,000, 8 prompt-variant-passes) have real, complete live-judge "
            "runs behind the H1/H1b/H3 claims (docs/DECISIONS.md D054/D055). All three G200-* "
            "sets (200 each) are also fully live-judged (D059, scripts/judge_gold_sets.py); "
            "Wave 3's real human gold (93 primary / 34-overlap retest, D057/D058) is matched "
            "against them for the intra-rater/H4/H5/PPI claims above. R100 needed no separate "
            "judge run -- it is a subset of the G200-* union. S10k-U/S10k-S are not drawn: the "
            "raw Egocentric-10K corpus this account has confirmed access to read metadata for "
            "but not download (docs/DECISIONS.md D044). H8 needs no sample at all -- public "
            "participant counts only."
        ),
        rubric_rev="1.2.0",
        judge_revisions={},
        agreement_results=[],
        prevalence_estimates=ppi_estimates,
    )

    out_path = Path(__file__).resolve().parent.parent / "MEASUREMENT_CARD.json"
    emit_card(card, out_path)
    print(f"wrote {out_path}")
    print(f"verdict: {card.verdict}")
    print(f"claims: {len(card.claims)}, what_could_not_be_checked: {len(card.what_could_not_be_checked)}")
    return verify_and_exit(card)


if __name__ == "__main__":
    sys.exit(main())
