"""Behavioural tests for `scripts/wave4_analysis.py`'s pure computation functions, against
synthetic `HumanLabel`/`JudgeResponse` fixtures -- no real files, no live judge, no network.
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from wave4_analysis import (  # noqa: E402
    _calibration,
    _h4,
    _h5,
    _intra_rater_ac1,
    _ppi_per_domain,
    _retest_separation,
)

from vernier.models import Confidence, HumanLabel, JudgeResponse


def _label(frame_id: str, hands_visible: int, manipulation: bool) -> HumanLabel:
    return HumanLabel.model_validate(
        {
            "frame_id": frame_id,
            "rater": "R1",
            "pass": "primary",
            "rubric_rev": "1.2.0",
            "hands_visible": hands_visible,
            "manipulation": manipulation,
            "edge_case": [],
            "difficulty": "easy",
            "note": "",
            "labelled_at": datetime.now(timezone.utc).isoformat(),
            "seconds_spent": 10,
        }
    )


def _response(
    frame_id: str, hands_visible: int, manipulation: bool, confidence: float | None = None
) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="qwen3-vl",
        judge_rev="rev",
        prompt_variant="P0b",
        hands_visible=hands_visible,  # type: ignore[arg-type]
        manipulation=manipulation,
        confidence=(
            Confidence(kind="none", value=None)
            if confidence is None
            else Confidence(kind="logprob", value=confidence)
        ),
        raw="raw",
        status="ok",
        latency_ms=10,
        cost_usd=0.0001,
    )


def test_intra_rater_ac1_is_one_on_perfect_agreement() -> None:
    primary = [_label(f"f{i}", 1, True) for i in range(10)]
    retest = [_label(f"f{i}", 1, True) for i in range(10)]

    ac1, n = _intra_rater_ac1(primary, retest, "manipulation")

    assert n == 10
    assert ac1 == 1.0


def test_intra_rater_ac1_only_counts_matched_frame_ids() -> None:
    primary = [_label("f0", 1, True), _label("f1", 0, False)]
    retest = [_label("f0", 1, True), _label("f-unrelated", 2, False)]

    _, n = _intra_rater_ac1(primary, retest, "manipulation")

    assert n == 1  # only f0 appears in both


def test_h4_reports_higher_ac1_for_hand_count_when_true(monkeypatch: object) -> None:
    # Perfect hand_count agreement, imperfect manipulation agreement.
    primary = [_label(f"f{i}", 1, i % 2 == 0) for i in range(10)]
    responses = [_response(f"f{i}", 1, True) for i in range(10)]  # always "True" -> half wrong

    result = _h4(primary, {"G200-ego": responses})

    assert result["hand_count"]["ac1"] == 1.0
    assert result["manipulation"]["ac1"] < 1.0
    assert result["holds"] is True
    for task in ("hand_count", "manipulation"):
        ci = result[task]["ac1_ci"]
        assert ci["method"] == "iid"
        assert ci["lo"] <= result[task]["ac1"] <= ci["hi"]


def test_h5_computes_real_pp_difference_between_domains() -> None:
    ego_labels = [_label(f"ego{i}", 1, True) for i in range(10)]
    epic_labels = [_label(f"epic{i}", 1, True) for i in range(10)]
    primary = ego_labels + epic_labels

    # judge is perfect on ego, wrong on half of epic
    ego_responses = [_response(f"ego{i}", 1, True) for i in range(10)]
    epic_responses = [_response(f"epic{i}", 1, i % 2 == 0) for i in range(10)]

    judged_by_sample = {"G200-ego": ego_responses, "G200-epic": epic_responses}
    frame_ids_by_sample = {
        "G200-ego": {label.frame_id for label in ego_labels},
        "G200-epic": {label.frame_id for label in epic_labels},
    }

    result = _h5(primary, judged_by_sample, frame_ids_by_sample)  # type: ignore[arg-type]

    assert result["egocentric"]["error_rate"] == 0.0
    assert result["epic_kitchens"]["error_rate"] == 0.5
    assert result["diff_pp"] == 50.0
    assert result["holds"] is True
    assert result["epic_kitchens_higher"] is True


def test_ppi_per_domain_returns_a_real_estimate_with_gold_and_unlabelled_split() -> None:
    # 5 gold frames (primary-labelled), 15 more real judged-only frames in the same arm pool.
    gold_labels = [_label(f"g{i}", 1, True) for i in range(5)]
    gold_responses = [_response(f"g{i}", 1, True) for i in range(5)]
    unlabelled_responses = [_response(f"u{i}", 1, True) for i in range(15)]
    responses = gold_responses + unlabelled_responses

    judged_by_sample = {"G200-ego": responses}
    frame_ids_by_sample = {"G200-ego": {label.frame_id for label in gold_labels} | {f"u{i}" for i in range(15)}}

    result = _ppi_per_domain(gold_labels, judged_by_sample, frame_ids_by_sample)  # type: ignore[arg-type]

    manipulation_est = result["G200-ego"]["manipulation"]
    assert manipulation_est["ppi"]["n_gold"] == 5
    assert manipulation_est["ppi"]["n_unlabelled"] == 15
    assert manipulation_est["published"] == 0.9166  # PRE-REGISTRATION.md's real Egocentric-10K figure


def test_calibration_only_uses_frames_with_real_logprob_confidence() -> None:
    primary = [_label("f0", 1, True), _label("f1", 1, True), _label("f2", 1, True)]
    responses = [
        _response("f0", 1, True, confidence=0.95),  # correct, high confidence
        _response("f1", 0, True, confidence=0.5),  # wrong on hand_count, mid confidence
        _response("f2", 1, True, confidence=None),  # no usable confidence -- excluded
    ]

    result = _calibration(primary, {"G200-ego": responses})

    assert result["hand_count"]["n"] == 2  # f2 excluded (no logprob confidence)
    assert result["manipulation"]["n"] == 2
    assert result["hand_count"]["judge"] == "qwen3-vl"
    assert result["hand_count"]["confidence_kind"] == "logprob"


def test_calibration_reports_perfect_ece_when_confidence_matches_accuracy_exactly() -> None:
    # 10 frames, all correct, all confidence 1.0 -> the top bin's mean_conf == accuracy == 1.0.
    primary = [_label(f"f{i}", 1, True) for i in range(10)]
    responses = [_response(f"f{i}", 1, True, confidence=1.0) for i in range(10)]

    result = _calibration(primary, {"G200-ego": responses})

    assert result["hand_count"]["ece"] == pytest.approx(0.0)
    assert result["manipulation"]["ece"] == pytest.approx(0.0)


def _label_at(frame_id: str, pass_: str, when: datetime) -> HumanLabel:
    return HumanLabel.model_validate(
        {
            "frame_id": frame_id,
            "rater": "R1",
            "pass": pass_,
            "rubric_rev": "1.2.0",
            "hands_visible": 2,
            "manipulation": True,
            "edge_case": [],
            "difficulty": "easy",
            "note": "",
            "labelled_at": when.isoformat(),
            "seconds_spent": 10,
        }
    )


def test_retest_separation_measures_the_real_gap_and_counts_pairs_meeting_the_rule() -> None:
    """D076: the pre-registration asks for >=7 days and the delivered data is hours apart, so
    the gap is measured from the labels rather than asserted from the protocol."""
    t0 = datetime(2026, 9, 3, 4, 15, tzinfo=timezone.utc)
    primary = [_label_at("a", "primary", t0), _label_at("b", "primary", t0)]
    retest = [
        _label_at("a", "retest", t0 + timedelta(hours=2, minutes=24)),
        _label_at("b", "retest", t0 + timedelta(days=8)),
    ]
    sep = _retest_separation(primary, retest)
    assert sep["n_pairs"] == 2
    assert sep["min_days"] == pytest.approx(0.1, abs=1e-3)
    assert sep["max_days"] == pytest.approx(8.0)
    assert sep["required_days"] == 7.0
    assert sep["n_pairs_meeting_requirement"] == 1


def test_retest_separation_says_why_it_is_absent_rather_than_reporting_a_zero_gap() -> None:
    t0 = datetime(2026, 9, 3, 4, 15, tzinfo=timezone.utc)
    sep = _retest_separation([_label_at("a", "primary", t0)], [_label_at("z", "retest", t0)])
    assert sep["n_pairs"] == 0
    assert "why_absent" in sep
