"""ECE with fixed bins, reliability diagrams, per judge and per confidence kind.

Empty bins are reported empty, never merged into neighbours to make a curve look smooth.
Calibration is measurable only under `P7` (the only prompt variant that requests a confidence
value) -- see H7. Also owns J and delta-J (2605.06939): judge quality and cross-corpus
calibration instability.
"""

from __future__ import annotations

from vernier.models import CalibrationBin, CalibrationReport, ConfidenceKind, JudgeResponse

FIXED_BIN_COUNT = 10


def reliability_bins(
    confidences: list[float],
    correct: list[bool],
    *,
    n_bins: int = FIXED_BIN_COUNT,
) -> list[CalibrationBin]:
    """Equal-width bins over [0, 1]. An empty bin is emitted with `n=0` and null `mean_conf`/
    `accuracy`, never dropped or merged."""
    raise NotImplementedError


def ece(bins: list[CalibrationBin]) -> float:
    raise NotImplementedError


def compute_j(responses: list[JudgeResponse], gold_correct: list[bool]) -> float:
    """Judge quality (2605.06939)."""
    raise NotImplementedError


def compute_delta_j(j_by_corpus: dict[str, float]) -> float:
    """Cross-corpus calibration instability: the diagnostic that says when a shared-calibration
    comparison is unreliable."""
    raise NotImplementedError


def build_calibration_report(
    judge: str,
    task: str,
    subset: str,
    confidence_kind: ConfidenceKind,
    bins: list[CalibrationBin],
) -> CalibrationReport:
    raise NotImplementedError
