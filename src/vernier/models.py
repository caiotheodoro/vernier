"""Pydantic records for every schema fixed in ``CONTRACTS.md``.

Field names, types and stated invariants follow that document exactly. Only invariants the
document states with an explicit "X ∈ {...}" or an explicit "required" clause are encoded as
`Literal`s or validators; everything else stays a plain type so this module does not assert
constraints ``CONTRACTS.md`` never made.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "Confidence",
    "ConfidenceKind",
    "JudgeStatus",
    "PromptVariant",
    "PassType",
    "EdgeCaseTag",
    "FrameRef",
    "JudgeResponse",
    "HumanLabel",
    "Comparison",
    "AgreementCI",
    "AgreementResult",
    "NaivePrevalence",
    "PPICI",
    "PPIBlock",
    "PrevalenceEstimate",
    "CalibrationBin",
    "CalibrationReport",
    "ProbeCI",
    "ProbeResult",
    "Claim",
    "UncheckedItem",
    "CardInterval",
    "MeasurementCard",
]


class Record(BaseModel):
    """Base for every contract record: immutable, and rejects fields ``CONTRACTS.md`` never named."""

    model_config = ConfigDict(frozen=True, extra="forbid")


# --- shared enums -----------------------------------------------------------------------

ConfidenceKind = Literal["logprob", "verbalized", "none"]

JudgeStatus = Literal["ok", "refused", "unparseable", "timeout", "error"]

# CONTRACTS.md: "prompt_variant ∈ {P0a, P0b, P1...P7}". The hand-count prompt shared across
# both P0 sources is labelled plain "P0" (PRE-REGISTRATION.md, RUBRIC.md Task 1).
PromptVariant = Literal["P0", "P0a", "P0b", "P1", "P2", "P3", "P4", "P5", "P6", "P7"]

# HumanLabel.pass ∈ {primary, retest, review}
# `review` is a third read of frames already labelled in `primary`, added for the targeted
# disagreement review. It is a separate pass rather than an edit of `primary` because the
# primary labels back published claims: overwriting them would silently restate a result.
# Nothing enumerates this Literal -- every consumer names the pass it wants -- so `review`
# reaches no analysis unless one is changed to ask for it.
PassType = Literal["primary", "retest", "review"]

# RUBRIC.md: "Tag list, closed."
EdgeCaseTag = Literal[
    "partial",
    "glove",
    "tool-occlusion",
    "reflection",
    "blur",
    "edge",
    "undecidable",
    "idle-grip",
    "gesture",
    "self-contact",
    "between-actions",
    "dark",
    "other-person",
]


class Confidence(Record):
    """``JudgeResponse.confidence``. ``kind`` is never pooled across judges (CONTRACTS.md)."""

    kind: ConfidenceKind
    value: float | None

    @model_validator(mode="after")
    def _value_null_iff_kind_none_and_in_range(self) -> "Confidence":
        if self.kind == "none" and self.value is not None:
            raise ValueError("value must be null when kind is 'none'")
        if self.kind != "none":
            if self.value is None:
                raise ValueError("value is required when kind is not 'none'")
            if not 0 <= self.value <= 1:
                raise ValueError("value must be in [0, 1]")
        return self


# --- FrameRef ----------------------------------------------------------------------------


class FrameRef(Record):
    """The unit of everything. ``worker_id`` is the cluster unit for every reported interval.

    Build AI's evaluation parquets ship ``frame_id`` as a bare UUID4 with no factory, worker,
    clip, or timestamp component (docs/UPSTREAM-FINDINGS.md F9) -- these four fields are null
    together for every E10k-*/P2k/G200-* frame, and ``why_no_provenance`` records why. Corpus
    draws (S10k-U, S10k-S) carry full provenance and leave ``why_no_provenance`` null.

    ``fps``/``codec`` join that same null-together group (D040): the evaluation parquets ship
    extracted still frames with no reference to a source video at all -- verified live against
    the real parquet schema (``frame_id``, ``image``, ``source_dataset``, ``hand_count``,
    ``active_labor``, nothing video-level) -- so there is no real fps/codec to report for an
    eval-arm frame, the identical root cause as the missing factory/worker/clip/timestamp
    fields. ``width``/``height`` stay required for every frame regardless, since they are
    always recoverable by decoding the frame image itself, independent of any video context.
    """

    frame_id: str
    corpus: str
    corpus_rev: str
    factory_id: str | None
    worker_id: str | None
    clip_id: str | None
    frame_index: int
    timestamp_s: float | None
    width: int
    height: int
    fps: float | None
    codec: str | None
    sample: str
    stratum: str
    why_no_provenance: str | None

    @model_validator(mode="after")
    def _why_no_provenance_required_when_fields_null(self) -> "FrameRef":
        provenance_fields = (
            self.factory_id,
            self.worker_id,
            self.clip_id,
            self.timestamp_s,
            self.fps,
            self.codec,
        )
        any_null = any(f is None for f in provenance_fields)
        all_null = all(f is None for f in provenance_fields)
        if any_null and not all_null:
            raise ValueError(
                "factory_id, worker_id, clip_id, timestamp_s, fps, and codec must be null "
                "together, never partially -- a frame either has full corpus/source-video "
                "provenance or none"
            )
        if all_null and not self.why_no_provenance:
            raise ValueError(
                "why_no_provenance is required when factory_id/worker_id/clip_id/timestamp_s/"
                "fps/codec are null"
            )
        if not all_null and self.why_no_provenance is not None:
            raise ValueError("why_no_provenance must be null when provenance fields are present")
        return self


# --- JudgeResponse -------------------------------------------------------------------------


class JudgeResponse(Record):
    """One judge, one prompt variant, one frame.

    A non-``ok`` ``status`` keeps ``raw`` and is excluded from the denominator with its
    reason (CONTRACTS.md rule 2, "absence is explicit"); ``hands_visible`` and ``manipulation``
    are null whenever the judge's answer could not be classified as one of the closed answers.
    """

    frame_id: str
    judge: str
    judge_rev: str
    prompt_variant: PromptVariant
    hands_visible: Literal[0, 1, 2] | None
    manipulation: bool | None
    confidence: Confidence
    raw: str
    status: JudgeStatus
    latency_ms: int
    cost_usd: float

    @model_validator(mode="after")
    def _hands_visible_and_manipulation_null_iff_unparseable_or_worse(self) -> "JudgeResponse":
        if self.status == "ok":
            if self.hands_visible is None:
                raise ValueError("status 'ok' requires a non-null hands_visible")
            if self.manipulation is None:
                raise ValueError("status 'ok' requires a non-null manipulation")
        else:
            if self.hands_visible is not None:
                raise ValueError(f"status {self.status!r} requires a null hands_visible")
            if self.manipulation is not None:
                raise ValueError(f"status {self.status!r} requires a null manipulation")
        return self


# --- HumanLabel ----------------------------------------------------------------------------


class HumanLabel(Record):
    """The oracle. The labelling tool that produces this has no read path to judge output."""

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    frame_id: str
    rater: str
    pass_: PassType = Field(alias="pass")
    rubric_rev: str
    hands_visible: Literal[0, 1, 2]
    manipulation: bool
    edge_case: tuple[EdgeCaseTag, ...]
    difficulty: Literal["easy", "medium", "hard"]
    note: str
    labelled_at: datetime
    seconds_spent: int


# --- AgreementResult -----------------------------------------------------------------------


class Comparison(Record):
    a: str
    b: str


class AgreementCI(Record):
    lo: float
    hi: float
    # PRE-REGISTRATION.md "the cluster problem": iid intervals are shown only as a labelled
    # lower bound on width, never reported alone.
    method: Literal["cluster-bootstrap", "iid"]
    clusters: int | None
    B: int | None

    @model_validator(mode="after")
    def _cluster_bootstrap_requires_clusters_and_b(self) -> "AgreementCI":
        if self.method == "cluster-bootstrap":
            if self.clusters is None:
                raise ValueError("clusters is required when method is 'cluster-bootstrap'")
            if self.B is None:
                raise ValueError("B is required when method is 'cluster-bootstrap'")
        else:
            if self.clusters is not None:
                raise ValueError("clusters must be null when method is 'iid'")
            if self.B is not None:
                raise ValueError("B must be null when method is 'iid'")
        return self


class AgreementResult(Record):
    """Consumes JudgeResponse + HumanLabel. Does not own intervals (ARCHITECTURE.md: `agreement`) --
    ``ci`` is computed by `estimation` and attached here, not recomputed by this module."""

    comparison: Comparison
    task: str
    subset: str
    n: int
    n_excluded: int
    # dict, not an immutable mapping: `frozen=True` blocks reassigning this attribute but does
    # not block in-place mutation of the dict it points to. Accepted risk (D031) -- a true
    # immutable mapping would break the plain-JSON-object shape CONTRACTS.md specifies for this
    # field, and every constructor here is one-shot, not long-lived.
    excluded_why: dict[str, int]
    raw_agreement: float
    ac1: float
    kappa: float
    ci: AgreementCI
    design_effect: float


# --- PrevalenceEstimate --------------------------------------------------------------------


class NaivePrevalence(Record):
    value: float
    n: int


class PPICI(Record):
    lo: float
    hi: float
    level: float


class PPIBlock(Record):
    value: float
    ci: PPICI
    n_gold: int
    n_unlabelled: int
    rectifier: float
    method: Literal["ppi", "ppi++"]
    clustered: bool
    cluster_by: str | None
    why_not_clustered: str | None

    @model_validator(mode="after")
    def _cluster_by_and_why_not_clustered_match_clustered_flag(self) -> "PPIBlock":
        # ARCHITECTURE.md `estimation` seam: "clustered is a property of the arm... the flag
        # is required and the reason string is required with it." The symmetric case -- what
        # was clustered on -- is equally required when clustered is True (D031: a prevalence
        # estimate must never claim clustered=True without naming cluster_by).
        if self.clustered:
            if not self.cluster_by:
                raise ValueError("cluster_by is required when clustered is True")
            if self.why_not_clustered is not None:
                raise ValueError("why_not_clustered must be null when clustered is True")
        else:
            if self.cluster_by is not None:
                raise ValueError("cluster_by must be null when clustered is False")
            if not self.why_not_clustered:
                raise ValueError("why_not_clustered is required when clustered is False")
        return self


class PrevalenceEstimate(Record):
    """The headline number. Referenced by every published proportion."""

    corpus: str
    task: str
    prompt_variant: PromptVariant
    judge: str
    naive: NaivePrevalence
    ppi: PPIBlock
    published: float


# --- CalibrationReport ---------------------------------------------------------------------


class CalibrationBin(Record):
    lo: float
    hi: float
    n: int
    mean_conf: float | None
    accuracy: float | None


class CalibrationReport(Record):
    """ECE with fixed bins. Empty bins are reported empty, never merged into neighbours."""

    judge: str
    task: str
    subset: str
    confidence_kind: ConfidenceKind
    ece: float
    bins: tuple[CalibrationBin, ...]
    note: str


# --- ProbeResult ---------------------------------------------------------------------------


class ProbeCI(Record):
    lo: float
    hi: float
    method: Literal["cluster-bootstrap", "iid"]


class ProbeResult(Record):
    """Result 2. Matched frozen-feature probes; matching is enforced in code, not left to the caller."""

    source_corpus: str
    n_frames: int
    backbone: str
    downstream: str
    metric: str
    value: float
    ci: ProbeCI
    seed: int
    matched_on: tuple[str, ...]


# --- MeasurementCard -----------------------------------------------------------------------
# CONTRACTS.md gives no JSON example for this record, only the prose list of what it carries.
# Each field below maps to one bullet in that list.


class Claim(Record):
    """One published claim, tied to the record that produced it."""

    statement: str
    record_type: str
    record_ref: str


class UncheckedItem(Record):
    """One entry in "what could not be checked" -- a named reason is required, never omitted."""

    item: str
    reason: str


class CardInterval(Record):
    label: str
    ci: AgreementCI
    design_effect: float | None


class MeasurementCard(Record):
    """The published artifact, inherited from Assay's Environment Card."""

    verdict: str
    claims: tuple[Claim, ...]
    what_could_not_be_checked: tuple[UncheckedItem, ...]
    sample_definition: str
    rubric_rev: str
    # dict, not an immutable mapping -- same accepted-risk note as AgreementResult.excluded_why.
    judge_revisions: dict[str, str]
    prompt_variants: tuple[PromptVariant, ...]
    intervals: tuple[CardInterval, ...]
    # Identifies the card and catches corruption; not tamper-evidence (CONTRACTS.md).
    content_digest: str
