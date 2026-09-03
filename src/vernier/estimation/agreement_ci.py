"""Bootstrap confidence intervals on Gwet's AC1.

`agreement/core.py`'s own module docstring says it does not own intervals -- `ci` is computed
by `vernier.estimation` and passed in, never recomputed in `agreement`. This module is that
computation for AC1 specifically: `estimation/bootstrap.py`'s `cluster_bootstrap_ci` resamples
a list of scalar per-unit values (a mean-like statistic); AC1 is a whole-sample pooled-marginal
statistic, not a mean, so it needs its own resampling loop that recomputes AC1 fresh on every
resample rather than resampling a precomputed per-unit value.

`HumanLabel`/`JudgeResponse` carry no shared cluster id (`docs/DECISIONS.md` D039, disclosed,
unfixed) -- every interval returned here is `method="iid"`, per
`docs/PRE-REGISTRATION.md` ("the cluster problem"): a labelled lower bound on true width, never
reported alone.
"""

from __future__ import annotations

import numpy as np

from vernier.agreement.core import _categories, _comparable_pairs, _gwet_ac1_from_pairs
from vernier.models import AgreementCI, HumanLabel, JudgeResponse

AC1_BOOTSTRAP_B = 10_000
AC1_BOOTSTRAP_SEED = 777


def _percentile_ci_from_pairs(
    pairs: list[tuple[object, object]], categories: tuple[object, ...], *, B: int, seed: int
) -> AgreementCI:
    n = len(pairs)
    rng = np.random.default_rng(seed)
    values = np.empty(B, dtype=float)
    for b in range(B):
        resample = [pairs[i] for i in rng.integers(0, n, size=n)]
        values[b] = _gwet_ac1_from_pairs(resample, categories)
    lo, hi = np.percentile(values, [2.5, 97.5])
    return AgreementCI(lo=float(lo), hi=float(hi), method="iid", clusters=None, B=None)


def ac1_bootstrap_ci(
    labels: list[HumanLabel],
    responses: list[JudgeResponse],
    task: str,
    *,
    B: int = AC1_BOOTSTRAP_B,
    seed: int = AC1_BOOTSTRAP_SEED,
) -> AgreementCI:
    """Percentile bootstrap CI on `gwet_ac1(labels, responses, task)`.

    Resamples matched (human, judge) pairs with replacement `B` times, recomputing AC1 fresh on
    each resample -- never resampling a precomputed per-unit value, since AC1 is a single
    statistic over the whole matched set, not a per-unit mean.
    """
    categories = _categories(task)
    pairs = _comparable_pairs(labels, responses, task)
    return _percentile_ci_from_pairs(pairs, categories, B=B, seed=seed)


def intra_rater_ac1_bootstrap_ci(
    primary: list[HumanLabel],
    retest: list[HumanLabel],
    task: str,
    *,
    B: int = AC1_BOOTSTRAP_B,
    seed: int = AC1_BOOTSTRAP_SEED,
) -> AgreementCI:
    """Percentile bootstrap CI on intra-rater AC1 (primary pass vs. retest, matched by
    `frame_id`), same resampling discipline as `ac1_bootstrap_ci`."""
    from vernier.agreement.core import _LABEL_FIELD

    categories = _categories(task)
    label_value = _LABEL_FIELD[task]
    retest_by_frame = {label.frame_id: label for label in retest}
    pairs: list[tuple[object, object]] = []
    for label in primary:
        match = retest_by_frame.get(label.frame_id)
        if match is None:
            continue
        pairs.append((label_value(label), label_value(match)))
    return _percentile_ci_from_pairs(pairs, categories, B=B, seed=seed)
