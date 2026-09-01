"""Behavioural tests for the free functions in `vernier.judges.base`: response parsing and
status classification shared by every judge adapter against the real, shipped bare-value
answer format (`0`/`1`/`2`, `yes`/`no`, P7 adds a comma-separated confidence -- never JSON,
`docs/DECISIONS.md` D043).
"""

from __future__ import annotations

import pytest

from vernier.judges.base import build_confidence, parse_hand_count_response, parse_manipulation_response
from vernier.models import Confidence

# --- parse_hand_count_response ---------------------------------------------------------

def test_well_formed_hand_count_is_ok() -> None:
    assert parse_hand_count_response("2") == (2, "ok")


def test_hand_count_zero_is_ok() -> None:
    assert parse_hand_count_response("0") == (0, "ok")


def test_hand_count_out_of_range_is_unparseable() -> None:
    assert parse_hand_count_response("3") == (None, "unparseable")


def test_hand_count_negative_is_unparseable() -> None:
    assert parse_hand_count_response("-1") == (None, "unparseable")


def test_hand_count_wrong_kind_of_value_is_unparseable() -> None:
    # A manipulation-shaped answer to the hand-count prompt: recognizable value token, wrong task.
    assert parse_hand_count_response("yes") == (None, "unparseable")


def test_hand_count_tolerates_surrounding_quotes_and_trailing_period() -> None:
    assert parse_hand_count_response('"2".') == (2, "ok")


def test_hand_count_p7_style_with_confidence_still_extracts_the_value() -> None:
    assert parse_hand_count_response("1, 0.85") == (1, "ok")


def test_hand_count_extra_prose_is_unparseable() -> None:
    # "No extra words" is part of the instruction -- violating it is a real deviation, not
    # something to be lenient about by extracting a value out of surrounding prose.
    raw = "Sure, here is the result: 2 -- hope that helps."
    assert parse_hand_count_response(raw) == (None, "unparseable")


def test_hand_count_refusal_language_is_refused() -> None:
    raw = "I'm sorry, but I cannot analyze this image."
    assert parse_hand_count_response(raw) == (None, "refused")


def test_hand_count_unable_to_assist_is_refused() -> None:
    raw = "As an AI, I am unable to view or process image content."
    assert parse_hand_count_response(raw) == (None, "refused")


def test_hand_count_garbled_non_refusal_text_is_unparseable() -> None:
    raw = "the image shows a workbench with tools scattered around it"
    assert parse_hand_count_response(raw) == (None, "unparseable")


def test_hand_count_empty_string_is_unparseable() -> None:
    assert parse_hand_count_response("") == (None, "unparseable")


# --- parse_manipulation_response --------------------------------------------------------

def test_manipulation_yes_is_ok_true() -> None:
    assert parse_manipulation_response("yes") == (True, "ok")


def test_manipulation_no_is_ok_false() -> None:
    assert parse_manipulation_response("no") == (False, "ok")


def test_manipulation_is_case_insensitive() -> None:
    assert parse_manipulation_response("Yes") == (True, "ok")
    assert parse_manipulation_response("NO") == (False, "ok")


def test_manipulation_invalid_enum_value_is_unparseable() -> None:
    assert parse_manipulation_response("maybe") == (None, "unparseable")


def test_manipulation_wrong_kind_of_value_is_unparseable() -> None:
    assert parse_manipulation_response("2") == (None, "unparseable")


def test_manipulation_p7_style_with_confidence_still_extracts_the_value() -> None:
    assert parse_manipulation_response("no, 0.42") == (False, "ok")


def test_manipulation_refusal_language_is_refused() -> None:
    raw = "I can't help with identifying actions in images of people."
    assert parse_manipulation_response(raw) == (None, "refused")


def test_manipulation_non_json_non_refusal_is_unparseable() -> None:
    assert parse_manipulation_response("worker appears to be idle") == (None, "unparseable")


# --- build_confidence --------------------------------------------------------------------

def test_p7_style_response_builds_verbalized_confidence() -> None:
    confidence = build_confidence("yes, 0.87")
    assert confidence == Confidence(kind="verbalized", value=0.87)
    # Round-trips through the actual pydantic model.
    reloaded = Confidence.model_validate_json(confidence.model_dump_json())
    assert reloaded == confidence


def test_p0_style_response_with_no_confidence_builds_none_kind() -> None:
    confidence = build_confidence("2")
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_out_of_range_falls_back_to_none_kind() -> None:
    confidence = build_confidence("yes, 1.5")
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_unparseable_raw_builds_none_kind() -> None:
    confidence = build_confidence("not a recognizable answer at all")
    assert confidence == Confidence(kind="none", value=None)


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_confidence_boundary_values_are_verbalized(value: float) -> None:
    assert build_confidence(f"no, {value}") == Confidence(kind="verbalized", value=value)
