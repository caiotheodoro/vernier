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
    if len(confidences) != len(correct):
        raise ValueError(
            f"confidences and correct must be the same length, got "
            f"{len(confidences)} and {len(correct)}"
        )

    width = 1.0 / n_bins
    edges = [i * width for i in range(n_bins)] + [1.0]

    members: list[list[int]] = [[] for _ in range(n_bins)]
    for idx, conf in enumerate(confidences):
        bin_idx = min(int(conf / width), n_bins - 1)
        members[bin_idx].append(idx)

    bins: list[CalibrationBin] = []
    for i in range(n_bins):
        idxs = members[i]
        if idxs:
            n = len(idxs)
            mean_conf = sum(confidences[j] for j in idxs) / n
            accuracy = sum(1 for j in idxs if correct[j]) / n
        else:
            n = 0
            mean_conf = None
            accuracy = None
        bins.append(CalibrationBin(lo=edges[i], hi=edges[i + 1], n=n, mean_conf=mean_conf, accuracy=accuracy))
    return bins

def ece(bins: list[CalibrationBin]) -> float:
    """Standard Expected Calibration Error: sum over non-empty bins of
    `(n_i / N) * |accuracy_i - mean_conf_i|`, `N` the total count across all bins. Empty bins
    contribute 0 -- there is no confidence/accuracy pair to compare."""
    total = sum(b.n for b in bins)
    if total == 0:
        return 0.0
    result = 0.0
    for b in bins:
        if b.n == 0:
            continue
        assert b.mean_conf is not None and b.accuracy is not None
        result += (b.n / total) * abs(b.accuracy - b.mean_conf)
    return result

def compute_j(responses: list[JudgeResponse], gold_correct: list[bool]) -> float:
    """Judge quality (2605.06939).

    PLACEHOLDER, not the paper's real metric. arXiv 2605.06939 is described in this repo
    (docs/SURVEY.md, docs/DECISIONS.md D028) only at the level of "judge quality J" and
    "cross-corpus calibration instability delta-J" -- no exact formula is recorded here, and
    this implementation has not verified the paper's actual statistic against its full text.
    Per the task instructions, presenting a guessed formula as the paper's real metric would
    repeat the mis-citation pattern docs/DECISIONS.md D030 exists to catch. Until someone reads
    2605.06939 and updates this docstring, `compute_j` is simple accuracy of the judge against
    gold: `mean(gold_correct)`.
    """
    if len(responses) != len(gold_correct):
        raise ValueError(
            f"responses and gold_correct must be the same length, got "
            f"{len(responses)} and {len(gold_correct)}"
        )
    if not gold_correct:
        raise ValueError("gold_correct must not be empty")
    return sum(1 for c in gold_correct if c) / len(gold_correct)

def compute_delta_j(j_by_corpus: dict[str, float]) -> float:
    """Cross-corpus calibration instability: the diagnostic that says when a shared-calibration
    comparison is unreliable.

    PLACEHOLDER, not the paper's real metric -- same caveat as `compute_j`: arXiv 2605.06939's
    exact definition of delta-J has not been verified against the paper's full text (see that
    function's docstring for why this repo will not present a guess as the settled metric).
    Until verified, this is the range of J across corpora (`max(J) - min(J)`), chosen because
    the name "delta-J" reads as a difference rather than a dispersion measure, and because a
    range makes the worst-case cross-corpus gap visible directly, which is what "when is a
    shared-calibration comparison unreliable" needs.
    """
    if not j_by_corpus:
        raise ValueError("j_by_corpus must not be empty")
    values = list(j_by_corpus.values())
    return max(values) - min(values)

def build_calibration_report(
    judge: str,
    task: str,
    subset: str,
    confidence_kind: ConfidenceKind,
    bins: list[CalibrationBin],
) -> CalibrationReport:
    return CalibrationReport(
        judge=judge,
        task=task,
        subset=subset,
        confidence_kind=confidence_kind,
        ece=ece(bins),
        bins=tuple(bins),
        note="empty bins are reported as empty, never merged away",
    )
