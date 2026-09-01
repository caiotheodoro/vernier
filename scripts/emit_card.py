"""Emit vernier's real `MeasurementCard` for its current actual state.

This is not a demo or a synthetic fixture: every `Claim` and `UncheckedItem` here reflects
what has and has not actually been run, as of this commit. H8 is pre-registered as
"computable from public participant counts before a single frame is labelled, and reported
first for that reason" (`PRE-REGISTRATION.md`) -- it is the one hypothesis with a real claim
today. H1, H1b, H2, H3, H4, H5, H6, H7, and Result 2 all require a resource this environment
does not have (a live judge API key, the gated corpus, or the 600 human labels) and are named
as such, each with a `"BLOCKER:"`-prefixed reason (`docs/DECISIONS.md` D038) -- ensuring
`_derive_verdict` returns `NOT_VERIFIED`, not a vacuous `VERIFIED` from having zero
prevalence estimates to fail to claim.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from vernier.card import build_card, emit_card, verify_and_exit
from vernier.estimation.disparity import participant_count_disparity
from vernier.models import Claim, UncheckedItem

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


def _unmet_claims() -> list[UncheckedItem]:
    live_judge = "BLOCKER: requires a live judge API call (GEMINI_API_KEY/ANTHROPIC_API_KEY not configured)"
    gated_corpus = "BLOCKER: requires the gated Egocentric-10K corpus (HF_TOKEN not configured)"
    human_gold = "BLOCKER: requires the 600 primary human labels (Wave 3, not yet collected)"
    return [
        UncheckedItem(
            item="H1 -- gemini-2.5-flash P0a replicates the published figures within +/-2pp",
            reason=live_judge,
        ),
        UncheckedItem(
            item="H1b -- P0a and P0b disagree on the manipulation figure by >=1pp",
            reason=live_judge,
        ),
        UncheckedItem(
            item="H2 -- cluster-bootstrap design effect >=2 on S10k-U/S10k-S",
            reason=gated_corpus,
        ),
        UncheckedItem(
            item="H3 -- prompt sensitivity spread >=5pp for manipulation across P1-P7",
            reason=live_judge,
        ),
        UncheckedItem(
            item="H4 -- AC1(judge, human) higher for hand-count than manipulation",
            reason=f"{live_judge}; {human_gold}",
        ),
        UncheckedItem(
            item="H5 -- domain-bias judge error rate differs >=5pp, Egocentric vs EPIC-KITCHENS-100",
            reason=f"{live_judge}; {human_gold}",
        ),
        UncheckedItem(
            item="H6 -- distilled instrument holds >=0.80 agreement floor at >=0.70 coverage",
            reason=f"{live_judge}; {human_gold} (training targets are judge labels; evaluation is human gold)",
        ),
        UncheckedItem(
            item="H7 -- calibration (ECE, J/deltaJ) under the P7 confidence-schema variant",
            reason=live_judge,
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
        claims=[_h8_claim()],
        what_could_not_be_checked=_unmet_claims(),
        sample_definition=(
            "No sample drawn yet (Wave 2 blocked on credentials). H8 needs no sample -- public "
            "participant counts only."
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
