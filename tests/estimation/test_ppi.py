"""Behavioural tests for `vernier.estimation.ppi`.

Golden-case coverage per docs/WAVES.md ("tests are schema tests, not scientific tests"), plus
the project's own statistical bar for this specific unit (docs/DECISIONS.md D021/D030 -- PPI is
the primary estimator and its citation has already been wrong once):

(a) a judge with a known, constant positive-report bias -- PPI's corrected value must land
    closer to the constructed true prevalence than the naive judge-only mean, and match a
    hand-computed expected value from the PPI formula exactly;
(b) judge and gold agree perfectly -- rectifier ~= 0 and PPI's value == the naive value;
(c)/(d) `PPIBlock`'s `clustered`/`cluster_by`/`why_not_clustered` fields validate in both the
    clustered and unclustered call paths; the clustered path monkeypatches
    `cluster_bootstrap_ci` (its own unit, `vernier.estimation.bootstrap`, is still a stub) so
    this unit's tests never depend on that sibling's implementation status.
"""

from __future__ import annotations

import pytest

from tests.fixtures import make_human_label, make_judge_response
from vernier.estimation import ppi as ppi_mod
from vernier.estimation.ppi import estimate_prevalence, ppi_estimate
from vernier.models import AgreementCI, HumanLabel, JudgeResponse, PPIBlock


def _gold_frame(i: int, *, true_positive: bool, judge_says: bool) -> tuple[HumanLabel, JudgeResponse]:
    frame_id = f"gold-{i}"
    gold = make_human_label(
        frame_id=frame_id,
        manipulation=true_positive,
        hands_visible=2 if true_positive else 0,
    )
    judged = make_judge_response(
        frame_id=frame_id,
        manipulation=judge_says,
        hands_visible=2 if judge_says else 0,
    )
    return gold, judged


def _unlabelled_frame(i: int, *, judge_says: bool) -> JudgeResponse:
    return make_judge_response(
        frame_id=f"unlabelled-{i}",
        manipulation=judge_says,
        hands_visible=2 if judge_says else 0,
    )


def _biased_judge_dataset() -> tuple[list[HumanLabel], list[JudgeResponse]]:
    """20 gold frames: 10 true positives (judge always right), 10 true negatives of which the
    judge over-calls 6 as positive (a constant +0.3 over-report bias: judge mean 0.8 vs gold
    mean 0.5). 200 unlabelled frames carry the same +0.3 judge-positive rate (80% positive).

    PPI's correction does not need or assume a true rate for the unlabelled pool -- it applies
    the gold-estimated bias (+0.3) to the unlabelled judge mean regardless. Since the judge's
    bias is constructed identically on both pools, the corrected estimate should land near the
    gold pool's own true rate (0.5), not the judge's raw 0.8 -- that gap, not any claim about
    the unlabelled pool's unobserved truth, is what this test actually checks.
    """
    gold: list[HumanLabel] = []
    judged: list[JudgeResponse] = []
    for i in range(10):
        h, j = _gold_frame(i, true_positive=True, judge_says=True)
        gold.append(h)
        judged.append(j)
    for i in range(10, 20):
        judge_over_calls = i < 16  # 6 of the 10 true-negative frames: indices 10..15
        h, j = _gold_frame(i, true_positive=False, judge_says=judge_over_calls)
        gold.append(h)
        judged.append(j)

    for i in range(200):
        judged.append(_unlabelled_frame(i, judge_says=i < 160))  # 160/200 = 0.8, matching the bias

    return gold, judged


def _agreeing_dataset() -> tuple[list[HumanLabel], list[JudgeResponse]]:
    """Judge and gold agree on every gold frame, and the unlabelled judge rate matches too --
    no bias anywhere, so PPI should not move the estimate at all."""
    gold: list[HumanLabel] = []
    judged: list[JudgeResponse] = []
    for i in range(20):
        positive = i < 12  # 12/20 = 0.6
        h, j = _gold_frame(i, true_positive=positive, judge_says=positive)
        gold.append(h)
        judged.append(j)

    for i in range(200):
        judged.append(_unlabelled_frame(i, judge_says=i < 120))  # 120/200 = 0.6, same rate

    return gold, judged


def test_ppi_corrects_a_known_constant_judge_bias_toward_the_true_rate() -> None:
    gold, judged = _biased_judge_dataset()

    naive_unlabelled_mean = sum(1 for i in range(200) if i < 160) / 200  # 0.8
    # method="ppi" fixes lambda=1 (classical PPI, no power-tuning) so the correction is
    # hand-computable directly from the formula in the module docstring:
    # rectifier = mean(gold) - mean(judge on gold) = 0.5 - 0.8 = -0.3
    # theta_hat = mean(judge on unlabelled) + rectifier = 0.8 - 0.3 = 0.5
    block = ppi_estimate(
        gold, judged, cluster_by=None, why_not_clustered="unit test, no clusters", method="ppi"
    )

    assert block.rectifier == pytest.approx(-0.3, abs=1e-9)
    assert block.value == pytest.approx(0.5, abs=1e-9)

    # Corrected estimate must be closer to the constructed true rate (0.5) than the naive
    # judge-only mean (0.8) is.
    true_rate = 0.5
    assert abs(block.value - true_rate) < abs(naive_unlabelled_mean - true_rate)


def test_ppi_plus_plus_also_corrects_toward_the_true_rate_via_a_tuned_lambda() -> None:
    """Same biased data, default `method="ppi++"`: the power-tuning coefficient lambda is
    computed from the gold sample's covariance/variance rather than fixed at 1, but must still
    pull the estimate toward the true rate, not away from it or past it."""
    gold, judged = _biased_judge_dataset()

    naive_unlabelled_mean = 0.8
    block = ppi_estimate(gold, judged, cluster_by=None, why_not_clustered="unit test, no clusters")

    true_rate = 0.5
    assert abs(block.value - true_rate) < abs(naive_unlabelled_mean - true_rate)
    assert block.method == "ppi++"


def test_ppi_matches_naive_when_judge_and_gold_agree_perfectly() -> None:
    gold, judged = _agreeing_dataset()

    naive_unlabelled_mean = 0.6
    block = ppi_estimate(gold, judged, cluster_by=None, why_not_clustered="unit test, no clusters")

    assert block.rectifier == pytest.approx(0.0, abs=1e-9)
    assert block.value == pytest.approx(naive_unlabelled_mean, abs=1e-9)


def test_ppi_block_unclustered_fields_round_trip_the_validator() -> None:
    gold, judged = _biased_judge_dataset()

    block = ppi_estimate(gold, judged, cluster_by=None, why_not_clustered="no participant id available")

    assert block.clustered is False
    assert block.cluster_by is None
    assert block.why_not_clustered == "no participant id available"
    # Round-trips through the real pydantic model without the validator raising.
    PPIBlock.model_validate(block.model_dump())


def test_ppi_block_clustered_fields_round_trip_the_validator(monkeypatch: pytest.MonkeyPatch) -> None:
    gold, judged = _biased_judge_dataset()

    captured: dict[str, object] = {}

    def _fake_cluster_bootstrap_ci(
        values: list[float], cluster_ids: list[str] | None, **kwargs: object
    ) -> AgreementCI:
        captured["values"] = values
        captured["cluster_ids"] = cluster_ids
        return AgreementCI(lo=0.4, hi=0.6, method="cluster-bootstrap", clusters=len(set(cluster_ids or [])), B=2000)

    monkeypatch.setattr(ppi_mod, "cluster_bootstrap_ci", _fake_cluster_bootstrap_ci)

    block = ppi_estimate(gold, judged, cluster_by="rater")

    assert block.clustered is True
    assert block.cluster_by == "rater"
    assert block.why_not_clustered is None
    # Round-trips through the real pydantic model without the validator raising.
    PPIBlock.model_validate(block.model_dump())

    # The mock actually got called with the gold-residual series, clustered by `rater`.
    assert captured["cluster_ids"] == [h.rater for h in gold]
    assert len(captured["values"]) == len(gold)  # type: ignore[arg-type]


def test_ppi_uses_the_mocked_clustered_ci_to_build_the_final_interval(monkeypatch: pytest.MonkeyPatch) -> None:
    gold, judged = _agreeing_dataset()

    def _fake_cluster_bootstrap_ci(
        values: list[float], cluster_ids: list[str] | None, **kwargs: object
    ) -> AgreementCI:
        return AgreementCI(lo=-0.1, hi=0.1, method="cluster-bootstrap", clusters=5, B=2000)

    monkeypatch.setattr(ppi_mod, "cluster_bootstrap_ci", _fake_cluster_bootstrap_ci)

    block = ppi_estimate(gold, judged, cluster_by="rater")

    # theta_hat is unaffected by which CI method rectifies its width (still ~0.6, agreeing data).
    assert block.value == pytest.approx(0.6, abs=1e-9)
    # But the interval is derived from the mocked cluster CI, not the analytic iid one -- it
    # must be centred on theta_hat and have finite positive width.
    assert block.ci.hi > block.ci.lo
    assert block.ci.lo < block.value < block.ci.hi


def test_ppi_estimate_rejects_empty_gold() -> None:
    with pytest.raises(ValueError):
        ppi_estimate([], [], cluster_by=None, why_not_clustered="n/a")


def test_ppi_estimate_rejects_unknown_method() -> None:
    gold, judged = _agreeing_dataset()
    with pytest.raises(ValueError):
        ppi_estimate(gold, judged, cluster_by=None, why_not_clustered="n/a", method="bogus")


def test_ppi_estimate_requires_a_judge_prediction_for_every_gold_frame() -> None:
    gold = [make_human_label(frame_id="orphan-gold", manipulation=True)]
    judged = [_unlabelled_frame(i, judge_says=True) for i in range(5)]
    with pytest.raises(ValueError):
        ppi_estimate(gold, judged, cluster_by=None, why_not_clustered="n/a")


# --- estimate_prevalence -------------------------------------------------------------------


def test_estimate_prevalence_assembles_naive_ppi_and_published() -> None:
    gold, judged = _biased_judge_dataset()
    # Give every record a matching judge/prompt_variant so estimate_prevalence's filter keeps them.
    judged = [j.model_copy(update={"judge": "gemini-2.5-flash", "prompt_variant": "P0a"}) for j in judged]

    result = estimate_prevalence(
        "egocentric-10k",
        "manipulation",
        "P0a",
        "gemini-2.5-flash",
        gold,
        judged,
        published=0.9166,
        cluster_by=None,
        why_not_clustered="unit test, no clusters",
    )

    assert result.corpus == "egocentric-10k"
    assert result.task == "manipulation"
    assert result.prompt_variant == "P0a"
    assert result.judge == "gemini-2.5-flash"
    assert result.published == 0.9166
    assert result.naive.value == pytest.approx(0.8, abs=1e-9)
    assert result.naive.n == 220  # 20 gold-paired + 200 unlabelled, all task-matched
    assert result.ppi.value == pytest.approx(0.5, abs=1e-9)


def test_estimate_prevalence_filters_by_judge_and_prompt_variant() -> None:
    gold, judged = _agreeing_dataset()
    matching = [j.model_copy(update={"judge": "gemini-2.5-flash", "prompt_variant": "P0a"}) for j in judged]
    other_judge_noise = [
        make_judge_response(frame_id=f"noise-{i}", judge="qwen3-vl", prompt_variant="P0a", manipulation=True)
        for i in range(50)
    ]

    result = estimate_prevalence(
        "egocentric-10k",
        "manipulation",
        "P0a",
        "gemini-2.5-flash",
        gold,
        matching + other_judge_noise,
        published=0.6,
        cluster_by=None,
        why_not_clustered="unit test, no clusters",
    )

    # The other judge's 50 all-positive noise frames must not have moved naive.n or naive.value.
    assert result.naive.n == 220
    assert result.naive.value == pytest.approx(0.6, abs=1e-9)


def test_estimate_prevalence_hand_count_task_uses_at_least_one_hand_indicator() -> None:
    gold = [
        make_human_label(frame_id=f"h{i}", hands_visible=hv, manipulation=(hv >= 1))
        for i, hv in enumerate([0, 1, 2, 0, 1, 2, 0, 1, 2, 0])
    ]
    judged = [
        make_judge_response(
            frame_id=f"h{i}",
            judge="gemini-2.5-flash",
            prompt_variant="P0a",
            hands_visible=hv,
            manipulation=(hv >= 1),
        )
        for i, hv in enumerate([0, 1, 2, 0, 1, 2, 0, 1, 2, 0])
    ]
    unlabelled = [
        make_judge_response(
            frame_id=f"u{i}",
            judge="gemini-2.5-flash",
            prompt_variant="P0a",
            hands_visible=2 if i < 90 else 0,
            manipulation=(i < 90),
        )
        for i in range(100)
    ]

    result = estimate_prevalence(
        "egocentric-10k",
        "hand_count",
        "P0a",
        "gemini-2.5-flash",
        gold,
        judged + unlabelled,
        published=0.9642,
        cluster_by=None,
        why_not_clustered="unit test, no clusters",
    )

    # Gold "≥1 hand" rate: 6/10 = 0.6, exactly matching judge on gold here -> no rectification.
    assert result.ppi.rectifier == pytest.approx(0.0, abs=1e-9)
    # naive is the mean over the FULL task-matched judged sample (10 gold-paired + 100
    # unlabelled = 110), unlike ppi's internal unlabelled-only mean.
    assert result.naive.n == 110
    assert result.naive.value == pytest.approx(96 / 110, abs=1e-9)
    assert result.ppi.value == pytest.approx(0.9, abs=1e-9)  # 90/100 unlabelled frames >=1 hand
