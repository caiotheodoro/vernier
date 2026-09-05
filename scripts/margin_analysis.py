"""EXPLORATORY: the gold-corrected difference between two corpora, not just their levels.

`PRE-REGISTRATION.md` registers H5 as an interaction -- whether the judge's *error rate* differs
by domain -- and D035 found that underpowered before any label was written. What Build AI
actually publishes is not an error rate but a *margin*: Egocentric-10K leads
EPIC-KITCHENS-100 by 6.62pp on active manipulation and 6.05pp on >=1 hand
(`docs/UPSTREAM-FINDINGS.md` F4). This script estimates that margin after correcting each side
for judge error against human gold, and asks whether the published margin sits inside the
corrected interval.

**This estimand is not pre-registered.** `PRE-REGISTRATION.md`'s own rule is that anything not
listed there is reported as exploratory, in those words, and that is what this is. It is a
re-parameterisation of H5's question on the same frozen data, not a new outcome fished from a
family, and the pre-registered H5 is reported beside it unchanged.

Variance: the two arms are disjoint frame sets from different corpora, so their PPI estimates
are treated as independent and the margin's variance is the sum. That is conservative in the
direction that matters here -- the arms share one rater and one judge, and any shared offset is
positively correlated across them, which would make the true variance of the *difference*
smaller than the sum, not larger. A margin that excludes the published value under this
interval would also exclude it under a tighter one.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from scipy.stats import norm  # noqa: E402

from vernier.agreement.core import _LABEL_FIELD, _RESPONSE_FIELD  # noqa: E402
from vernier.estimation.ppi import estimate_prevalence  # noqa: E402
from vernier.judges.prompts import PromptVariant  # noqa: E402
from vernier.labels.store import HumanLabelStore  # noqa: E402
from vernier.models import HumanLabel, JudgeResponse  # noqa: E402
from vernier.sampling.draw import SampleName  # noqa: E402
from vernier.sampling.membership import load_membership  # noqa: E402

_LABEL_STORE_ROOT = Path("data/labels")
_MEMBERSHIP_ROOT = Path("data/membership")
_GOLD_JUDGED_ROOT = Path("data/gold_judged")
_RATER = "caio"
_JUDGE = "qwen3-vl"
_VARIANT: PromptVariant = "P0b"
_CI_LEVEL = 0.95
_Z = float(norm.ppf(1 - (1 - _CI_LEVEL) / 2))

_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")
_CORPUS_NAME = {
    "G200-ego": "egocentric-10k",
    "G200-ego4d": "ego4d",
    "G200-epic": "epic-kitchens-100",
}
# PRE-REGISTRATION.md's frozen headline table.
_PUBLISHED: dict[str, dict[str, float]] = {
    "G200-ego": {"hand_count": 0.9642, "manipulation": 0.9166},
    "G200-ego4d": {"hand_count": 0.6733, "manipulation": 0.5007},
    "G200-epic": {"hand_count": 0.9037, "manipulation": 0.8504},
}
# Egocentric-10K is always the left side: the published claim is that it leads.
_COMPARISONS: tuple[tuple[SampleName, SampleName], ...] = (
    ("G200-ego", "G200-epic"),
    ("G200-ego", "G200-ego4d"),
)
_WHY_NOT_CLUSTERED = (
    "HumanLabel carries no shared participant/cluster id with FrameRef (docs/DECISIONS.md D039)"
)


def _se_from_block(block: Any) -> float:
    """`ppi_estimate` builds its interval as theta +/- z*se, so the standard error is recoverable
    exactly from the interval rather than by re-deriving the variance here."""
    return float(block.ci.hi - block.ci.lo) / (2 * _Z)


def margin(
    left: Any,
    right: Any,
    published_left: float,
    published_right: float,
    components: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """The corrected difference left - right, against the published difference.

    `components` is (summed gold residual variance, summed unlabelled floor variance) across the
    two arms, which is what any sample-size question needs; without it the sizing is omitted
    rather than guessed (D088).
    """
    point = left.value - right.value
    se = math.sqrt(_se_from_block(left) ** 2 + _se_from_block(right) ** 2)
    lo, hi = point - _Z * se, point + _Z * se
    published = published_left - published_right
    out: dict[str, Any] = {
        "corrected_margin_pp": point * 100,
        "ci_pp": {"lo": lo * 100, "hi": hi * 100, "level": _CI_LEVEL},
        "published_margin_pp": published * 100,
        "published_inside_corrected_ci": bool(lo <= published <= hi),
        "sign_flipped": bool((published > 0) != (point > 0)),
        "left": {"value": left.value, "n_gold": left.n_gold, "n_unlabelled": left.n_unlabelled},
        "right": {"value": right.value, "n_gold": right.n_gold, "n_unlabelled": right.n_unlabelled},
        "se_pp": se * 100,
    }
    if components is not None:
        var_resid_sum, unl_floor = components
        out["gold_per_arm_to_exclude_published"] = _gold_needed_to_exclude(
            point, published, var_resid_sum, unl_floor
        )
    return out


def _variance_components(
    gold: list[HumanLabel], judged: list[JudgeResponse], task: str
) -> tuple[float, float, int, int]:
    """The PPI++ variance split: (gold residual variance, lambda^2 * unlabelled variance, n, N).

    `estimation/ppi.py` computes both and keeps neither, and the split is what any sample-size
    question turns on: only the first term shrinks when more frames are labelled. The second is
    a floor set by the size of the unlabelled pool (`docs/DECISIONS.md` D088).
    """
    label_value = _LABEL_FIELD[task]
    response_value = _RESPONSE_FIELD[task]
    gold_ids = {lab.frame_id for lab in gold}
    ok = [j for j in judged if j.status == "ok"]
    by_frame = {j.frame_id: j for j in ok}
    y = [float(bool(label_value(lab))) for lab in gold]
    f_gold = [float(bool(response_value(by_frame[lab.frame_id]))) for lab in gold]
    f_unl = [float(bool(response_value(j))) for j in ok if j.frame_id not in gold_ids]
    n, big_n = len(y), len(f_unl)
    mean_fg, mean_y = sum(f_gold) / n, sum(y) / n

    def var(xs: list[float], m: float) -> float:
        return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)

    var_fg = var(f_gold, mean_fg)
    cov = sum((a - mean_fg) * (b - mean_y) for a, b in zip(f_gold, y)) / (n - 1)
    lam = min(1.0, max(0.0, cov / var_fg)) if var_fg > 0 else 0.0
    resid = [b - lam * a for a, b in zip(f_gold, y)]
    var_resid = var(resid, sum(resid) / n)
    var_unl = var(f_unl, sum(f_unl) / big_n)
    return var_resid, (lam**2) * var_unl / big_n, n, big_n


def _gold_needed_to_exclude(
    point: float, published: float, var_resid_sum: float, unl_floor: float
) -> dict[str, Any]:
    """How many gold frames per arm would put `published` outside the interval.

    The previous version scaled the WHOLE standard error as 1/sqrt(n), which is wrong: the
    unlabelled term does not shrink when more frames are labelled, so it is a floor. That bug
    produced an answer smaller than the sample already collected (D088).
    """
    gap = abs(published - point)
    target_se = gap / _Z
    floor_se = math.sqrt(unl_floor)
    if target_se <= floor_se:
        return {
            "achievable_by_labelling_alone": False,
            "reason": (
                "the unlabelled pool alone contributes more variance than the target allows; "
                "no number of gold labels reaches it without a larger judged pool"
            ),
            "floor_half_width_pp": _Z * floor_se * 100,
        }
    needed = var_resid_sum / (target_se**2 - floor_se**2)
    return {
        "achievable_by_labelling_alone": True,
        "gold_per_arm": int(math.ceil(needed)),
        "floor_half_width_pp": _Z * floor_se * 100,
    }


def _load_labels() -> list[HumanLabel]:
    return HumanLabelStore(_LABEL_STORE_ROOT / _RATER).read_pass("primary")


def _load_judged(sample: SampleName) -> list[JudgeResponse]:
    path = _GOLD_JUDGED_ROOT / f"{sample}.P0b.json"
    return [JudgeResponse.model_validate(r) for r in json.loads(path.read_text())]


def main() -> int:
    primary = _load_labels()
    judged = {s: _load_judged(s) for s in _SAMPLES}
    ids = {s: {f.frame_id for f in load_membership(s, _MEMBERSHIP_ROOT)} for s in _SAMPLES}

    blocks: dict[str, dict[str, Any]] = {}
    comps: dict[str, dict[str, tuple[float, float, int, int]]] = {}
    for sample in _SAMPLES:
        gold = [lab for lab in primary if lab.frame_id in ids[sample]]
        blocks[sample] = {}
        comps[sample] = {
            task: _variance_components(gold, judged[sample], task)
            for task in ("hand_count", "manipulation")
        }
        for task in ("hand_count", "manipulation"):
            blocks[sample][task] = estimate_prevalence(
                corpus=_CORPUS_NAME[sample],
                task=task,
                prompt_variant=_VARIANT,
                judge=_JUDGE,
                gold=gold,
                judged=judged[sample],
                published=_PUBLISHED[sample][task],
                cluster_by=None,
                why_not_clustered=_WHY_NOT_CLUSTERED,
            ).ppi

    out: dict[str, Any] = {
        "estimand": "exploratory",
        "why_exploratory": (
            "Not in PRE-REGISTRATION.md. Its own rule is that anything not listed there is "
            "reported as exploratory, in those words. A re-parameterisation of H5's question on "
            "the same frozen data; the pre-registered H5 is unchanged and reported beside it."
        ),
        "variance_note": (
            "Arms are disjoint frame sets; variances are summed. Conservative: a shared rater or "
            "judge offset is positively correlated across arms, which would shrink the variance "
            "of the difference below the sum."
        ),
        "comparisons": {},
    }
    for left_s, right_s in _COMPARISONS:
        key = f"{_CORPUS_NAME[left_s]}_minus_{_CORPUS_NAME[right_s]}"
        out["comparisons"][key] = {
            task: margin(
                blocks[left_s][task],
                blocks[right_s][task],
                _PUBLISHED[left_s][task],
                _PUBLISHED[right_s][task],
                components=(
                    comps[left_s][task][0] + comps[right_s][task][0],
                    comps[left_s][task][1] + comps[right_s][task][1],
                ),
            )
            for task in ("hand_count", "manipulation")
        }

    path = Path("data/margin_exploratory.json")
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
    print(f"\nwrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
