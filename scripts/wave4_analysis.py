"""Wave 4: real analysis off Wave 3's human gold (primary + retest, D057/D058) and the real
`G200-*` live-judge run (`scripts/judge_gold_sets.py`).

Computes, all off real data, nothing synthetic:

- **Intra-rater AC1/kappa** (`R100` falsification gate, `PRE-REGISTRATION.md`'s first-listed
  one): primary vs. retest, matched by `frame_id`. AC1 has no dedicated entry point in
  `agreement.core` by design (see that module's `intra_rater_kappa` docstring) -- built here the
  same way that function builds Cohen's kappa, via the module's own pair/category machinery.
- **H4**: AC1(judge, human) higher for `hand_count` than `manipulation`, for the one judge in
  the panel (`qwen3-vl`).
- **H5**: judge error rate against human gold on `manipulation`, Egocentric (`G200-ego`) vs.
  EPIC-KITCHENS-100 (`G200-epic`) arms of the *primary*-labelled subset, checked against the
  pre-registered >=5pp threshold with EPIC-KITCHENS-100 expected higher.
- **PPI-corrected prevalence**, per domain and task, gold = the primary-labelled subset of that
  arm, unlabelled = the rest of that arm's real 200-frame judged pool (`scripts/judge_gold_sets.py`
  judges all 200, not just the labelled subset, precisely so this has a real unlabelled pool to
  draw power from). `cluster_by=None`: `HumanLabel` carries no shared participant/cluster id
  (D039's disclosed, unfixed gap) -- honestly `why_not_clustered`, not silently unclustered.

Real published figures used as `PrevalenceEstimate.published` (`PRE-REGISTRATION.md`'s frozen
table, `>=1 hand` / active manipulation columns; `hand_count` in this codebase's own PPI
vocabulary means the `>=1 hand` indicator, not "both hands" -- see `estimation/ppi.py`'s
docstring): Egocentric-10K 96.42%/91.66%, Ego4D 67.33%/50.07%, EPIC-KITCHENS-100 90.37%/85.04%.

- **H7 (calibration), a real, disclosed deviation from "P7 only" (D060)**: `PRE-REGISTRATION.md`
  scopes calibration to `P7` because the *retired* closed judges (Gemini/Claude) only ever
  exposed confidence when a prompt explicitly asked for one. The self-hosted `qwen3-vl` judge
  is different -- it derives logprob confidence from its own output distribution on *every*
  call, `P7` or not (`judges/qwen3vl.py`'s own docstring; D052/D053 pinned this). The 600 real
  `G200-*` `P0b` responses already carry real logprob confidence, so `_calibration()` computes
  ECE from that already-collected data against the 93 primary human-gold labels -- no new judge
  calls needed. Flagged in the report's own `note` field, not silently substituted for P7.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from vernier.agreement.core import (
    _LABEL_FIELD,
    _RESPONSE_FIELD,
    _categories,
    _gwet_ac1_from_pairs,
    cohens_kappa,
    gwet_ac1,
    intra_rater_kappa,
    raw_agreement,
)
from vernier.calibration import build_calibration_report, reliability_bins
from vernier.estimation.ppi import estimate_prevalence
from vernier.judges.prompts import PromptVariant
from vernier.labels.store import HumanLabelStore
from vernier.models import HumanLabel, JudgeResponse, PassType
from vernier.sampling.draw import SampleName
from vernier.sampling.membership import load_membership

_LABEL_STORE_ROOT = Path("data/labels")
_MEMBERSHIP_ROOT = Path("data/membership")
_GOLD_JUDGED_ROOT = Path("data/gold_judged")
_RATER = "caio"
_JUDGE = "qwen3-vl"
_VARIANT: PromptVariant = "P0b"
_H5_TOLERANCE_PP = 5.0

_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")

# PRE-REGISTRATION.md's frozen headline table -- >=1 hand / active manipulation columns only
# (PPI's own "hand_count" vocabulary is the >=1-hand indicator, not "2 hands"; see ppi.py).
_PUBLISHED: dict[str, dict[str, float]] = {
    "G200-ego": {"hand_count": 0.9642, "manipulation": 0.9166},
    "G200-ego4d": {"hand_count": 0.6733, "manipulation": 0.5007},
    "G200-epic": {"hand_count": 0.9037, "manipulation": 0.8504},
}
# Real domain identifiers (D024's own corpus keys), not the raw FrameRef.corpus field -- that
# field is uniformly "egocentric-10k" across all three G200-* arms (it names the released
# evaluation dataset, not the domain), verified live against real membership data.
_CORPUS_NAME: dict[str, str] = {
    "G200-ego": "egocentric-10k",
    "G200-ego4d": "ego4d",
    "G200-epic": "epic-kitchens-100",
}
_WHY_NOT_CLUSTERED = (
    "HumanLabel carries no shared participant/cluster id with FrameRef (docs/DECISIONS.md D039)"
)


def _load_human_labels(pass_: PassType) -> list[HumanLabel]:
    return HumanLabelStore(_LABEL_STORE_ROOT / _RATER).read_pass(pass_)


def _load_judged(sample: SampleName) -> list[JudgeResponse]:
    path = _GOLD_JUDGED_ROOT / f"{sample}.P0b.json"
    return [JudgeResponse.model_validate(r) for r in json.loads(path.read_text())]


def _frame_ids_by_sample() -> dict[SampleName, set[str]]:
    return {s: {f.frame_id for f in load_membership(s, _MEMBERSHIP_ROOT)} for s in _SAMPLES}


def _intra_rater_ac1(
    primary: list[HumanLabel], retest: list[HumanLabel], task: str
) -> tuple[float, int]:
    """AC1 has no dedicated entry point in `agreement.core` (see `intra_rater_kappa`'s own
    docstring) -- built the same way that function builds Cohen's kappa, using the module's own
    (technically private, but explicitly documented as the intended reuse pattern) pair-building
    machinery."""
    categories = _categories(task)
    label_value = _LABEL_FIELD[task]
    retest_by_frame = {label.frame_id: label for label in retest}
    pairs: list[tuple[object, object]] = []
    for label in primary:
        match = retest_by_frame.get(label.frame_id)
        if match is not None:
            pairs.append((label_value(label), label_value(match)))
    return _gwet_ac1_from_pairs(pairs, categories), len(pairs)


def _intra_rater(primary: list[HumanLabel], retest: list[HumanLabel]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for task in ("hand_count", "manipulation"):
        ac1, n = _intra_rater_ac1(primary, retest, task)
        result[task] = {"ac1": ac1, "kappa": intra_rater_kappa(primary, retest, task), "n_pairs": n}
    return result


def _h4(primary: list[HumanLabel], judged_by_sample: dict[SampleName, list[JudgeResponse]]) -> dict[str, Any]:
    all_judged = [j for responses in judged_by_sample.values() for j in responses]
    result: dict[str, Any] = {}
    for task in ("hand_count", "manipulation"):
        result[task] = {
            "ac1": gwet_ac1(primary, all_judged, task),
            "kappa": cohens_kappa(primary, all_judged, task),
            "raw_agreement": raw_agreement(primary, all_judged, task),
        }
    result["holds"] = result["hand_count"]["ac1"] > result["manipulation"]["ac1"]
    return result


def _calibration(
    primary: list[HumanLabel], judged_by_sample: dict[SampleName, list[JudgeResponse]]
) -> dict[str, Any]:
    """H7, a real, disclosed deviation from `PRE-REGISTRATION.md`'s "P7 only" scoping (D060) --
    see module docstring for why: the self-hosted judge exposes real logprob confidence on
    every call, not just P7, so this reads it straight off the already-collected `P0b`
    responses against the 93 primary human-gold labels. No new judge calls."""
    all_judged_by_frame = {j.frame_id: j for responses in judged_by_sample.values() for j in responses}
    result: dict[str, Any] = {}
    for task in ("hand_count", "manipulation"):
        label_value = _LABEL_FIELD[task]
        response_value = _RESPONSE_FIELD[task]
        confidences: list[float] = []
        correct: list[bool] = []
        for label in primary:
            response = all_judged_by_frame.get(label.frame_id)
            if response is None or response.status != "ok":
                continue
            if response.confidence.kind != "logprob" or response.confidence.value is None:
                continue
            confidences.append(response.confidence.value)
            correct.append(label_value(label) == response_value(response))
        bins = reliability_bins(confidences, correct)
        report = build_calibration_report(
            judge=_JUDGE,
            task=task,
            subset="G200-primary-labelled",
            confidence_kind="logprob",
            bins=bins,
        )
        result[task] = {**report.model_dump(mode="json"), "n": len(confidences)}
    return result


def _h5(
    primary: list[HumanLabel],
    judged_by_sample: dict[SampleName, list[JudgeResponse]],
    frame_ids_by_sample: dict[SampleName, set[str]],
) -> dict[str, Any]:
    error_rates: dict[str, dict[str, Any]] = {}
    for sample in ("G200-ego", "G200-epic"):
        arm_ids = frame_ids_by_sample[sample]
        arm_labels = [label for label in primary if label.frame_id in arm_ids]
        agreement = raw_agreement(arm_labels, judged_by_sample[sample], "manipulation")
        error_rates[sample] = {"n": len(arm_labels), "error_rate": 1 - agreement}

    diff_pp = (error_rates["G200-epic"]["error_rate"] - error_rates["G200-ego"]["error_rate"]) * 100
    return {
        "egocentric": error_rates["G200-ego"],
        "epic_kitchens": error_rates["G200-epic"],
        "diff_pp": diff_pp,
        "epic_kitchens_higher": error_rates["G200-epic"]["error_rate"] > error_rates["G200-ego"]["error_rate"],
        "holds": diff_pp >= _H5_TOLERANCE_PP,
    }


def _ppi_per_domain(
    primary: list[HumanLabel],
    judged_by_sample: dict[SampleName, list[JudgeResponse]],
    frame_ids_by_sample: dict[SampleName, set[str]],
) -> dict[str, Any]:
    results: dict[str, Any] = {}
    for sample in judged_by_sample:
        arm_ids = frame_ids_by_sample[sample]
        gold = [label for label in primary if label.frame_id in arm_ids]
        judged = judged_by_sample[sample]
        results[sample] = {}
        for task in ("hand_count", "manipulation"):
            estimate = estimate_prevalence(
                corpus=_CORPUS_NAME[sample],
                task=task,
                prompt_variant=_VARIANT,
                judge=_JUDGE,
                gold=gold,
                judged=judged,
                published=_PUBLISHED[sample][task],
                cluster_by=None,
                why_not_clustered=_WHY_NOT_CLUSTERED,
            )
            results[sample][task] = estimate.model_dump(mode="json")
    return results


def main() -> int:
    primary = _load_human_labels("primary")
    retest = _load_human_labels("retest")
    judged_by_sample = {sample: _load_judged(sample) for sample in _SAMPLES}
    frame_ids_by_sample = _frame_ids_by_sample()

    output = {
        "n_primary": len(primary),
        "n_retest": len(retest),
        "intra_rater": _intra_rater(primary, retest),
        "H4": _h4(primary, judged_by_sample),
        "H5": _h5(primary, judged_by_sample, frame_ids_by_sample),
        "ppi": _ppi_per_domain(primary, judged_by_sample, frame_ids_by_sample),
        "H7_calibration": _calibration(primary, judged_by_sample),
    }
    out_path = Path("data/wave4_analysis.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
