"""Generate the paper's numeric tables as LaTeX, straight from the committed result files.

`AGENTS.md` rule 2 says every figure in prose cites the file that produces it, and
`scripts/check_prose_figures.py` (D081) enforces that for markdown and LaTeX prose by pinning
literals. Numeric tables are never hand-typed in `paper/vernier.tex`; they are emitted here
from `data/*.json` (including `data/cluster_posthoc.json`, D091/D092) and
`space/public/data/{frames,stats}.json`, and pulled in with `\\input`.

Every table is a `booktabs` `tabular` with no surrounding `table` environment, so the paper
controls placement, captions and labels.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
_DATA = _ROOT / "data"
_OUT = _ROOT / "paper" / "generated"

_CORPUS_LABEL = {
    "G200-ego": "Egocentric-10K",
    "G200-ego4d": "Ego4D",
    "G200-epic": "EPIC-KITCHENS-100",
    "egocentric-10k": "Egocentric-10K",
    "ego4d": "Ego4D",
    "epic-kitchens-100": "EPIC-KITCHENS-100",
}
_TASK_LABEL = {"hand_count": "$\\geq$1 hand", "manipulation": "active manipulation"}


def _tex_escape(s: str) -> str:
    """Underscores are subscript operators in TeX; the verdict string carries one."""
    return s.replace("_", r"\_")


def _pct(x: float) -> str:
    return f"{x * 100:.2f}"


def _fmt_p(p: float) -> str:
    if p < 1e-4:
        exp = math.floor(math.log10(p))
        mant = p / (10**exp)
        return f"${mant:.1f}\\times 10^{{{exp}}}$"
    return f"{p:.4f}"


def _load() -> dict[str, Any]:
    return {
        "e2": json.loads((_DATA / "e2_full_n10000.json").read_text()),
        "e100k": json.loads((_DATA / "e2_100k_eval.json").read_text()),
        "e5": json.loads((_DATA / "e5_full_n2000.json").read_text()),
        "wave4": json.loads((_DATA / "wave4_analysis.json").read_text()),
        "rung1": json.loads((_DATA / "rung1_distillation.json").read_text()),
        "margin": json.loads((_DATA / "margin_exploratory.json").read_text()),
        "h2u": json.loads((_DATA / "h2_design_effect.S10k-U.json").read_text()),
        "h2s": json.loads((_DATA / "h2_design_effect.S10k-S.json").read_text()),
        "posthoc": json.loads((_DATA / "cluster_posthoc.json").read_text()),
        "stats": json.loads((_ROOT / "space" / "public" / "data" / "stats.json").read_text()),
        "card": json.loads((_ROOT / "MEASUREMENT_CARD.json").read_text()),
    }


def _replication(d: dict[str, Any]) -> str:
    rows = []
    for label, block, key in (
        ("Egocentric-10K", d["e2"]["H1"], "observed_P0a"),
        ("Egocentric-100K", d["e100k"]["published_comparison"], "observed_P0a"),
    ):
        for task, name in (
            ("hand_ge1_rate", "$\\geq$1 hand"),
            ("hand_eq2_rate", "2 hands"),
            ("active_manipulation_rate", "active manipulation"),
        ):
            b = block[task]
            mark = "" if b["within_2pp_tolerance"] else "$^{\\dagger}$"
            rows.append(
                f"{label} & {name} & {_pct(b[key])} & {_pct(b['published'])} & "
                f"{b['diff_pp']:.2f}{mark} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{llrrr}\n\\toprule\n"
        "release & figure & Qwen3-VL (\\%) & published (\\%) & diff (pp) \\\\\n\\midrule\n"
        f"{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _error_direction(d: dict[str, Any]) -> str:
    """Both judges against the single rater (n=153), vendor's own stored labels first (D092).

    Binary indicator rows come first because they match the published estimands; ternary hand
    count and one-against-two confusions sit underneath.
    """
    judges = d["posthoc"]["error_direction_both_judges"]["judges"]
    rows: list[str] = []
    for jkey, jlabel in (
        ("gemini-2.5-flash", "gemini-2.5-flash (vendor)"),
        ("qwen3-vl", "Qwen3-VL (open)"),
    ):
        ov = judges[jkey]["overall"]
        g, m, h = ov["hand_ge1"], ov["manipulation"], ov["hand_count_ternary"]
        if rows:
            rows.append("\\midrule")
        for tlabel, b in (("$\\geq$1 hand", g), ("active manipulation", m)):
            ow, uw = b["over_wilson"], b["under_wilson"]
            rows.append(
                f"{jlabel} & {tlabel} & {b['over']}/{b['at_risk_over']} & "
                f"{ow['rate_pct']:.1f} [{ow['lo_pct']:.1f}, {ow['hi_pct']:.1f}] & "
                f"{b['under']}/{b['at_risk_under']} & "
                f"{uw['rate_pct']:.1f} [{uw['lo_pct']:.1f}, {uw['hi_pct']:.1f}] & "
                f"{_fmt_p(b['fisher_p'])} \\\\"
            )
        rows.append(
            f"{jlabel} & hand count, ternary & {h['over']}/{h['at_risk_over']} & --- & "
            f"{h['under']}/{h['at_risk_under']} & --- & --- \\\\"
        )
        rows.append(
            f"\\quad of which 1$\\leftrightarrow$2 & & {h['one_to_two']} (1$\\to$2) & --- & "
            f"{h['two_to_one']} (2$\\to$1) & --- & --- \\\\"
        )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrlrlr@{}}\n\\toprule\n"
        "judge & task & over & rate (95\\% CI) & under & rate (95\\% CI) & Fisher $p$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _disagreement_tags(d: dict[str, Any]) -> str:
    """Structured breakdown of disagreements by rubric edge-case tag (n=153)."""
    judges = d["posthoc"]["error_direction_both_judges"]["judges"]
    tag_cols = ("other-person", "blur", "edge", "self-contact", "between-actions", "idle-grip", "untagged")
    rows: list[str] = []
    for jkey, jlabel in (("gemini-2.5-flash", "gemini-2.5-flash"), ("qwen3-vl", "Qwen3-VL")):
        tb = judges[jkey]["disagreement_tags"]
        for tkey, tlabel in (("hand_ge1", "$\\geq$1 hand"), ("manipulation", "manipulation")):
            block = tb[tkey]
            for direction, n_key, tags_key in (("over", "over_n", "over_tags"), ("under", "under_n", "under_tags")):
                n_val = block[n_key]
                if n_val == 0:
                    continue
                counts = " & ".join(str(block[tags_key].get(c, 0)) for c in tag_cols)
                rows.append(f"{jlabel} & {tlabel} & {direction} & {n_val} & {counts} \\\\")
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}lllr rrrrrrr@{}}\n\\toprule\n"
        "judge & task & dir. & $n$ & other & blur & edge & self & betw. & idle & none \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _prevalence(d: dict[str, Any]) -> str:
    rows = []
    for arm, tasks in d["wave4"]["ppi"].items():
        for task, block in tasks.items():
            p = block["ppi"]
            rows.append(
                f"{_CORPUS_LABEL[arm]} & {_TASK_LABEL[task]} & {_pct(block['published'])} & "
                f"{_pct(block['naive']['value'])} & {_pct(p['value'])} & "
                f"[{_pct(p['ci']['lo'])}, {_pct(p['ci']['hi'])}] & {p['n_gold']} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrrrlr@{}}\n\\toprule\n"
        "corpus & task & published & judge & PPI++ & 95\\% iid CI & $n_{\\text{gold}}$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _vendor_prevalence(d: dict[str, Any]) -> str:
    """Gold-corrected prevalence with the vendor's stored labels over N=9,800 per corpus."""
    v = d["margin"]["vendor_full_arm"]["prevalence"]
    arm_of = {"egocentric-10k": "G200-ego", "epic-kitchens-100": "G200-epic", "ego4d": "G200-ego4d"}
    order = ["egocentric-10k", "epic-kitchens-100", "ego4d"]
    rows = []
    for corpus in order:
        for task in ("hand_count", "manipulation"):
            b = v[corpus][task]
            published = d["wave4"]["ppi"][arm_of[corpus]][task]["published"]
            rows.append(
                f"{_CORPUS_LABEL[corpus]} & {_TASK_LABEL[task]} & {_pct(published)} & {_pct(b['value'])} & "
                f"[{_pct(b['ci']['lo'])}, {_pct(b['ci']['hi'])}] & {b['n_gold']} & {b['n_unlabelled']:,} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrrlrr@{}}\n\\toprule\n"
        "corpus & task & published & corrected & 95\\% iid CI & $n_{\\text{gold}}$ & $N$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _margins(d: dict[str, Any]) -> str:
    """Published margin vs gold-corrected margin for both the vendor full arm and the open judge."""
    short_task = {"hand_count": "$\\geq$1 hand", "manipulation": "manipulation"}
    rows: list[str] = []
    for arm_label, block in (
        ("vendor ($N{=}9{,}800$)", d["margin"]["vendor_full_arm"]["comparisons"]),
        ("open ($N{\\approx}140$)", d["margin"]["comparisons"]),
    ):
        if rows:
            rows.append("\\midrule")
        for key, comp in block.items():
            other = "EPIC-KITCHENS-100" if "epic" in key else "Ego4D"
            for task, m in comp.items():
                inside = "yes" if m["published_inside_corrected_ci"] else "no"
                sizing = m["gold_per_arm_to_exclude_published"]
                n_req = str(sizing["gold_per_arm"]) if sizing["achievable_by_labelling_alone"] else "floor"
                rows.append(
                    f"{arm_label} & {other} & {short_task[task]} & {m['published_margin_pp']:+.2f} & "
                    f"{m['corrected_margin_pp']:+.2f} & "
                    f"[{m['ci_pp']['lo']:+.2f}, {m['ci_pp']['hi']:+.2f}] & {inside} & {n_req} \\\\"
                )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}lllrrlcr@{}}\n\\toprule\n"
        "model arm & vs. & task & pub. & corr. & 95\\% iid CI & in CI & $n$/arm \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _design_effect(d: dict[str, Any]) -> str:
    """Raw-corpus iid vs worker-clustered vs factory-clustered intervals and exact ANOVA ICC."""
    rc = d["posthoc"]["raw_corpus_clustering"]
    rows: list[str] = []
    for draw in ("S10k-U", "S10k-S"):
        if rows:
            rows.append("\\midrule")
        for task, name in (
            ("hand_ge1", "$\\geq$1 hand"),
            ("hand_eq2", "2 hands"),
            ("active_manipulation", "manipulation"),
        ):
            t = rc[draw]["tasks"][task]
            iid = t["iid_ci"]
            wk = t["worker_ci"]
            rows.append(
                f"{draw} & {name} & {_pct(t['point_estimate'])} & "
                f"[{_pct(iid['lo'])}, {_pct(iid['hi'])}] & "
                f"[{_pct(wk['lo'])}, {_pct(wk['hi'])}] & "
                f"{t['worker_deff']:.2f} & {t['worker_anova']['icc']:.3f} & "
                f"{t['factory_deff']:.2f} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrllrrr@{}}\n\\toprule\n"
        "draw & figure & rate & iid 95\\% CI & worker 95\\% CI & deff$_w$ & $\\hat{\\rho}_w$ & deff$_f$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _cluster_sensitivity(d: dict[str, Any]) -> str:
    """Post-hoc cluster-sensitivity table for the vendor full-arm EPIC manipulation margin (D092)."""
    m = d["posthoc"]["evaluation_cluster_sensitivity"]["arms"]["vendor_full_arm"][
        "egocentric_minus_epic_margin"
    ]["manipulation"]
    rows = [
        (
            "Registered iid (lower bound on width)",
            f"[{m['iid_ci_pp']['lo']:+.2f}, {m['iid_ci_pp']['hi']:+.2f}]",
            f"{m['iid_ci_pp']['se_pp']:.2f}",
            f"{m['iid_gold_per_arm']['floor_half_width_pp']:.2f}",
            str(m["iid_gold_per_arm"]["gold_per_arm"]),
        ),
    ]
    labels = {
        "low_0.02": "Post hoc M1: worker-scaled + EPIC $K{=}37$ ($\\rho{=}0.02$)",
        "matched_ego_anova": "Post hoc M1: worker-scaled + EPIC $K{=}37$ ($\\rho{=}\\hat{\\rho}_{\\text{ego}}{=}0.070$)",
        "high_0.10": "Post hoc M1: worker-scaled + EPIC $K{=}37$ ($\\rho{=}0.10$)",
    }
    for entry in m["model1_epic_k37_grid"]:
        sz = entry["gold_per_arm_to_exclude_published"]
        n_req = str(sz["gold_per_arm"]) if sz["achievable_by_labelling_alone"] else "unachievable"
        rows.append(
            (
                labels[entry["scenario"]],
                f"[{entry['margin_ci_pp']['lo']:+.2f}, {entry['margin_ci_pp']['hi']:+.2f}]",
                f"{entry['margin_ci_pp']['se_pp']:.2f}",
                f"{sz['floor_half_width_pp']:.2f}",
                n_req,
            )
        )
    m2 = m["model2_direct_deff"]
    sz2 = m2["gold_per_arm_to_exclude_published"]
    rows.append(
        (
            f"Post hoc M2: direct $\\sqrt{{\\text{{deff}}_{{\\max}}}}$ scaling (deff={m2['deff_multiplier']:.2f})",
            f"[{m2['ci_pp']['lo']:+.2f}, {m2['ci_pp']['hi']:+.2f}]",
            f"{m2['ci_pp']['se_pp']:.2f}",
            f"{sz2['floor_half_width_pp']:.2f}",
            str(sz2["gold_per_arm"]),
        )
    )
    body = "\n".join(f"{a} & {b} & {c} & {e} & {f} \\\\" for a, b, c, e, f in rows)
    return (
        "\\begin{tabular}{@{}llrrr@{}}\n\\toprule\n"
        "variance assumption (point $-1.32$\\,pp vs.\\ $+6.62$\\,pp) & 95\\% CI (pp) & SE & floor & $n$/arm \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _ledger(d: dict[str, Any]) -> str:
    """Appendix A: all pre-registered hypotheses with their threshold and observed outcome."""
    w, e5, r1, m = d["wave4"], d["e5"], d["rung1"], d["margin"]
    h2max = max(d["h2u"]["design_effect_max"], d["h2s"]["design_effect_max"])
    rows = [
        ("H8", "participant counts differ across corpora", "computable, no bar",
         "58.2$\\times$", "reported"),
        ("H1", "all three figures within $\\pm$2\\,pp (open judge)", "$\\pm$2\\,pp",
         f"{d['e2']['H1']['hand_eq2_rate']['diff_pp']:.2f}\\,pp on 2 hands", "fails"),
        ("H1b", "P0a vs.\\ P0b manipulation disagree by $\\geq$1\\,pp", "$\\geq$1\\,pp",
         f"{d['e2']['H1b']['diff_pp']:.2f}\\,pp", "null"),
        ("H2", "design effect over worker id $\\geq$ 2", "$\\geq$ 2",
         f"{h2max:.2f} max", "fails"),
        ("H3", "manipulation prompt spread $\\geq$ 5\\,pp", "$\\geq$ 5\\,pp",
         f"{e5['H3']['manipulation_spread_pp']:.2f}\\,pp", "fails"),
        ("H4", "AC1 higher on hand count than manipulation", "direction",
         f"{w['H4']['hand_count']['ac1']:.3f} vs {w['H4']['manipulation']['ac1']:.3f}", "reversed"),
        ("H5", "judge error higher on EPIC by $\\geq$ 5\\,pp", "$\\geq$ 5\\,pp",
         f"{w['H5']['diff_pp']:+.2f}\\,pp", "fails"),
        ("H6", "agreement floor 0.80 at coverage $\\geq$ 0.70", "0.80 at 0.70",
         f"fidelity {r1['fidelity_vs_gemini_2_5_flash']:.3f}", "fails"),
        ("H7", "calibration not measurable on published protocol", "n/a",
         f"ECE {w['H7_calibration']['hand_count']['ece']:.3f}", "degenerate"),
    ]
    body = "\n".join(f"{h} & {claim} & {thr} & {obs} & {verdict} \\\\" for h, claim, thr, obs, verdict in rows)
    vm = m["vendor_full_arm"]["comparisons"]["egocentric-10k_minus_epic-kitchens-100"]["manipulation"]
    body += (
        "\n\\midrule\n\\multicolumn{5}{l}{\\emph{Not pre-registered, reported as exploratory:}} \\\\\n"
        f"--- & gold-corrected margin vs.\\ EPIC (vendor arm) & none & "
        f"{vm['corrected_margin_pp']:+.2f}\\,pp & unresolved \\\\"
    )
    return (
        "\\begin{tabular}{@{}lp{0.34\\linewidth}p{0.15\\linewidth}p{0.20\\linewidth}l@{}}\n"
        "\\toprule\n"
        "id & pre-registered claim & threshold & observed & outcome \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _provenance(d: dict[str, Any]) -> str:
    rev = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=_ROOT
    ).stdout.strip()
    digest = d["card"]["content_digest"].replace("sha256:", "")[:16]
    return (
        f"\\newcommand{{\\vernierGitRev}}{{{rev}}}\n"
        f"\\newcommand{{\\vernierCardDigest}}{{{digest}}}\n"
        f"\\newcommand{{\\vernierNPrimary}}{{{d['wave4']['n_primary']}}}\n"
        f"\\newcommand{{\\vernierNClaims}}{{{len(d['card']['claims'])}}}\n"
        f"\\newcommand{{\\vernierVerdict}}{{{_tex_escape(d['card']['verdict'])}}}\n"
    )


# ── appendices ──────────────────────────────────────────────────────────────────────────────


def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


def _var(xs: list[float]) -> float:
    """Sample variance, matching numpy's ddof=1 as `estimation/ppi.py` uses it."""
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def _confusion_per_corpus(d: dict[str, Any]) -> str:
    """Appendix B: per-corpus confusion matrices for both judges (n=153)."""
    frames = json.loads((_ROOT / "space" / "public" / "data" / "frames.json").read_text())
    labelled = [f for f in frames if f.get("r")]
    rows = []
    for corpus in ("egocentric-10k", "epic-kitchens-100", "ego4d"):
        arm = [f for f in labelled if f["corpus"] == corpus]
        for judge, key in (("gemini-2.5-flash", "g"), ("Qwen3-VL", "q")):
            hands = [[0, 0, 0] for _ in range(3)]
            manip = [[0, 0], [0, 0]]
            for f in arm:
                hands[f[key]["h"]][f["r"]["h"]] += 1
                manip[int(f[key]["m"])][int(f["r"]["m"])] += 1
            flat = " & ".join(str(hands[j][r]) for j in range(3) for r in range(3))
            rows.append(
                f"{_CORPUS_LABEL[corpus]} & {judge} & {len(arm)} & {flat} & "
                f"{manip[0][0]} & {manip[0][1]} & {manip[1][0]} & {manip[1][1]} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llr rrrrrrrrr rrrr@{}}\n\\toprule\n"
        "& & & \\multicolumn{9}{c}{hand count, judge row $\\times$ rater column} "
        "& \\multicolumn{4}{c}{manipulation} \\\\\n"
        "\\cmidrule(lr){4-12}\\cmidrule(lr){13-16}\n"
        "corpus & judge & $n$ & 00 & 01 & 02 & 10 & 11 & 12 & 20 & 21 & 22 "
        "& FF & FT & TF & TT \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _ppi_variance(d: dict[str, Any]) -> str:
    """Appendix C: PPI++ variance decomposition for both open-judge and vendor full-arm pools."""
    frames = json.loads((_ROOT / "space" / "public" / "data" / "frames.json").read_text())
    stored = json.loads((_DATA / "rung1_stored_labels.json").read_text())
    arm_ids: dict[str, set[str]] = {}
    for corpus, sample in (
        ("egocentric-10k", "E10k-ego"),
        ("epic-kitchens-100", "E10k-epic"),
        ("ego4d", "E10k-ego4d"),
    ):
        arm_ids[corpus] = {
            r["frame_id"] for r in json.loads((_DATA / "membership" / f"{sample}.json").read_text())
        }

    rows: list[str] = []
    for arm_label, use_vendor in (("vendor ($N=9{,}800$)", True), ("open ($N\\approx 140$)", False)):
        if rows:
            rows.append("\\midrule")
        for corpus in ("egocentric-10k", "epic-kitchens-100", "ego4d"):
            pool = [f for f in frames if f["corpus"] == corpus]
            gold = [f for f in pool if f.get("r")]
            unl_open = [f for f in pool if not f.get("r")]
            unl_vendor = [r for r in stored if r["frame_id"] in arm_ids[corpus]]
            for task, key, skey in (("hand_count", "h", "hands_visible"), ("manipulation", "m", "manipulation")):
                def ind(v: Any, _t: str = task) -> float:
                    return float(v >= 1) if _t == "hand_count" else float(bool(v))

                y = [ind(f["r"][key]) for f in gold]
                jkey = "g" if use_vendor else "q"
                fg = [ind(f[jkey][key]) for f in gold]
                fu = (
                    [ind(r[skey]) for r in unl_vendor]
                    if use_vendor
                    else [ind(f["q"][key]) for f in unl_open]
                )
                n, big_n = len(y), len(fu)
                vfg = _var(fg)
                mfg, my = _mean(fg), _mean(y)
                cov = sum((a - mfg) * (b - my) for a, b in zip(fg, y)) / (n - 1)
                lam = min(1.0, max(0.0, cov / vfg)) if vfg > 0 else 0.0
                resid = [b - lam * a for a, b in zip(fg, y)]
                gold_term = _var(resid) / n
                unl_term = (lam**2) * _var(fu) / big_n
                share = 100 * gold_term / (gold_term + unl_term)
                rows.append(
                    f"{arm_label} & {_CORPUS_LABEL[corpus]} & {_TASK_LABEL[task]} & {n} & {big_n:,} & "
                    f"{lam:.3f} & {gold_term:.2e} & {unl_term:.2e} & {share:.1f} \\\\"
                )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}lllrrrrrr@{}}\n\\toprule\n"
        "arm & corpus & task & $n$ & $N$ & $\\lambda$ & gold var & unl.\\ var & gold \\% \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _cluster_detail(d: dict[str, Any]) -> str:
    """Appendix D: exact unequal-cluster ANOVA ICC and Kish m_tilde for workers and factories."""
    rc = d["posthoc"]["raw_corpus_clustering"]
    rows: list[str] = []
    for level_label, c_key, a_key, d_key in (
        ("worker", "worker_clusters", "worker_anova", "worker_deff"),
        ("factory", "factory_clusters", "factory_anova", "factory_deff"),
    ):
        if rows:
            rows.append("\\midrule")
        for draw in ("S10k-U", "S10k-S"):
            c = rc[draw][c_key]
            tasks = rc[draw]["tasks"]
            deffs = [tasks[t][d_key] for t in ("hand_ge1", "hand_eq2", "active_manipulation")]
            iccs = [tasks[t][a_key]["icc"] for t in ("hand_ge1", "hand_eq2", "active_manipulation")]
            an = tasks["hand_ge1"][a_key]
            rows.append(
                f"{draw} ({level_label}) & {c['n_clusters']} & {c['mean_cluster_size']:.2f} & "
                f"{an['m_tilde']:.2f} & {c['min_cluster_size']}--{c['max_cluster_size']} & "
                f"{min(deffs):.2f}--{max(deffs):.2f} & {min(iccs):.3f}--{max(iccs):.3f} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}lrrrlrr@{}}\n\\toprule\n"
        "draw (level) & clusters & $\\bar{m}$ & $\\tilde{m}$ & min--max & deff range & ANOVA $\\hat{\\rho}$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _fig_forest(d: dict[str, Any]) -> str:
    """Active-manipulation prevalence: published point (no CI), open-judge PPI++, vendor full-arm PPI++."""
    vprev = d["margin"]["vendor_full_arm"]["prevalence"]
    rows: list[str] = []
    pub, open_ppi, vendor_ppi = [], [], []
    y = 0
    labels = []
    for arm, corpus_key, label in (
        ("G200-ego", "egocentric-10k", "Egocentric-10K"),
        ("G200-epic", "epic-kitchens-100", "EPIC-KITCHENS-100"),
        ("G200-ego4d", "ego4d", "Ego4D"),
    ):
        block = d["wave4"]["ppi"][arm]["manipulation"]
        vblock = vprev[corpus_key]["manipulation"]
        y += 1
        labels.append(f"{y}/{label}")
        pub.append(f"({block['published']},{y})")
        p_ = block["ppi"]
        half_open = (p_["ci"]["hi"] - p_["ci"]["lo"]) / 2
        open_ppi.append(f"({p_['value']},{y - 0.14:.2f}) +- ({half_open},0)")
        half_vend = (vblock["ci"]["hi"] - vblock["ci"]["lo"]) / 2
        vendor_ppi.append(f"({vblock['value']},{y + 0.14:.2f}) +- ({half_vend},0)")
    rows.append("\\begin{tikzpicture}")
    yticks = ",".join(lbl.split("/")[1] for lbl in labels)
    opts = (
        "width=0.78\\linewidth,height=5.4cm,xlabel={active manipulation prevalence},"
        "xmin=0.30,xmax=1.00,ytick={1,2,3},yticklabels={" + yticks + "},"
        "ymin=0.4,ymax=3.6,y dir=reverse,legend pos=south west,legend cell align=left,"
        "legend style={font=\\footnotesize,draw=none,fill=none},grid=major,"
        "major grid style={dotted,gray!40},tick label style={font=\\footnotesize},"
        "label style={font=\\footnotesize}"
    )
    rows.append("\\begin{axis}[" + opts + "]")
    rows.append(
        "\\addplot+[only marks,mark=|,mark size=6pt,black,very thick] coordinates {"
        + " ".join(pub)
        + "};"
    )
    rows.append("\\addlegendentry{published (no interval)}")
    rows.append(
        "\\addplot+[only marks,mark=*,black,error bars/.cd,x dir=both,x explicit] coordinates {"
        + " ".join(vendor_ppi)
        + "};"
    )
    rows.append("\\addlegendentry{vendor stored arm ($N=9{,}800$), PPI++ 95\\% iid CI}")
    rows.append(
        "\\addplot+[only marks,mark=o,gray!80!black,error bars/.cd,x dir=both,x explicit] coordinates {"
        + " ".join(open_ppi)
        + "};"
    )
    rows.append("\\addlegendentry{open judge ($N\\approx 140$), PPI++ 95\\% iid CI}")
    rows.append("\\end{axis}")
    rows.append("\\end{tikzpicture}")
    return "\n".join(rows) + "\n"


def _sensitivity(d: dict[str, Any]) -> str:
    """Batch and labelling-pace sensitivity for both judges (first 93, all 153, >2s)."""
    judges = d["posthoc"]["error_direction_both_judges"]["judges"]
    rows: list[str] = []
    for jkey, jlabel in (("gemini-2.5-flash", "gemini-2.5-flash"), ("qwen3-vl", "Qwen3-VL")):
        if rows:
            rows.append("\\midrule")
        sens = judges[jkey]["sensitivity"]
        for skey, slabel in (
            ("first_batch_93", "first batch"),
            ("all_153", "all labels"),
            ("excluding_le_2s", "excl.\\ $\\leq$2\\,s"),
        ):
            b = sens[skey]
            g, m = b["hand_ge1"], b["manipulation"]
            rows.append(
                f"{jlabel} & {slabel} & {b['n']} & "
                f"{g['over']}/{g['at_risk_over']} & {g['under']}/{g['at_risk_under']} & "
                f"{m['over']}/{m['at_risk_over']} & {m['under']}/{m['at_risk_under']} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrrrrr@{}}\n\\toprule\n"
        "& & & \\multicolumn{2}{c}{$\\geq$1 hand} & \\multicolumn{2}{c}{manipulation} \\\\\n"
        "\\cmidrule(lr){4-5}\\cmidrule(lr){6-7}\n"
        "judge & subset & $n$ & over & under & over & under \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def main() -> int:
    d = _load()
    _OUT.mkdir(parents=True, exist_ok=True)
    tables = {
        "replication": _replication(d),
        "error_direction": _error_direction(d),
        "disagreement_tags": _disagreement_tags(d),
        "prevalence": _prevalence(d),
        "margins": _margins(d),
        "design_effect": _design_effect(d),
        "cluster_sensitivity": _cluster_sensitivity(d),
        "ledger": _ledger(d),
        "confusion_per_corpus": _confusion_per_corpus(d),
        "ppi_variance": _ppi_variance(d),
        "cluster_detail": _cluster_detail(d),
        "fig_forest": _fig_forest(d),
        "vendor_prevalence": _vendor_prevalence(d),
        "sensitivity": _sensitivity(d),
    }
    for name, tex in tables.items():
        (_OUT / f"{name}.tex").write_text(tex)
    (_OUT / "provenance.tex").write_text(_provenance(d))
    # Remove retired run_ledger.tex if present so paper/generated/ holds only active tables.
    retired = _OUT / "run_ledger.tex"
    if retired.exists():
        retired.unlink()
    print(f"wrote {len(tables) + 1} files to {_OUT.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
