"""Post-hoc cluster and error-direction analyses for paper v2 (`docs/DECISIONS.md` D091).

Reads only committed artifacts under `data/` and `space/public/data/frames.json`; makes zero
network or API calls and modifies no registered artifact (`data/wave4_analysis.json`,
`data/h2_design_effect.*.json`, `data/margin_exploratory.json`, `MEASUREMENT_CARD.json`).

Computes three blocks specified in D091 before this script was run:
- `raw_corpus_clustering`: exact unequal-cluster one-way ANOVA ICC (`worker_id`), Kish's
  unequal-cluster factor `m_tilde`, and factory-level cluster-bootstrap CIs / design effects
  (`factory_id`, B=10,000, seed 777) on `S10k-U` and `S10k-S`.
- `evaluation_cluster_sensitivity`: post-hoc cluster-sensitivity bounds for the evaluation-arm
  PPI++ intervals, comparative margins, and gold-set sizing (both vendor 9,800-frame stored arm
  and open-judge 200-frame arm), because Build AI's evaluation parquets ship bare UUID4
  `frame_id`s with no cluster identifier (F9), preventing direct Cluster-Robust PPI++
  (Broska & Howes, 2026, arXiv:2610.09601).
- `error_direction_both_judges`: exact counts, Wilson 95% CIs, two-sided Fisher's exact
  p-values, batch/pace sensitivity subsets, per-corpus cells, and rubric edge-case tag counts
  for both `gemini-2.5-flash` (vendor, stored) and `Qwen3-VL` (open, live).
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scipy.stats import fisher_exact, norm

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))

from h2_design_effect import HEADLINE_TASKS, cluster_size_summary, outcomes_from_responses  # noqa: E402
from margin_analysis import (  # noqa: E402
    _COMPARISONS,
    _CORPUS_NAME,
    _PUBLISHED,
    _SAMPLES,
    _gold_needed_to_exclude,
    _load_judged,
    _load_labels,
    _variance_components,
    _vendor_full_arm,
)

from vernier.estimation.bootstrap import (  # noqa: E402
    CLUSTER_BOOTSTRAP_B,
    CLUSTER_BOOTSTRAP_SEED,
    cluster_bootstrap_ci,
    design_effect,
)
from vernier.models import FrameRef, JudgeResponse  # noqa: E402
from vernier.sampling.membership import load_membership  # noqa: E402

_DATA = _ROOT / "data"
_FRAMES_PATH = _ROOT / "space" / "public" / "data" / "frames.json"
_OUT_PATH = _DATA / "cluster_posthoc.json"
_Z = float(norm.ppf(0.975))
_EPIC_PARTICIPANTS = 37
_EPIC_ICC_GRID = (0.02, 0.10)
_TASK_TO_H2 = {"hand_count": "hand_ge1", "manipulation": "active_manipulation"}


def anova_icc(values: list[float], cluster_ids: list[str]) -> dict[str, float]:
    """Exact one-way random-effects ANOVA intra-cluster correlation for unequal cluster sizes.

    Uses the standard unequal-cluster effective size:
        m0 = (1 / (K - 1)) * (N - sum(m_i^2) / N)
        rho = (MSB - MSW) / (MSB + (m0 - 1) * MSW)
    and also reports Kish's unequal-cluster factor m_tilde = sum(m_i^2) / N and the analytic
    design effect 1 + (m_tilde - 1) * rho.
    """
    if len(values) != len(cluster_ids):
        raise ValueError("values and cluster_ids must have the same length")
    n_total = len(values)
    if n_total < 2:
        raise ValueError("need at least two observations")

    groups: dict[str, list[float]] = {}
    for v, cid in zip(values, cluster_ids, strict=True):
        groups.setdefault(cid, []).append(float(v))

    k = len(groups)
    if k < 2:
        return {
            "icc": 0.0,
            "m_bar": float(n_total),
            "m0": float(n_total),
            "m_tilde": float(n_total),
            "cv_cluster_size": 0.0,
            "sum_p_sq": 1.0,
            "deff_analytic": 1.0,
        }

    grand_mean = sum(values) / n_total
    ssb = 0.0
    ssw = 0.0
    sum_m_sq = 0
    for grp in groups.values():
        m_i = len(grp)
        sum_m_sq += m_i * m_i
        mean_i = sum(grp) / m_i
        ssb += m_i * (mean_i - grand_mean) ** 2
        ssw += sum((x - mean_i) ** 2 for x in grp)

    m_bar = n_total / k
    m_tilde = sum_m_sq / n_total
    m0 = (n_total - m_tilde) / (k - 1)
    cv_sq = max(0.0, m_tilde / m_bar - 1.0)
    sum_p_sq = sum_m_sq / (n_total * n_total)

    if n_total == k:
        # All clusters are singletons: within-cluster variance is unidentifiable (0 df).
        icc = 0.0
    else:
        msb = ssb / (k - 1)
        msw = ssw / (n_total - k)
        denom = msb + (m0 - 1.0) * msw
        icc = 0.0 if denom == 0.0 else (msb - msw) / denom

    deff_analytic = 1.0 + (m_tilde - 1.0) * max(0.0, icc)
    return {
        "icc": float(icc),
        "m_bar": float(m_bar),
        "m0": float(m0),
        "m_tilde": float(m_tilde),
        "cv_cluster_size": float(math.sqrt(cv_sq)),
        "sum_p_sq": float(sum_p_sq),
        "deff_analytic": float(deff_analytic),
    }


def wilson_ci(k: int, n: int) -> dict[str, float]:
    """95% Wilson score interval for a binomial proportion, reported in percent."""
    if n <= 0:
        return {"rate_pct": 0.0, "lo_pct": 0.0, "hi_pct": 0.0}
    p = k / n
    z2 = _Z * _Z
    denom = 1.0 + z2 / n
    center = (p + z2 / (2.0 * n)) / denom
    half = _Z * math.sqrt((p * (1.0 - p) + z2 / (4.0 * n)) / n) / denom
    return {
        "rate_pct": p * 100.0,
        "lo_pct": max(0.0, center - half) * 100.0,
        "hi_pct": min(1.0, center + half) * 100.0,
    }


def expected_m_tilde(n: int, sum_p_sq: float) -> float:
    """Expected Kish cluster factor E[sum m_i^2] / n under multinomial sampling of n units."""
    if n <= 1:
        return 1.0
    return 1.0 + (n - 1) * sum_p_sq


def _load_jsonl_responses(path: Path) -> list[JudgeResponse]:
    out: list[JudgeResponse] = []
    for line in path.read_text().splitlines():
        if line.strip():
            out.append(JudgeResponse.model_validate(json.loads(line)))
    return out


def _raw_corpus_clustering(
    *, B: int = CLUSTER_BOOTSTRAP_B, seed: int = CLUSTER_BOOTSTRAP_SEED
) -> dict[str, Any]:
    arms: dict[str, Any] = {}
    for arm in ("S10k-U", "S10k-S"):
        h2 = json.loads((_DATA / f"h2_design_effect.{arm}.json").read_text())
        membership = [
            FrameRef.model_validate(r)
            for r in json.loads((_DATA / "membership" / f"{arm}.json").read_text())
        ]
        by_id = {f.frame_id: f for f in membership}
        responses = _load_jsonl_responses(_DATA / f"h2_design_effect.{arm}.{arm}.responses.jsonl")
        outcomes, kept = outcomes_from_responses(responses)
        worker_ids = [str(by_id[fid].worker_id) for fid in kept]
        factory_ids = [str(by_id[fid].factory_id) for fid in kept]

        tasks_out: dict[str, Any] = {}
        for task in HEADLINE_TASKS:
            vals = outcomes[task]
            worker_anova = anova_icc(vals, worker_ids)
            factory_anova = anova_icc(vals, factory_ids)
            iid_ci = h2["tasks"][task]["iid"]
            worker_ci = h2["tasks"][task]["cluster"]
            factory_boot = cluster_bootstrap_ci(vals, factory_ids, B=B, seed=seed)
            iid_obj = cluster_bootstrap_ci(vals, None, B=B, seed=seed)
            # Use the committed iid width for the factory deff ratio so both ratios share one denominator.
            iid_width = float(iid_ci["hi"] - iid_ci["lo"])
            fac_width = factory_boot.hi - factory_boot.lo
            factory_deff = (fac_width / iid_width) ** 2
            tasks_out[task] = {
                "point_estimate": float(h2["tasks"][task]["point_estimate"]),
                "iid_ci": iid_ci,
                "worker_ci": worker_ci,
                "worker_deff": float(h2["tasks"][task]["design_effect"]),
                "worker_width_excess_pct": (float(h2["tasks"][task]["design_effect"]) ** 0.5 - 1.0) * 100.0,
                "worker_anova": worker_anova,
                "factory_ci": factory_boot.model_dump(mode="json"),
                "factory_deff": float(factory_deff),
                "factory_deff_fresh_iid": float(design_effect(factory_boot, iid_obj)),
                "factory_width_excess_pct": (factory_deff**0.5 - 1.0) * 100.0,
                "factory_anova": factory_anova,
            }

        arms[arm] = {
            "n_ok": len(kept),
            "worker_clusters": cluster_size_summary(worker_ids),
            "factory_clusters": cluster_size_summary(factory_ids),
            "tasks": tasks_out,
        }
    return arms


def _evaluation_cluster_sensitivity(raw_clustering: dict[str, Any]) -> dict[str, Any]:
    margin_data = json.loads((_DATA / "margin_exploratory.json").read_text())
    wave4 = json.loads((_DATA / "wave4_analysis.json").read_text())

    primary = _load_labels()
    judged_open = {s: _load_judged(s) for s in _SAMPLES}
    ids = {s: {f.frame_id for f in load_membership(s, _DATA / "membership")} for s in _SAMPLES}

    # Empirical worker sampling structure from S10k-U (uniform draw) and max measured H2 deff.
    u_tasks = raw_clustering["S10k-U"]["tasks"]
    s_tasks = raw_clustering["S10k-S"]["tasks"]

    ego_sum_p_sq = float(u_tasks["active_manipulation"]["worker_anova"]["sum_p_sq"])
    epic_sum_p_sq = 1.0 / _EPIC_PARTICIPANTS

    def _ci_from_se(point: float, se: float) -> dict[str, float]:
        return {"lo": (point - _Z * se) * 100.0, "hi": (point + _Z * se) * 100.0, "se_pp": se * 100.0}

    arm_outputs: dict[str, Any] = {}
    for arm_name, use_vendor in (("vendor_full_arm", True), ("open_judge_arm", False)):
        comps: dict[str, dict[str, tuple[float, float, int, int]]] = {}
        points: dict[str, dict[str, float]] = {}
        for sample in _SAMPLES:
            gold = [lab for lab in primary if lab.frame_id in ids[sample]]
            pool = _vendor_full_arm(sample, gold) if use_vendor else judged_open[sample]
            corpus = _CORPUS_NAME[sample]
            comps[sample] = {
                task: _variance_components(gold, pool, task) for task in ("hand_count", "manipulation")
            }
            if use_vendor:
                points[sample] = {
                    task: float(margin_data["vendor_full_arm"]["prevalence"][corpus][task]["value"])
                    for task in ("hand_count", "manipulation")
                }
            else:
                points[sample] = {
                    task: float(wave4["ppi"][sample][task]["ppi"]["value"])
                    for task in ("hand_count", "manipulation")
                }

        ego_prev_sens: dict[str, Any] = {}
        margin_sens: dict[str, Any] = {}
        for task in ("hand_count", "manipulation"):
            h2_key = _TASK_TO_H2[task]
            rho_ego = float(u_tasks[h2_key]["worker_anova"]["icc"])
            deff_max = max(float(u_tasks[h2_key]["worker_deff"]), float(s_tasks[h2_key]["worker_deff"]))

            v_res_ego, v_unl_ego, n_ego, big_n_ego = comps["G200-ego"][task]
            v_res_epic, v_unl_epic, n_epic, big_n_epic = comps["G200-epic"][task]

            # Model 1: empirical worker-share scaling on Egocentric-10K
            m_ego_gold = expected_m_tilde(n_ego, ego_sum_p_sq)
            m_ego_unl = expected_m_tilde(big_n_ego, ego_sum_p_sq)
            deff_ego_gold = 1.0 + (m_ego_gold - 1.0) * max(0.0, rho_ego)
            deff_ego_unl = 1.0 + (m_ego_unl - 1.0) * max(0.0, rho_ego)

            var_ego_iid = v_res_ego / n_ego + v_unl_ego
            var_ego_m1 = deff_ego_gold * (v_res_ego / n_ego) + deff_ego_unl * v_unl_ego
            var_ego_m2 = deff_max * var_ego_iid

            ego_pt = points["G200-ego"][task]
            ego_prev_sens[task] = {
                "point_pct": ego_pt * 100.0,
                "rho_ego_anova": rho_ego,
                "deff_max_measured": deff_max,
                "model1_ego_deff_gold": deff_ego_gold,
                "model1_ego_deff_unl": deff_ego_unl,
                "iid_ci_pct": _ci_from_se(ego_pt, math.sqrt(var_ego_iid)),
                "model1_worker_scaled_ci_pct": _ci_from_se(ego_pt, math.sqrt(var_ego_m1)),
                "model2_direct_deff_ci_pct": _ci_from_se(ego_pt, math.sqrt(var_ego_m2)),
            }

            # Egocentric-10K minus EPIC-KITCHENS-100 margin sensitivity
            epic_pt = points["G200-epic"][task]
            margin_pt = ego_pt - epic_pt
            pub_margin = _PUBLISHED["G200-ego"][task] - _PUBLISHED["G200-epic"][task]

            var_epic_iid = v_res_epic / n_epic + v_unl_epic
            var_margin_iid = var_ego_iid + var_epic_iid

            # Model 2: conservative direct sqrt(deff_max) scaling on both arms
            var_margin_m2 = deff_max * var_margin_iid
            m2_sizing = _gold_needed_to_exclude(
                margin_pt,
                pub_margin,
                deff_max * (v_res_ego + v_res_epic),
                deff_max * (v_unl_ego + v_unl_epic),
            )

            # Model 1 grid over assumed EPIC-KITCHENS-100 participant ICC (K=37)
            m_epic_gold = expected_m_tilde(n_epic, epic_sum_p_sq)
            m_epic_unl = expected_m_tilde(big_n_epic, epic_sum_p_sq)
            epic_grid: list[dict[str, Any]] = []
            for label, rho_epic in (
                ("low_0.02", _EPIC_ICC_GRID[0]),
                ("matched_ego_anova", max(0.0, rho_ego)),
                ("high_0.10", _EPIC_ICC_GRID[1]),
            ):
                deff_epic_gold = 1.0 + (m_epic_gold - 1.0) * rho_epic
                deff_epic_unl = 1.0 + (m_epic_unl - 1.0) * rho_epic
                var_epic_m1 = deff_epic_gold * (v_res_epic / n_epic) + deff_epic_unl * v_unl_epic
                var_m1 = var_ego_m1 + var_epic_m1
                ci_m1 = _ci_from_se(margin_pt, math.sqrt(var_m1))
                # Sizing under Model 1 holds cluster-inflated unlabelled floor fixed and inflates
                # each arm's gold residual variance by its cluster factor at current n.
                m1_sizing = _gold_needed_to_exclude(
                    margin_pt,
                    pub_margin,
                    deff_ego_gold * v_res_ego + deff_epic_gold * v_res_epic,
                    deff_ego_unl * v_unl_ego + deff_epic_unl * v_unl_epic,
                )
                epic_grid.append(
                    {
                        "scenario": label,
                        "rho_epic": rho_epic,
                        "epic_deff_gold": deff_epic_gold,
                        "epic_deff_unl": deff_epic_unl,
                        "margin_ci_pp": ci_m1,
                        "published_inside_ci": bool(ci_m1["lo"] <= pub_margin * 100.0 <= ci_m1["hi"]),
                        "gold_per_arm_to_exclude_published": m1_sizing,
                    }
                )

            ci_m2 = _ci_from_se(margin_pt, math.sqrt(var_margin_m2))
            margin_sens[task] = {
                "published_margin_pp": pub_margin * 100.0,
                "corrected_margin_pp": margin_pt * 100.0,
                "iid_ci_pp": _ci_from_se(margin_pt, math.sqrt(var_margin_iid)),
                "iid_gold_per_arm": _gold_needed_to_exclude(
                    margin_pt, pub_margin, v_res_ego + v_res_epic, v_unl_ego + v_unl_epic
                ),
                "model2_direct_deff": {
                    "deff_multiplier": deff_max,
                    "ci_pp": ci_m2,
                    "published_inside_ci": bool(ci_m2["lo"] <= pub_margin * 100.0 <= ci_m2["hi"]),
                    "gold_per_arm_to_exclude_published": m2_sizing,
                },
                "model1_epic_k37_grid": epic_grid,
            }

        arm_outputs[arm_name] = {
            "egocentric_10k_prevalence": ego_prev_sens,
            "egocentric_minus_epic_margin": margin_sens,
        }

    # Check exact comparison list parity with margin_analysis
    assert _COMPARISONS[0] == ("G200-ego", "G200-epic")
    return {
        "why_sensitivity_not_direct": (
            "Build AI's evaluation parquets ship frame_id as a bare UUID4 with worker_id=null, "
            "factory_id=null, clip_id=null across all 30,000 evaluation frames (F9), so direct "
            "Cluster-Robust PPI++ (Broska & Howes, 2026, arXiv:2610.09601) cannot be computed on "
            "the evaluation arms."
        ),
        "ego_s10ku_sum_p_sq": ego_sum_p_sq,
        "epic_participants_K": _EPIC_PARTICIPANTS,
        "arms": arm_outputs,
    }


def _judge_error_block(frames: list[dict[str, Any]], jkey: str) -> dict[str, Any]:
    h_o = sum(1 for f in frames if f["r"]["h"] == 0 and f[jkey]["h"] >= 1)
    h_ao = sum(1 for f in frames if f["r"]["h"] == 0)
    h_u = sum(1 for f in frames if f["r"]["h"] >= 1 and f[jkey]["h"] == 0)
    h_au = sum(1 for f in frames if f["r"]["h"] >= 1)
    _, p_h = fisher_exact([[h_o, h_ao - h_o], [h_u, h_au - h_u]])

    m_o = sum(1 for f in frames if (not f["r"]["m"]) and f[jkey]["m"])
    m_ao = sum(1 for f in frames if not f["r"]["m"])
    m_u = sum(1 for f in frames if f["r"]["m"] and (not f[jkey]["m"]))
    m_au = sum(1 for f in frames if f["r"]["m"])
    _, p_m = fisher_exact([[m_o, m_ao - m_o], [m_u, m_au - m_u]])

    ht_o = sum(1 for f in frames if f[jkey]["h"] > f["r"]["h"])
    ht_ao = sum(1 for f in frames if f["r"]["h"] < 2)
    ht_u = sum(1 for f in frames if f[jkey]["h"] < f["r"]["h"])
    ht_au = sum(1 for f in frames if f["r"]["h"] > 0)
    one_to_two = sum(1 for f in frames if f["r"]["h"] == 1 and f[jkey]["h"] == 2)
    two_to_one = sum(1 for f in frames if f["r"]["h"] == 2 and f[jkey]["h"] == 1)

    return {
        "n": len(frames),
        "hand_ge1": {
            "over": h_o,
            "at_risk_over": h_ao,
            "over_wilson": wilson_ci(h_o, h_ao),
            "under": h_u,
            "at_risk_under": h_au,
            "under_wilson": wilson_ci(h_u, h_au),
            "fisher_p": float(p_h),
        },
        "manipulation": {
            "over": m_o,
            "at_risk_over": m_ao,
            "over_wilson": wilson_ci(m_o, m_ao),
            "under": m_u,
            "at_risk_under": m_au,
            "under_wilson": wilson_ci(m_u, m_au),
            "fisher_p": float(p_m),
        },
        "hand_count_ternary": {
            "over": ht_o,
            "at_risk_over": ht_ao,
            "under": ht_u,
            "at_risk_under": ht_au,
            "one_to_two": one_to_two,
            "two_to_one": two_to_one,
        },
    }


def _error_direction_both_judges() -> dict[str, Any]:
    frames = [f for f in json.loads(_FRAMES_PATH.read_text()) if f.get("r")]
    cut = "2026-09-04"
    subsets = {
        "first_batch_93": [f for f in frames if f["r"]["at"] < cut],
        "all_153": frames,
        "excluding_le_2s": [f for f in frames if f["r"]["s"] > 2],
    }

    judges_out: dict[str, Any] = {}
    for jname, jkey in (("gemini-2.5-flash", "g"), ("qwen3-vl", "q")):
        per_corpus: dict[str, Any] = {}
        for corpus in ("egocentric-10k", "epic-kitchens-100", "ego4d"):
            arm = [f for f in frames if f["corpus"] == corpus]
            per_corpus[corpus] = _judge_error_block(arm, jkey)

        tag_breakdown: dict[str, Any] = {}
        for task_name, pred_j, pred_r in (
            ("hand_ge1", lambda f, k=jkey: f[k]["h"] >= 1, lambda f: f["r"]["h"] >= 1),
            ("manipulation", lambda f, k=jkey: bool(f[k]["m"]), lambda f: bool(f["r"]["m"])),
        ):
            over_fs = [f for f in frames if pred_j(f) and not pred_r(f)]
            under_fs = [f for f in frames if not pred_j(f) and pred_r(f)]

            def _tag_counts(fs: list[dict[str, Any]]) -> dict[str, int]:
                c: Counter[str] = Counter()
                for f in fs:
                    tags = f["r"]["e"]
                    if not tags:
                        c["untagged"] += 1
                    else:
                        for t in tags:
                            c[t] += 1
                # Explicitly pin idle-grip so zero is never ambiguous.
                c.setdefault("idle-grip", 0)
                return dict(sorted(c.items()))

            tag_breakdown[task_name] = {
                "over_n": len(over_fs),
                "over_in_atlas": sum(1 for f in over_fs if f["t"] is not None),
                "over_tags": _tag_counts(over_fs),
                "under_n": len(under_fs),
                "under_in_atlas": sum(1 for f in under_fs if f["t"] is not None),
                "under_tags": _tag_counts(under_fs),
            }

        judges_out[jname] = {
            "overall": _judge_error_block(frames, jkey),
            "per_corpus": per_corpus,
            "sensitivity": {sub: _judge_error_block(fs, jkey) for sub, fs in subsets.items()},
            "disagreement_tags": tag_breakdown,
        }

    return {
        "n_primary": len(frames),
        "judges": judges_out,
    }


def run_posthoc(*, B: int = CLUSTER_BOOTSTRAP_B, seed: int = CLUSTER_BOOTSTRAP_SEED) -> dict[str, Any]:
    raw_clustering = _raw_corpus_clustering(B=B, seed=seed)
    return {
        "decision": "D091",
        "status": "post_hoc",
        "B": B,
        "seed": seed,
        "raw_corpus_clustering": raw_clustering,
        "evaluation_cluster_sensitivity": _evaluation_cluster_sensitivity(raw_clustering),
        "error_direction_both_judges": _error_direction_both_judges(),
    }


def main() -> int:
    payload = run_posthoc()
    _OUT_PATH.write_text(json.dumps(payload, indent=2) + "\n")
    print(f"wrote {_OUT_PATH.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
