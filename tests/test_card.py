from __future__ import annotations

from pathlib import Path

from tests.fixtures import make_agreement_result, make_prevalence_estimate
from vernier.card import VERIFIED, build_card, compute_digest, emit_card, verify_and_exit
from vernier.models import Claim, MeasurementCard, UncheckedItem


def _claim_for(prevalence_estimate: object, statement: str = "replicates within tolerance") -> Claim:
    pe = prevalence_estimate
    return Claim(
        statement=statement,
        record_type="PrevalenceEstimate",
        record_ref=f"{pe.corpus}/{pe.task}/{pe.prompt_variant}/{pe.judge}",  # type: ignore[attr-defined]
    )


def _build(**overrides: object) -> MeasurementCard:
    pe = make_prevalence_estimate()
    payload: dict[str, object] = dict(
        claims=[_claim_for(pe)],
        what_could_not_be_checked=[],
        sample_definition="G200-ego, n=200, seed 777",
        rubric_rev="1.2.0",
        judge_revisions={"gemini-2.5-flash": "2025-06-01"},
        agreement_results=[make_agreement_result()],
        prevalence_estimates=[pe],
    )
    payload.update(overrides)
    return build_card(**payload)  # type: ignore[arg-type]


def test_every_prevalence_estimate_claimed_and_no_blockers_yields_verified() -> None:
    card = _build()
    assert card.verdict == VERIFIED


def test_prevalence_estimate_without_matching_claim_is_not_verified() -> None:
    pe = make_prevalence_estimate()
    unclaimed_pe = make_prevalence_estimate(task="grasp-type")
    card = build_card(
        claims=[_claim_for(pe)],
        what_could_not_be_checked=[],
        sample_definition="G200-ego, n=200, seed 777",
        rubric_rev="1.2.0",
        judge_revisions={"gemini-2.5-flash": "2025-06-01"},
        agreement_results=[make_agreement_result()],
        prevalence_estimates=[pe, unclaimed_pe],
    )
    assert card.verdict != VERIFIED


def test_hard_blocker_unchecked_item_prevents_verified_even_with_full_claim_coverage() -> None:
    card = _build(
        what_could_not_be_checked=[
            UncheckedItem(item="Calibration under P0a", reason="BLOCKER: no gold labels collected"),
        ],
    )
    assert card.verdict != VERIFIED


def test_non_blocker_unchecked_item_does_not_prevent_verified() -> None:
    card = _build(
        what_could_not_be_checked=[
            UncheckedItem(item="Calibration under P0a/P0b", reason="published schema exposes no confidence"),
        ],
    )
    assert card.verdict == VERIFIED


def test_intervals_built_from_agreement_results() -> None:
    ar = make_agreement_result()
    card = _build(agreement_results=[ar])
    assert len(card.intervals) == 1
    interval = card.intervals[0]
    assert interval.ci == ar.ci
    assert interval.design_effect == ar.design_effect
    assert ar.task in interval.label
    assert ar.subset in interval.label


def test_prompt_variants_derived_sorted_and_deduplicated() -> None:
    pe_a = make_prevalence_estimate(prompt_variant="P0b")
    pe_b = make_prevalence_estimate(prompt_variant="P0a")
    pe_c = make_prevalence_estimate(prompt_variant="P0a")
    card = build_card(
        claims=[_claim_for(pe_a), _claim_for(pe_b), _claim_for(pe_c)],
        what_could_not_be_checked=[],
        sample_definition="G200-ego, n=200, seed 777",
        rubric_rev="1.2.0",
        judge_revisions={"gemini-2.5-flash": "2025-06-01"},
        agreement_results=[make_agreement_result()],
        prevalence_estimates=[pe_a, pe_b, pe_c],
    )
    assert card.prompt_variants == ("P0a", "P0b")


def test_build_card_stamps_a_content_digest() -> None:
    card = _build()
    assert card.content_digest
    assert card.content_digest == compute_digest(card.model_copy(update={"content_digest": ""}))


def test_compute_digest_deterministic() -> None:
    card = _build()
    assert compute_digest(card) == compute_digest(card)


def test_compute_digest_changes_when_a_field_changes() -> None:
    card = _build()
    mutated = card.model_copy(update={"sample_definition": "a different sample"})
    assert compute_digest(card) != compute_digest(mutated)


def test_emit_card_round_trips_through_json(tmp_path: Path) -> None:
    card = _build()
    path = tmp_path / "card.json"
    emit_card(card, path)
    reloaded = MeasurementCard.model_validate_json(path.read_text())
    assert reloaded == card


def test_verify_and_exit_zero_for_verified() -> None:
    card = _build()
    assert card.verdict == VERIFIED
    assert verify_and_exit(card) == 0


def test_verify_and_exit_nonzero_for_not_verified() -> None:
    pe = make_prevalence_estimate()
    unclaimed_pe = make_prevalence_estimate(task="grasp-type")
    card = build_card(
        claims=[_claim_for(pe)],
        what_could_not_be_checked=[],
        sample_definition="G200-ego, n=200, seed 777",
        rubric_rev="1.2.0",
        judge_revisions={"gemini-2.5-flash": "2025-06-01"},
        agreement_results=[make_agreement_result()],
        prevalence_estimates=[pe, unclaimed_pe],
    )
    assert verify_and_exit(card) != 0
