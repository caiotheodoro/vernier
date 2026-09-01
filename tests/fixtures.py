"""Fixture generator for every record type in `CONTRACTS.md`.

Part of the Wave 0 gate: `ALL_VALID` builds one well-formed instance of each record, including
the "absence is explicit" cases (`refused`/`unparseable`/`timeout`/`error` `JudgeResponse`s and
an unclustered `PrevalenceEstimate`). `ALL_MALFORMED` holds raw payloads that violate a stated
invariant and must fail `model_validate`, keyed by the model that should reject them.
"""

from __future__ import annotations

from datetime import datetime, timezone

from vernier.models import (
    AgreementCI,
    AgreementResult,
    CalibrationBin,
    CalibrationReport,
    CardInterval,
    Claim,
    Comparison,
    Confidence,
    FrameRef,
    HumanLabel,
    JudgeResponse,
    JudgeStatus,
    MeasurementCard,
    NaivePrevalence,
    PPIBlock,
    PPICI,
    PrevalenceEstimate,
    ProbeCI,
    ProbeResult,
    UncheckedItem,
)

FRAME_ID = "ego10k/f0051/w00243/v0007/000418"


def make_frame_ref(**overrides: object) -> FrameRef:
    payload: dict[str, object] = dict(
        frame_id=FRAME_ID,
        corpus="egocentric-10k",
        corpus_rev="d74b7883c998dd360e3f051830fcc792a83985e6",
        factory_id="0051",
        worker_id="00243",
        clip_id="0007",
        frame_index=418,
        timestamp_s=13.933,
        width=1920,
        height=1080,
        fps=30.0,
        codec="hevc",
        sample="S10k-U",
        stratum="factory-0051",
        why_no_provenance=None,
    )
    payload.update(overrides)
    return FrameRef.model_validate(payload)


def make_judge_response(*, status: JudgeStatus = "ok", **overrides: object) -> JudgeResponse:
    payload: dict[str, object] = dict(
        frame_id=FRAME_ID,
        judge="gemini-2.5-flash",
        judge_rev="2025-06-01",
        prompt_variant="P0",
        hands_visible=2,
        manipulation=True,
        confidence=Confidence(kind="none", value=None),
        raw="2",
        status="ok",
        latency_ms=412,
        cost_usd=0.00031,
    )
    if status != "ok":
        payload["status"] = status
        payload["hands_visible"] = None
        payload["manipulation"] = None
        payload["raw"] = {
            "refused": "I can't help with that.",
            "unparseable": "probably two hands, hard to say",
            "timeout": "",
            "error": "",
        }[status]
    payload.update(overrides)
    return JudgeResponse.model_validate(payload)


def make_human_label(**overrides: object) -> HumanLabel:
    payload: dict[str, object] = dict(
        frame_id=FRAME_ID,
        rater="R1",
        pass_="primary",
        rubric_rev="1.2.0",
        hands_visible=2,
        manipulation=True,
        edge_case=["glove", "tool-occlusion"],
        difficulty="hard",
        note="left hand behind workpiece, thumb visible",
        labelled_at=datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        seconds_spent=22,
    )
    payload.update(overrides)
    return HumanLabel.model_validate(payload)


def make_agreement_result(**overrides: object) -> AgreementResult:
    payload: dict[str, object] = dict(
        comparison=Comparison(a="human:R1", b="gemini-2.5-flash:P0"),
        task="manipulation",
        subset="G200-ego",
        n=300,
        n_excluded=4,
        excluded_why={"unparseable": 3, "timeout": 1},
        raw_agreement=0.9067,
        ac1=0.727,
        kappa=0.612,
        ci=AgreementCI(lo=0.501, hi=0.714, method="cluster-bootstrap", clusters=61, B=10000),
        design_effect=2.31,
    )
    payload.update(overrides)
    return AgreementResult.model_validate(payload)


def make_prevalence_estimate(*, clustered: bool = False, **overrides: object) -> PrevalenceEstimate:
    ppi_payload: dict[str, object] = dict(
        value=0.8931,
        ci=PPICI(lo=0.8612, hi=0.9250, level=0.95),
        n_gold=200,
        n_unlabelled=10000,
        rectifier=-0.0235,
        method="ppi++",
        clustered=clustered,
        cluster_by="worker_id" if clustered else None,
        why_not_clustered=None if clustered else "frame_id is a bare UUID4; no grouping variable shipped",
    )
    payload: dict[str, object] = dict(
        corpus="egocentric-10k",
        task="manipulation",
        prompt_variant="P0a",
        judge="gemini-2.5-flash",
        naive=NaivePrevalence(value=0.9166, n=10000),
        ppi=PPIBlock.model_validate(ppi_payload),
        published=0.9166,
    )
    payload.update(overrides)
    return PrevalenceEstimate.model_validate(payload)


def make_calibration_report(**overrides: object) -> CalibrationReport:
    payload: dict[str, object] = dict(
        judge="gemini-2.5-flash",
        task="manipulation",
        subset="G200-ego",
        confidence_kind="verbalized",
        ece=0.083,
        bins=[
            CalibrationBin(lo=0.0, hi=0.1, n=0, mean_conf=None, accuracy=None),
            CalibrationBin(lo=0.9, hi=1.0, n=180, mean_conf=0.94, accuracy=0.91),
        ],
        note="empty bins are reported as empty, never merged away",
    )
    payload.update(overrides)
    return CalibrationReport.model_validate(payload)


def make_probe_result(**overrides: object) -> ProbeResult:
    payload: dict[str, object] = dict(
        source_corpus="egocentric-10k",
        n_frames=2000,
        backbone="facebook/dinov3-vits16-pretrain-lvd1689m",
        downstream="ego4d-fho-noun",
        metric="top1_accuracy",
        value=0.63,
        ci=ProbeCI(lo=0.60, hi=0.66, method="cluster-bootstrap"),
        seed=777,
        matched_on=["n_frames", "n_clusters", "training_steps"],
    )
    payload.update(overrides)
    return ProbeResult.model_validate(payload)


def make_measurement_card(**overrides: object) -> MeasurementCard:
    payload: dict[str, object] = dict(
        verdict="VERIFIED",
        claims=[
            Claim(
                statement="gemini-2.5-flash replicates the published manipulation figure within +/-2pp on E10k-ego.",
                record_type="PrevalenceEstimate",
                record_ref="egocentric-10k/manipulation/P0a/gemini-2.5-flash",
            )
        ],
        what_could_not_be_checked=[
            UncheckedItem(item="Calibration under P0a/P0b", reason="published schema exposes no confidence (H7)"),
        ],
        sample_definition="G200-ego, n=200, seed 777",
        rubric_rev="1.2.0",
        judge_revisions={"gemini-2.5-flash": "2025-06-01"},
        prompt_variants=["P0a", "P0b"],
        intervals=[
            CardInterval(
                label="manipulation AC1, human vs gemini-2.5-flash, G200-ego",
                ci=AgreementCI(lo=0.501, hi=0.714, method="cluster-bootstrap", clusters=61, B=10000),
                design_effect=2.31,
            )
        ],
        content_digest="sha256:0000000000000000000000000000000000000000000000000000000000000000",
    )
    payload.update(overrides)
    return MeasurementCard.model_validate(payload)


ALL_VALID = {
    "FrameRef": make_frame_ref(),
    "FrameRef.eval_arm_no_provenance": make_frame_ref(
        factory_id=None,
        worker_id=None,
        clip_id=None,
        timestamp_s=None,
        sample="E10k-ego",
        why_no_provenance=(
            "Build AI's evaluation parquet ships frame_id as a bare UUID4 with no factory, "
            "worker, clip, or timestamp component (docs/UPSTREAM-FINDINGS.md F9)"
        ),
    ),
    "JudgeResponse.ok": make_judge_response(status="ok"),
    "JudgeResponse.refused": make_judge_response(status="refused"),
    "JudgeResponse.unparseable": make_judge_response(status="unparseable"),
    "JudgeResponse.timeout": make_judge_response(status="timeout"),
    "JudgeResponse.error": make_judge_response(status="error"),
    "HumanLabel": make_human_label(),
    "AgreementResult": make_agreement_result(),
    "PrevalenceEstimate.clustered": make_prevalence_estimate(clustered=True),
    "PrevalenceEstimate.unclustered": make_prevalence_estimate(clustered=False),
    "CalibrationReport": make_calibration_report(),
    "ProbeResult": make_probe_result(),
    "MeasurementCard": make_measurement_card(),
}


# Raw payloads that must fail `model_validate` against the paired model. Each key is the
# model name; values are (payload, model) pairs so the test can validate against the right class.
ALL_MALFORMED: dict[str, dict[str, object]] = {
    "FrameRef.missing_worker_id": {
        "frame_id": FRAME_ID,
        "corpus": "egocentric-10k",
        "corpus_rev": "abc",
        "factory_id": "0051",
        # worker_id omitted: the cluster unit every interval depends on.
        "clip_id": "0007",
        "frame_index": 418,
        "timestamp_s": 13.933,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "codec": "hevc",
        "sample": "S10k-U",
        "stratum": "factory-0051",
        "why_no_provenance": None,
    },
    "FrameRef.partial_provenance_null": {
        "frame_id": FRAME_ID,
        "corpus": "egocentric-10k",
        "corpus_rev": "abc",
        "factory_id": "0051",
        "worker_id": None,  # null alone, without clip_id/timestamp_s also null: rejected.
        "clip_id": "0007",
        "frame_index": 418,
        "timestamp_s": 13.933,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "codec": "hevc",
        "sample": "E10k-ego",
        "stratum": "unstratified",
        "why_no_provenance": None,
    },
    "FrameRef.null_provenance_missing_reason": {
        "frame_id": FRAME_ID,
        "corpus": "egocentric-10k",
        "corpus_rev": "abc",
        "factory_id": None,
        "worker_id": None,
        "clip_id": None,
        "frame_index": 418,
        "timestamp_s": None,
        "width": 1920,
        "height": 1080,
        "fps": 30.0,
        "codec": "hevc",
        "sample": "E10k-ego",
        "stratum": "unstratified",
        "why_no_provenance": None,  # all four null but no reason given: rejected.
    },
    "JudgeResponse.hands_visible_out_of_range": {
        "frame_id": FRAME_ID,
        "judge": "gemini-2.5-flash",
        "judge_rev": "2025-06-01",
        "prompt_variant": "P0",
        "hands_visible": 3,
        "manipulation": True,
        "confidence": {"kind": "none", "value": None},
        "raw": "3",
        "status": "ok",
        "latency_ms": 412,
        "cost_usd": 0.00031,
    },
    "JudgeResponse.ok_with_null_hands_visible": {
        "frame_id": FRAME_ID,
        "judge": "gemini-2.5-flash",
        "judge_rev": "2025-06-01",
        "prompt_variant": "P0",
        "hands_visible": None,
        "manipulation": None,
        "confidence": {"kind": "none", "value": None},
        "raw": "2",
        "status": "ok",
        "latency_ms": 412,
        "cost_usd": 0.00031,
    },
    "JudgeResponse.ok_with_null_manipulation": {
        "frame_id": FRAME_ID,
        "judge": "gemini-2.5-flash",
        "judge_rev": "2025-06-01",
        "prompt_variant": "P0",
        "hands_visible": 2,
        "manipulation": None,
        "confidence": {"kind": "none", "value": None},
        "raw": "2",
        "status": "ok",
        "latency_ms": 412,
        "cost_usd": 0.00031,
    },
    "JudgeResponse.refused_with_non_null_manipulation": {
        "frame_id": FRAME_ID,
        "judge": "gemini-2.5-flash",
        "judge_rev": "2025-06-01",
        "prompt_variant": "P0",
        "hands_visible": None,
        "manipulation": True,
        "confidence": {"kind": "none", "value": None},
        "raw": "I can't help with that.",
        "status": "refused",
        "latency_ms": 412,
        "cost_usd": 0.00031,
    },
    "JudgeResponse.unknown_status": {
        "frame_id": FRAME_ID,
        "judge": "gemini-2.5-flash",
        "judge_rev": "2025-06-01",
        "prompt_variant": "P0",
        "hands_visible": None,
        "manipulation": None,
        "confidence": {"kind": "none", "value": None},
        "raw": "",
        "status": "flaky",
        "latency_ms": 412,
        "cost_usd": 0.00031,
    },
    "HumanLabel.tag_outside_closed_list": {
        "frame_id": FRAME_ID,
        "rater": "R1",
        "pass_": "primary",
        "rubric_rev": "1.2.0",
        "hands_visible": 2,
        "manipulation": True,
        "edge_case": ["motion-blur-but-spelled-wrong"],
        "difficulty": "hard",
        "note": "",
        "labelled_at": "2026-01-15T12:00:00Z",
        "seconds_spent": 22,
    },
    "PPIBlock.unclustered_missing_reason": {
        "value": 0.8931,
        "ci": {"lo": 0.8612, "hi": 0.9250, "level": 0.95},
        "n_gold": 200,
        "n_unlabelled": 10000,
        "rectifier": -0.0235,
        "method": "ppi++",
        "clustered": False,
        "cluster_by": None,
        "why_not_clustered": None,
    },
    "PPIBlock.clustered_with_stray_reason": {
        "value": 0.8931,
        "ci": {"lo": 0.8612, "hi": 0.9250, "level": 0.95},
        "n_gold": 200,
        "n_unlabelled": 10000,
        "rectifier": -0.0235,
        "method": "ppi++",
        "clustered": True,
        "cluster_by": "worker_id",
        "why_not_clustered": "should not be set when clustered",
    },
    "Confidence.none_kind_with_value": {"kind": "none", "value": 0.5},
    "Confidence.verbalized_missing_value": {"kind": "verbalized", "value": None},
    "Confidence.value_out_of_range": {"kind": "logprob", "value": 1.2},
    "AgreementCI.cluster_bootstrap_missing_clusters": {
        "lo": 0.62,
        "hi": 0.79,
        "method": "cluster-bootstrap",
        "clusters": None,
        "B": 10000,
    },
    "AgreementCI.cluster_bootstrap_missing_b": {
        "lo": 0.62,
        "hi": 0.79,
        "method": "cluster-bootstrap",
        "clusters": 61,
        "B": None,
    },
    "AgreementCI.iid_with_stray_clusters": {
        "lo": 0.62,
        "hi": 0.79,
        "method": "iid",
        "clusters": 61,
        "B": None,
    },
    "AgreementCI.iid_with_stray_b": {
        "lo": 0.62,
        "hi": 0.79,
        "method": "iid",
        "clusters": None,
        "B": 10000,
    },
    "PPIBlock.clustered_missing_cluster_by": {
        "value": 0.8931,
        "ci": {"lo": 0.8612, "hi": 0.9250, "level": 0.95},
        "n_gold": 200,
        "n_unlabelled": 10000,
        "rectifier": -0.0235,
        "method": "ppi++",
        "clustered": True,
        "cluster_by": None,
        "why_not_clustered": None,
    },
}
