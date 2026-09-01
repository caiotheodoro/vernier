"""Behavioural tests for the free functions in `vernier.judges.base`: response parsing and
status classification shared by every judge adapter against Build AI's published JSON schema
(`hand_count` int, `answer` yes/no enum -- `docs/UPSTREAM-FINDINGS.md` F1).
"""

from __future__ import annotations

import pytest

from vernier.judges.base import build_confidence, parse_hand_count_response, parse_manipulation_response
from vernier.models import Confidence

# --- parse_hand_count_response ---------------------------------------------------------

def test_well_formed_hand_count_is_ok() -> None:
    assert parse_hand_count_response('{"hand_count": 2}') == (2, "ok")


def test_hand_count_zero_is_ok() -> None:
    assert parse_hand_count_response('{"hand_count": 0}') == (0, "ok")


def test_hand_count_out_of_range_is_unparseable() -> None:
    assert parse_hand_count_response('{"hand_count": 3}') == (None, "unparseable")


def test_hand_count_negative_is_unparseable() -> None:
    assert parse_hand_count_response('{"hand_count": -1}') == (None, "unparseable")


def test_hand_count_wrong_type_is_unparseable() -> None:
    assert parse_hand_count_response('{"hand_count": "2"}') == (None, "unparseable")


def test_hand_count_bool_is_unparseable() -> None:
    # bool is a subclass of int in Python -- must not silently accept True/False as 0/1.
    assert parse_hand_count_response('{"hand_count": true}') == (None, "unparseable")


def test_hand_count_missing_key_is_unparseable() -> None:
    assert parse_hand_count_response('{"other_field": 1}') == (None, "unparseable")


def test_hand_count_json_in_markdown_fence_parses() -> None:
    raw = '```json\n{"hand_count": 1}\n```'
    assert parse_hand_count_response(raw) == (1, "ok")


def test_hand_count_json_embedded_in_prose_parses() -> None:
    raw = 'Sure, here is the result: {"hand_count": 2} -- hope that helps.'
    assert parse_hand_count_response(raw) == (2, "ok")


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
    assert parse_manipulation_response('{"answer": "yes"}') == (True, "ok")


def test_manipulation_no_is_ok_false() -> None:
    assert parse_manipulation_response('{"answer": "no"}') == (False, "ok")


def test_manipulation_invalid_enum_value_is_unparseable() -> None:
    assert parse_manipulation_response('{"answer": "maybe"}') == (None, "unparseable")


def test_manipulation_wrong_type_is_unparseable() -> None:
    assert parse_manipulation_response('{"answer": true}') == (None, "unparseable")


def test_manipulation_missing_key_is_unparseable() -> None:
    assert parse_manipulation_response('{"hand_count": 1}') == (None, "unparseable")


def test_manipulation_refusal_language_is_refused() -> None:
    raw = "I can't help with identifying actions in images of people."
    assert parse_manipulation_response(raw) == (None, "refused")


def test_manipulation_non_json_non_refusal_is_unparseable() -> None:
    assert parse_manipulation_response("worker appears to be idle") == (None, "unparseable")


# --- build_confidence --------------------------------------------------------------------

def test_p7_style_response_builds_verbalized_confidence() -> None:
    raw = '{"answer": "yes", "confidence": 0.87}'
    confidence = build_confidence(raw)
    assert confidence == Confidence(kind="verbalized", value=0.87)
    # Round-trips through the actual pydantic model.
    reloaded = Confidence.model_validate_json(confidence.model_dump_json())
    assert reloaded == confidence


def test_p0_style_response_with_no_confidence_field_builds_none_kind() -> None:
    raw = '{"hand_count": 2}'
    confidence = build_confidence(raw)
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_out_of_range_falls_back_to_none_kind() -> None:
    raw = '{"answer": "yes", "confidence": 1.5}'
    confidence = build_confidence(raw)
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_wrong_type_falls_back_to_none_kind() -> None:
    raw = '{"answer": "yes", "confidence": "high"}'
    confidence = build_confidence(raw)
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_null_field_builds_none_kind() -> None:
    raw = '{"answer": "yes", "confidence": null}'
    confidence = build_confidence(raw)
    assert confidence == Confidence(kind="none", value=None)


def test_confidence_unparseable_raw_builds_none_kind() -> None:
    confidence = build_confidence("not json at all")
    assert confidence == Confidence(kind="none", value=None)


@pytest.mark.parametrize("value", [0.0, 1.0])
def test_confidence_boundary_values_are_verbalized(value: float) -> None:
    raw = f'{{"answer": "no", "confidence": {value}}}'
    assert build_confidence(raw) == Confidence(kind="verbalized", value=value)
