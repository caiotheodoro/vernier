"""Emits the `MeasurementCard`: verdict, every claim tied to the record that produced it,
"what could not be checked" with a reason per item, and a content digest.

Exits nonzero when the verdict is not `VERIFIED` -- an audit that always exits zero is
decoration.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from vernier.models import (
    AgreementResult,
    Claim,
    CardInterval,
    MeasurementCard,
    PrevalenceEstimate,
    UncheckedItem,
)

VERIFIED = "VERIFIED"
NOT_VERIFIED = "NOT_VERIFIED"

# Reasons that name a hard blocker are prefixed "BLOCKER:" by convention (case-insensitive).
# Any other reason is informational -- it documents a gap without invalidating the verdict.
_HARD_BLOCKER_PREFIX = "BLOCKER:"


def _prevalence_ref(estimate: PrevalenceEstimate) -> str:
    return f"{estimate.corpus}/{estimate.task}/{estimate.prompt_variant}/{estimate.judge}"


def _is_hard_blocker(item: UncheckedItem) -> bool:
    return item.reason.strip().upper().startswith(_HARD_BLOCKER_PREFIX)


def _derive_verdict(
    claims: list[Claim],
    what_could_not_be_checked: list[UncheckedItem],
    prevalence_estimates: list[PrevalenceEstimate],
) -> str:
    """VERIFIED iff every `PrevalenceEstimate` is tied to a claim, and no unchecked item is a
    hard blocker.

    A claim ties to an estimate when it has `record_type == "PrevalenceEstimate"` and
    `record_ref` equal to `f"{corpus}/{task}/{prompt_variant}/{judge}"` for that estimate --
    this is the same natural key `PrevalenceEstimate` carries, so callers do not invent a
    separate id scheme. A hard blocker is any unchecked item whose `reason` starts with
    "BLOCKER:" (case-insensitive); everything else in `what_could_not_be_checked` is
    informational and does not, by itself, prevent VERIFIED -- CONTRACTS.md requires that
    gaps be *named*, not that naming one always fails the card.
    """
    claimed_refs = {
        claim.record_ref for claim in claims if claim.record_type == "PrevalenceEstimate"
    }
    all_estimates_claimed = all(
        _prevalence_ref(estimate) in claimed_refs for estimate in prevalence_estimates
    )
    has_hard_blocker = any(_is_hard_blocker(item) for item in what_could_not_be_checked)
    if all_estimates_claimed and not has_hard_blocker:
        return VERIFIED
    return NOT_VERIFIED


def build_card(
    claims: list[Claim],
    what_could_not_be_checked: list[UncheckedItem],
    sample_definition: str,
    rubric_rev: str,
    judge_revisions: dict[str, str],
    agreement_results: list[AgreementResult],
    prevalence_estimates: list[PrevalenceEstimate],
) -> MeasurementCard:
    """Assemble the card. An empty `what_could_not_be_checked` must never read as a clean
    bill of health -- callers must justify it, not default to it. This function accepts an
    empty list as-is (justifying it is the caller's job); see `_derive_verdict` for how the
    verdict itself is decided."""
    intervals = tuple(
        CardInterval(
            label=f"{result.task} AC1, {result.comparison.a} vs {result.comparison.b}, {result.subset}",
            ci=result.ci,
            design_effect=result.design_effect,
        )
        for result in agreement_results
    )
    prompt_variants = tuple(sorted({estimate.prompt_variant for estimate in prevalence_estimates}))
    verdict = _derive_verdict(claims, what_could_not_be_checked, prevalence_estimates)
    card = MeasurementCard(
        verdict=verdict,
        claims=tuple(claims),
        what_could_not_be_checked=tuple(what_could_not_be_checked),
        sample_definition=sample_definition,
        rubric_rev=rubric_rev,
        judge_revisions=judge_revisions,
        prompt_variants=prompt_variants,
        intervals=intervals,
        content_digest="",
    )
    return card.model_copy(update={"content_digest": compute_digest(card)})


def compute_digest(card: MeasurementCard) -> str:
    """A content digest identifies the card and catches corruption. Not tamper-evidence:
    anyone editing the body can recompute it."""
    canonical = card.model_dump_json(exclude={"content_digest"})
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()


def emit_card(card: MeasurementCard, path: Path) -> None:
    path.write_text(card.model_dump_json())


def verify_and_exit(card: MeasurementCard) -> int:
    """Return 0 iff `card.verdict == VERIFIED`, nonzero otherwise. Callers pass this to
    `sys.exit`."""
    return 0 if card.verdict == VERIFIED else 1
