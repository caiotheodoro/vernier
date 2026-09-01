"""Emits the `MeasurementCard`: verdict, every claim tied to the record that produced it,
"what could not be checked" with a reason per item, and a content digest.

Exits nonzero when the verdict is not `VERIFIED` -- an audit that always exits zero is
decoration.
"""

from __future__ import annotations

from pathlib import Path

from vernier.models import (
    AgreementResult,
    Claim,
    MeasurementCard,
    PrevalenceEstimate,
    UncheckedItem,
)

VERIFIED = "VERIFIED"


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
    bill of health -- callers must justify it, not default to it."""
    raise NotImplementedError


def compute_digest(card: MeasurementCard) -> str:
    """A content digest identifies the card and catches corruption. Not tamper-evidence:
    anyone editing the body can recompute it."""
    raise NotImplementedError


def emit_card(card: MeasurementCard, path: Path) -> None:
    raise NotImplementedError


def verify_and_exit(card: MeasurementCard) -> int:
    """Return 0 iff `card.verdict == VERIFIED`, nonzero otherwise. Callers pass this to
    `sys.exit`."""
    raise NotImplementedError
