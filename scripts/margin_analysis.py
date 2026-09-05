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
    left: Any, right: Any, published_left: float, published_right: float
) -> dict[str, Any]:
    """The corrected difference left - right, against the published difference."""
    point = left.value - right.value
    se = math.sqrt(_se_from_block(left) ** 2 + _se_from_block(right) ** 2)
    lo, hi = point - _Z * se, point + _Z * se
    published = published_left - published_right
    return {
        "corrected_margin_pp": point * 100,
        "ci_pp": {"lo": lo * 100, "hi": hi * 100, "level": _CI_LEVEL},
        "published_margin_pp": published * 100,
        "published_inside_corrected_ci": bool(lo <= published <= hi),
        "sign_flipped": bool((published > 0) != (point > 0)),
        "left": {"value": left.value, "n_gold": left.n_gold, "n_unlabelled": left.n_unlabelled},
        "right": {"value": right.value, "n_gold": right.n_gold, "n_unlabelled": right.n_unlabelled},
        "se_pp": se * 100,
        # What it would take to separate the two. Approximate on purpose: it scales the gold
        # term as 1/n and holds the residual variance and the unlabelled term fixed, so it is a
        # floor on the labels required, not a power analysis. Reported because "the interval
        # includes the published value" is only actionable with a price attached.
        "approx_gold_per_arm_to_exclude_published": _gold_needed_to_exclude(point, se, published),
    }


def _gold_needed_to_exclude(point: float, se: float, published: float, n_now: int = 30) -> int | None:
    """Roughly how many gold labels per arm would put `published` outside the interval, if the
    point estimate held. None when the point estimate is already on the published side."""
    gap = abs(published - point)
    if gap == 0.0:
        return None
    se_needed = gap / _Z
    if se_needed >= se:
        return n_now
    return int(math.ceil(n_now * (se / se_needed) ** 2))


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
    for sample in _SAMPLES:
        gold = [lab for lab in primary if lab.frame_id in ids[sample]]
        blocks[sample] = {}
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
