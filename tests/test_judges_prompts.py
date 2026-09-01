"""Behavioural tests for `vernier.judges.prompts.load_prompt`.

Reads the pinned upstream files directly (never hardcodes their text) so these tests fail
the moment `docs/upstream/*.txt` and `prompts.py` drift apart.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from vernier.judges.prompts import load_prompt
from vernier.models import PromptVariant

UPSTREAM = Path(__file__).resolve().parents[1] / "docs" / "upstream"


def _upstream_text(name: str) -> str:
    return (UPSTREAM / name).read_text()


# --- P0a / P0b: verbatim upstream, keyed by task --------------------------------------------


@pytest.mark.parametrize("task, upstream_file", [
    ("hand_count", "P0a-hand_count.txt"),
    ("manipulation", "P0a-active_manipulation.txt"),
])
def test_p0a_matches_upstream_file(task: str, upstream_file: str) -> None:
    text = load_prompt("P0a", task=task)
    assert text
    assert text == _upstream_text(upstream_file)


@pytest.mark.parametrize("task, upstream_file", [
    ("hand_count", "P0b-hand_count.txt"),
    ("manipulation", "P0b-active_manipulation.txt"),
])
def test_p0b_matches_upstream_file(task: str, upstream_file: str) -> None:
    text = load_prompt("P0b", task=task)
    assert text
    assert text == _upstream_text(upstream_file)


def test_p0a_and_p0b_diverge_on_manipulation() -> None:
    # D014/D015: the dataset-card prompt and the shipped prompts/ file genuinely differ for
    # active_manipulation -- that divergence is the entire point of running both as arms.
    assert load_prompt("P0a", task="manipulation") != load_prompt("P0b", task="manipulation")


# --- P0: hand-count only, one canonical source ------------------------------------------------


def test_p0_hand_count_is_non_empty_and_stable() -> None:
    text = load_prompt("P0", task="hand_count")
    assert text
    # Whichever source is canonical, P0 must be single-valued -- never silently alias two
    # different byte sequences for what's supposed to be one prompt run once.
    assert text == load_prompt("P0", task="hand_count")


def test_p0_hand_count_matches_its_documented_canonical_source() -> None:
    # prompts.py's docstring names P0b as canonical for hand_count P0 (identical to P0a apart
    # from an apostrophe glyph and incidental whitespace, per PRE-REGISTRATION.md).
    assert load_prompt("P0", task="hand_count") == load_prompt("P0b", task="hand_count")


def test_p0_manipulation_is_not_supported() -> None:
    # Unlike hand_count, active_manipulation's P0a/P0b genuinely diverge (D014) -- there is no
    # single unified "P0" for that task.
    with pytest.raises(Exception):
        load_prompt("P0", task="manipulation")


# --- P1-P4: hand-count rule variants, relative to P0b -----------------------------------------


def test_p1_tightens_hand_rule_and_drops_fingertip_clause() -> None:
    base = load_prompt("P0b", task="hand_count")
    p1 = load_prompt("P1", task="hand_count")
    assert p1 != base
    assert "fingertips" not in p1
    assert "clearly and unambiguously visible" in p1
    assert "fingertips" in base


def test_p2_drops_fingertip_clause_only() -> None:
    base = load_prompt("P0b", task="hand_count")
    p2 = load_prompt("P2", task="hand_count")
    assert p2 != base
    assert "fingertips" not in p2
    # P2 does not tighten the rule the way P1 does -- isolating the fingertip line alone.
    assert "Only count hands that are directly visible." in p2


def test_p3_adds_gloved_hand_instruction() -> None:
    base = load_prompt("P0b", task="hand_count")
    p3 = load_prompt("P3", task="hand_count")
    assert p3 != base
    assert "glove" in p3.lower()
    assert "glove" not in base.lower()


def test_p4_adds_reflection_screen_exclusion() -> None:
    base = load_prompt("P0b", task="hand_count")
    p4 = load_prompt("P4", task="hand_count")
    assert p4 != base
    assert "reflection" in p4.lower()
    assert "reflection" not in base.lower()


# --- P5-P6: manipulation definition variants, relative to P0b ---------------------------------


def test_p5_narrows_manipulation_to_visible_contact() -> None:
    base = load_prompt("P0b", task="manipulation")
    p5 = load_prompt("P5", task="manipulation")
    assert p5 != base
    assert "contact" in p5.lower()
    assert "contact" not in base.lower()


def test_p6_widens_manipulation_to_reaching() -> None:
    base = load_prompt("P0b", task="manipulation")
    p6 = load_prompt("P6", task="manipulation")
    assert p6 != base
    assert "reaching" in p6.lower()
    assert "reaching" not in base.lower()


def test_p5_and_p6_diverge_from_each_other() -> None:
    assert load_prompt("P5", task="manipulation") != load_prompt("P6", task="manipulation")


# --- P7: response schema extended with a confidence value, both tasks -------------------------


@pytest.mark.parametrize("task", ["hand_count", "manipulation"])
def test_p7_adds_confidence_to_response_schema(task: str) -> None:
    base = load_prompt("P0b", task=task)
    p7 = load_prompt("P7", task=task)
    assert p7 != base
    assert "confidence" in p7.lower()
    assert "confidence" not in base.lower()


# --- variants applied to the task they don't describe fall back to P0b unmodified -------------


def test_hand_rule_variant_is_unmodified_on_manipulation_task() -> None:
    # P1-P4 describe changes to the hand-count rule only; PRE-REGISTRATION.md gives them no
    # documented effect on the manipulation task, so they must not silently invent one.
    assert load_prompt("P1", task="manipulation") == load_prompt("P0b", task="manipulation")


def test_manipulation_variant_is_unmodified_on_hand_count_task() -> None:
    assert load_prompt("P5", task="hand_count") == load_prompt("P0b", task="hand_count")


# --- invalid task -------------------------------------------------------------------------------


@pytest.mark.parametrize("variant", ["P0a", "P0b", "P1", "P7"])
def test_invalid_task_raises(variant: PromptVariant) -> None:
    with pytest.raises(Exception):
        load_prompt(variant, task="active_manipulation")  # wrong spelling of "manipulation"


def test_unrelated_invalid_task_raises() -> None:
    with pytest.raises(Exception):
        load_prompt("P0b", task="not_a_real_task")
