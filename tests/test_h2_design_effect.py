"""Behavioural tests for `scripts/h2_design_effect.py`.

The statistics are pure and offline-testable: outcomes plus cluster ids in, intervals and a
design effect out. `docs/WAVES.md` requires a golden case with a hand-computable answer for a
statistical unit, and clustering has two: an ICC of exactly 0 must give a design effect of
about 1, and an ICC of exactly 1 with equal cluster sizes must give about the cluster size.
Both are asserted below against real bootstrap output, not mocked.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from h2_design_effect import (  # noqa: E402
    HEADLINE_TASKS,
    cluster_size_summary,
    design_effects,
    outcomes_from_responses,
)
from vernier.models import Confidence, JudgeResponse  # noqa: E402

_B = 400  # small B keeps the suite fast; the real run uses CLUSTER_BOOTSTRAP_B = 10,000


def _response(
    frame_id: str, hands: Literal[0, 1, 2] | None, manip: bool | None, status: str = "ok"
) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="qwen3-vl-8b",
        judge_rev="test",
        prompt_variant="P0a",
        hands_visible=hands,
        manipulation=manip,
        confidence=Confidence(kind="none", value=None),
        raw="{}",
        status=status,  # type: ignore[arg-type]
        latency_ms=1,
        cost_usd=0.0,
    )


# --- the two golden cases -------------------------------------------------------------


def test_design_effect_is_about_one_when_every_cluster_holds_one_frame() -> None:
    """ICC is undefined-to-zero with singleton clusters: resampling clusters and resampling
    rows are the same operation, so the two intervals must have the same width."""
    values = [float(i % 2) for i in range(400)]
    clusters = [f"w{i}" for i in range(400)]

    result = design_effects({"t": values}, clusters, B=_B, seed=777)

    assert result["t"]["design_effect"] == pytest.approx(1.0, abs=0.25)


def test_design_effect_is_about_the_cluster_size_when_a_cluster_is_perfectly_correlated() -> None:
    """The textbook identity: deff = 1 + (m - 1) * ICC. With every frame in a cluster carrying
    the identical value, ICC is 1, so deff must land near m -- here 10.

    This is the case H2 is actually asking about. If frames from one worker were perfectly
    redundant, 10,000 frames from 1,000 workers would carry the information of 1,000.
    """
    values: list[float] = []
    clusters: list[str] = []
    for worker in range(100):
        value = float(worker % 2)
        values.extend([value] * 10)
        clusters.extend([f"w{worker}"] * 10)

    result = design_effects({"t": values}, clusters, B=_B, seed=777)

    assert result["t"]["design_effect"] == pytest.approx(10.0, rel=0.35)


def test_both_intervals_are_reported_and_labelled() -> None:
    """`CONTRACTS.md`: an iid interval is never reported as though it were the real one. Both
    arms are kept so the card can show the effect rather than assert it."""
    values = [float(i % 3 == 0) for i in range(200)]
    clusters = [f"w{i // 4}" for i in range(200)]

    result = design_effects({"t": values}, clusters, B=_B, seed=777)

    assert result["t"]["iid"]["method"] == "iid"
    assert result["t"]["cluster"]["method"] == "cluster-bootstrap"
    assert result["t"]["cluster"]["clusters"] == 50
    assert result["t"]["cluster"]["B"] == _B


def test_a_task_with_no_usable_outcomes_is_recorded_as_absent_not_dropped() -> None:
    """`CONTRACTS.md` rule 2: absence is explicit. A task every judge call refused must not
    silently vanish from the result and read as "not measured yet"."""
    result = design_effects({"t": []}, [], B=_B, seed=777)

    assert result["t"]["design_effect"] is None
    assert result["t"]["why_absent"]


# --- outcome extraction ---------------------------------------------------------------


def test_outcomes_cover_the_three_headline_figures() -> None:
    responses = [
        _response("a", 2, True),
        _response("b", 1, False),
        _response("c", 0, False),
    ]

    outcomes, kept = outcomes_from_responses(responses)

    assert set(outcomes) == set(HEADLINE_TASKS)
    assert outcomes["hand_ge1"] == [1.0, 1.0, 0.0]
    assert outcomes["hand_eq2"] == [1.0, 0.0, 0.0]
    assert outcomes["active_manipulation"] == [1.0, 0.0, 0.0]
    assert kept == ["a", "b", "c"]


def test_non_ok_responses_are_excluded_from_the_denominator() -> None:
    """`CONTRACTS.md` rule 2 again, and the exact class of error this project exists to catch:
    silently counting a refusal as a negative inflates agreement."""
    responses = [
        _response("a", 2, True),
        _response("b", None, None, status="refused"),
        _response("c", 1, True),
    ]

    outcomes, kept = outcomes_from_responses(responses)

    assert kept == ["a", "c"]
    assert outcomes["hand_ge1"] == [1.0, 1.0]


# --- cluster shape, which is what makes a design effect interpretable -----------------


def test_cluster_size_summary_reports_the_spread_not_just_the_mean() -> None:
    """Unequal cluster sizes inflate the design effect on their own, independently of ICC. A
    deff reported without the size spread cannot be read."""
    clusters = ["w0"] * 5 + ["w1"] * 1 + ["w2"] * 2

    summary = cluster_size_summary(clusters)

    assert summary["n_clusters"] == 3
    assert summary["n_observations"] == 8
    assert summary["mean_cluster_size"] == pytest.approx(8 / 3)
    assert summary["max_cluster_size"] == 5
    assert summary["min_cluster_size"] == 1
