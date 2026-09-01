"""Prediction-powered inference: the primary bias-corrected prevalence estimator.

Bias-corrected estimation from a small human-gold sample plus the large judge-labelled sample,
returning a valid interval for the *true* prevalence regardless of how biased the judge labels
are (`docs/DECISIONS.md` D021, corrected citation D030/D031).

Classical PPI mean estimator, Angelopoulos, Bates, Fannjiang, Jordan & Zrnic, "Prediction-Powered
Inference," arXiv:2301.09633 (NOT arXiv:2408.15204 -- that paper is Confidence-Driven Inference,
a different, later estimator; D030 corrected this exact mis-citation once already):

    theta_hat = mean(f(X) | unlabelled) + [ mean(Y | gold) - mean(f(X) | gold) ]

i.e. the judge's mean prediction on the large unlabelled pool, rectified by the mean residual
(human label minus judge prediction) on the small human-gold pool where both are observed. The
bracketed term is `PPIBlock.rectifier`. Its asymptotic-normal variance (also 2301.09633):

    Var(theta_hat) = Var(Y - f(X) | gold) / n_gold + Var(f(X) | unlabelled) / n_unlabelled

`method="ppi++"` (Angelopoulos, Duchi & Zrnic, "PPI++: Efficient Prediction-Powered Inference,"
arXiv:2311.01453) generalises this with a power-tuning parameter lambda that scales the judge's
contribution on both pools:

    theta_hat_lambda = lambda * mean(f(X) | unlabelled) + [ mean(Y | gold) - lambda * mean(f(X) | gold) ]

with lambda chosen to minimise the resulting variance. For scalar mean estimation this reduces to
the plug-in control-variate coefficient lambda* = Cov(f(X), Y | gold) / Var(f(X) | gold), which
this module estimates from the gold sample and clips to [0, 1] -- the convention used by the
`ppi_py` reference implementation, not a restriction 2311.01453 itself imposes -- so PPI++ can
never do worse than classical PPI (lambda=1) or the naive judge-only mean, but never flips the
correction's sign either. `method="ppi"` fixes lambda=1, i.e. classical PPI with no tuning.

Clustered resampling (`cluster_by` not None) delegates the gold-residual interval to
`vernier.estimation.bootstrap.cluster_bootstrap_ci`, which this module imports but does not
implement (Wave 1 unit split, `docs/DECISIONS.md` D033). `HumanLabel` and `JudgeResponse` carry
no shared participant identifier today (`worker_id` lives on `FrameRef`, joined upstream of this
module) -- `cluster_by` therefore names an attribute read directly off the `gold` (`HumanLabel`)
records via `getattr`, e.g. `cluster_by="rater"` clusters the gold-residual bootstrap by labeller.
Clustering the unlabelled judge pool by participant would need a `FrameRef` join this module does
not have access to; that term's variance stays the analytic `Var(f)/N` plug-in regardless of
`cluster_by`. This is a known scope gap, not a silent guess -- flagged for the Wave 1 reviewer.
"""

from __future__ import annotations

import math
from typing import Literal, cast

import numpy as np
from scipy.stats import norm

from vernier.estimation.bootstrap import cluster_bootstrap_ci
from vernier.models import (
    HumanLabel,
    JudgeResponse,
    NaivePrevalence,
    PPIBlock,
    PPICI,
    PrevalenceEstimate,
    PromptVariant,
)

__all__ = ["ppi_estimate", "estimate_prevalence"]

_PPIMethod = Literal["ppi", "ppi++"]

# The two tasks `vernier.judges.prompts` scores today (`_TASK_UPSTREAM_STEM`). `manipulation`
# reads `.manipulation` directly (a bool on both HumanLabel and JudgeResponse). `hand_count`
# has no ready-made shared boolean field -- `hands_visible` is a 0/1/2 count -- so it reproduces
# the "≥1 hand" headline figure (`docs/BENCHMARK.md`, `docs/PRE-REGISTRATION.md`) as an indicator.
# "Both hands" (`hands_visible == 2`) is a third published figure this two-task vocabulary does
# not cover; out of scope here.
_KNOWN_TASKS = ("manipulation", "hand_count")

_CI_LEVEL = 0.95
_Z = float(norm.ppf(1 - (1 - _CI_LEVEL) / 2))


def _judge_outcome(response: JudgeResponse) -> float:
    if response.status != "ok" or response.manipulation is None:
        raise ValueError(f"judge response for {response.frame_id!r} is not 'ok': no outcome to read")
    return float(response.manipulation)


def _gold_outcome(label: HumanLabel) -> float:
    return float(label.manipulation)


def _split_gold_and_unlabelled(
    gold: list[HumanLabel], judged: list[JudgeResponse]
) -> tuple[list[JudgeResponse], list[JudgeResponse]]:
    """Pair each gold frame with its judge prediction (by `frame_id`), and split `judged` into
    that matched gold-frame subset and the disjoint unlabelled remainder.

    PPI requires the labelled (gold) set to carry both the model prediction and the true label
    for the *same* units, and the unlabelled set to be disjoint from it -- counting a gold frame
    in both terms would double-count it and bias the correction.
    """
    ok_judged = [j for j in judged if j.status == "ok"]
    by_frame = {j.frame_id: j for j in ok_judged}
    gold_frame_ids = {h.frame_id for h in gold}

    paired: list[JudgeResponse] = []
    for h in gold:
        j = by_frame.get(h.frame_id)
        if j is None:
            raise ValueError(f"no 'ok' judge prediction found for gold frame_id {h.frame_id!r}")
        paired.append(j)

    unlabelled = [j for j in ok_judged if j.frame_id not in gold_frame_ids]
    return paired, unlabelled


def ppi_estimate(
    gold: list[HumanLabel],
    judged: list[JudgeResponse],
    *,
    cluster_by: str | None,
    why_not_clustered: str | None = None,
    method: str = "ppi++",
) -> PPIBlock:
    """Bias-corrected prevalence via prediction-powered inference over human gold plus judge
    labels, with clustered resampling wherever `cluster_by` is not None. See module docstring
    for the exact formula and citations."""
    if method not in ("ppi", "ppi++"):
        raise ValueError(f"unknown PPI method {method!r}; expected 'ppi' or 'ppi++'")
    resolved_method = cast(_PPIMethod, method)
    if not gold:
        raise ValueError("gold must be non-empty")

    paired_judge, unlabelled_judge = _split_gold_and_unlabelled(gold, judged)
    if not unlabelled_judge:
        raise ValueError("judged must contain at least one 'ok' frame outside gold (the unlabelled pool)")

    f_gold = np.array([_judge_outcome(j) for j in paired_judge], dtype=np.float64)
    y_gold = np.array([_gold_outcome(h) for h in gold], dtype=np.float64)
    f_unlabelled = np.array([_judge_outcome(j) for j in unlabelled_judge], dtype=np.float64)

    n = len(gold)
    N = len(unlabelled_judge)

    if resolved_method == "ppi":
        lam = 1.0
    else:
        var_f_gold = float(f_gold.var(ddof=1)) if n > 1 else 0.0
        if var_f_gold > 0.0:
            cov_fy = float(np.cov(f_gold, y_gold, ddof=1)[0, 1])
            lam = min(1.0, max(0.0, cov_fy / var_f_gold))
        else:
            lam = 0.0

    mean_f_unlabelled = float(f_unlabelled.mean())
    mean_f_gold = float(f_gold.mean())
    mean_y_gold = float(y_gold.mean())

    rectifier = mean_y_gold - lam * mean_f_gold
    theta_hat = lam * mean_f_unlabelled + rectifier

    residual_gold = y_gold - lam * f_gold
    var_unlabelled = float(f_unlabelled.var(ddof=1)) if N > 1 else 0.0

    if cluster_by is None:
        var_resid = float(residual_gold.var(ddof=1)) if n > 1 else 0.0
        variance = var_resid / n + (lam**2) * var_unlabelled / N
        se = math.sqrt(max(variance, 0.0))
        clustered = False
    else:
        gold_cluster_ids = [str(getattr(h, cluster_by)) for h in gold]
        residual_ci = cluster_bootstrap_ci(residual_gold.tolist(), gold_cluster_ids)
        se_resid = (residual_ci.hi - residual_ci.lo) / (2 * _Z)
        se_unlabelled = math.sqrt(max(var_unlabelled, 0.0) / N)
        se = math.sqrt(se_resid**2 + (lam**2) * se_unlabelled**2)
        clustered = True

    ci = PPICI(lo=theta_hat - _Z * se, hi=theta_hat + _Z * se, level=_CI_LEVEL)

    return PPIBlock(
        value=theta_hat,
        ci=ci,
        n_gold=n,
        n_unlabelled=N,
        rectifier=rectifier,
        method=resolved_method,
        clustered=clustered,
        cluster_by=cluster_by,
        why_not_clustered=why_not_clustered,
    )


def _remap_gold_to_task(gold: list[HumanLabel], task: str) -> list[HumanLabel]:
    if task == "manipulation":
        return list(gold)
    return [h.model_copy(update={"manipulation": h.hands_visible >= 1}) for h in gold]


def _remap_judged_to_task(judged: list[JudgeResponse], task: str) -> list[JudgeResponse]:
    if task == "manipulation":
        return list(judged)
    remapped: list[JudgeResponse] = []
    for j in judged:
        if j.hands_visible is None:
            raise ValueError(f"'ok' judge response {j.frame_id!r} has null hands_visible")
        remapped.append(j.model_copy(update={"manipulation": j.hands_visible >= 1}))
    return remapped


def estimate_prevalence(
    corpus: str,
    task: str,
    prompt_variant: PromptVariant,
    judge: str,
    gold: list[HumanLabel],
    judged: list[JudgeResponse],
    published: float,
    *,
    cluster_by: str | None,
    why_not_clustered: str | None = None,
) -> PrevalenceEstimate:
    """Assemble the headline `PrevalenceEstimate`: `naive` is the uncorrected judge-only
    proportion on the full task-matched judged sample, `ppi` is the bias-corrected block from
    `ppi_estimate`, `published` is passed through unchanged."""
    if task not in _KNOWN_TASKS:
        raise ValueError(f"unknown task {task!r}; expected one of {_KNOWN_TASKS}")

    matching_judged = [
        j for j in judged if j.judge == judge and j.prompt_variant == prompt_variant and j.status == "ok"
    ]
    if not matching_judged:
        raise ValueError(f"no 'ok' judge responses for judge={judge!r} prompt_variant={prompt_variant!r}")

    task_gold = _remap_gold_to_task(gold, task)
    task_judged = _remap_judged_to_task(matching_judged, task)

    naive_values = [_judge_outcome(j) for j in task_judged]
    naive = NaivePrevalence(value=float(np.mean(naive_values)), n=len(task_judged))

    ppi = ppi_estimate(
        task_gold,
        task_judged,
        cluster_by=cluster_by,
        why_not_clustered=why_not_clustered,
    )

    return PrevalenceEstimate(
        corpus=corpus,
        task=task,
        prompt_variant=prompt_variant,
        judge=judge,
        naive=naive,
        ppi=ppi,
        published=published,
    )
