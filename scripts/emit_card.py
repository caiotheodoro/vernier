"""Emit vernier's real `MeasurementCard` for its current actual state.

This is not a demo or a synthetic fixture: every `Claim` and `UncheckedItem` here reflects
what has and has not actually been run, as of this commit. H8 is pre-registered as
"computable from public participant counts before a single frame is labelled, and reported
first for that reason" (`PRE-REGISTRATION.md`) -- it is the one hypothesis with a real claim
today.

**Refreshed post-reframe (`docs/DECISIONS.md` D042-D045)** -- the previous version of this
script predated the judge-panel reframe and named credentials-not-configured as every blocker's
reason. That is no longer true: real samples are drawn and persisted
(`scripts/draw_all_samples.py`), the Qwen3-VL judge is live and deployed, and
`scripts/e2_replication.py`/`scripts/e5_prompt_sweep.py` have real, live, preliminary results
(n=100/n=5 respectively -- see `docs/HANDOFF.md`). None of that reaches the pre-registered
sample sizes those hypotheses are actually specified at, so H1, H1b, H2, H3, H4, H5, H6, H7,
and Result 2 all remain named as unmet, each with a `"BLOCKER:"`-prefixed reason
(`docs/DECISIONS.md` D038) describing the REAL current blocker, not a stale one -- ensuring
`_derive_verdict` returns `NOT_VERIFIED`, not a vacuous `VERIFIED` from having zero prevalence
estimates to fail to claim.
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
    # Real infra exists and is live for H1/H1b/H3 (docs/HANDOFF.md): scripts/e2_replication.py
    # and scripts/e5_prompt_sweep.py both ran real preliminary batches (n=100, n=5) against the
    # deployed Qwen3-VL judge with every call status "ok". What's missing is scale, not
    # plumbing -- these hypotheses are pre-registered at N=10,000/full prompt-variant sets, and
    # running near that size needs a separate, explicit decision from Caio (the approved
    # reframe plan scoped this session to smoke-testing, not a production run).
    e2_scale = (
        "BLOCKER: pre-registered N=10,000 not run. Real infra is deployed and live "
        "(scripts/e2_replication.py) -- a real n=100 preliminary run exists "
        "(data/e2_n100.json, gitignored) with every call status 'ok', but running at "
        "pre-registered scale needs a separate, explicit decision from Caio, not more code"
    )
    e5_scale = (
        "BLOCKER: pre-registered N/full prompt-variant coverage not run. Real infra is "
        "deployed and live (scripts/e5_prompt_sweep.py) -- a real n=5 preliminary run exists "
        "(data/e5_smoke_n5.json, gitignored) with every call status 'ok', but running at "
        "pre-registered scale needs a separate, explicit decision from Caio, not more code"
    )
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
            item="H1 -- the live judge's aggregate rates land within +/-2pp of Build AI's "
            "three published figures (E10k-ego, docs/DECISIONS.md D042's reframe of this "
            "hypothesis from a gemini-2.5-flash replication to a live-judge comparison)",
            reason=e2_scale,
        ),
        UncheckedItem(
            item="H1b -- P0a and P0b disagree on the manipulation figure by >=1pp",
            reason=e2_scale,
        ),
        UncheckedItem(
            item="H2 -- cluster-bootstrap design effect >=2 on S10k-U/S10k-S",
            reason=gated_corpus,
        ),
        UncheckedItem(
            item="H3 -- prompt sensitivity spread >=5pp for manipulation across P1-P7",
            reason=e5_scale,
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
        claims=[_h8_claim()],
        what_could_not_be_checked=_unmet_claims(),
        sample_definition=(
            "E10k-ego/E10k-ego4d/E10k-epic (10,000 each), P2k (2,000), "
            "G200-ego/G200-ego4d/G200-epic (200 each), and R100 (100) are drawn and persisted "
            "(scripts/draw_all_samples.py, docs/DECISIONS.md D045) -- but no PrevalenceEstimate "
            "has been computed from any of them yet, only real preliminary judge calls outside "
            "the pre-registered sample sizes (see H1/H1b/H3's reasons below). S10k-U/S10k-S "
            "are not drawn: the raw Egocentric-10K corpus this account has confirmed access to "
            "read metadata for but not download (docs/DECISIONS.md D044). H8 needs no sample "
            "at all -- public participant counts only."
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
