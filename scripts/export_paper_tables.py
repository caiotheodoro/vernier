"""Generate the paper's numeric tables as LaTeX, straight from the result files.

`AGENTS.md` rule 2 says every figure in prose cites the file that produces it, and
`scripts/check_prose_figures.py` (D081) enforces that for the two markdown writeups by pinning
literals. A paper is worse than prose for this: a table has dozens of cells, and a `.tex` file
is the last place anyone re-checks before submitting. So the paper's tables are not written at
all. They are emitted here from `data/*.json` and `space/public/data/stats.json` and pulled in
with `\\input`, which makes drift impossible rather than detectable.

Prose figures inside `paper/vernier.tex` are a different matter and are pinned the same way the
markdown is (D086).

Every table is a `booktabs` `tabular` with no surrounding `table` environment, so the paper
controls placement, captions and labels.
"""

from __future__ import annotations

import json
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
}
_TASK_LABEL = {"hand_count": "$\\geq$1 hand", "manipulation": "active manipulation"}


def _tex_escape(s: str) -> str:
    """Underscores are subscript operators in TeX; the verdict string carries one."""
    return s.replace("_", r"\_")


def _pct(x: float) -> str:
    return f"{x * 100:.2f}"


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
        "release & figure & measured & published & diff (pp) \\\\\n\\midrule\n"
        f"{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _error_direction(d: dict[str, Any]) -> str:
    e = d["stats"]["confusion"]["error_direction"]
    rows = [
        f"hand count & {e['hand_count']['over']} & {e['hand_count']['at_risk_over']} & "
        f"{e['hand_count']['under']} & {e['hand_count']['at_risk_under']} \\\\",
        f"active manipulation & {e['manipulation']['over']} & {e['manipulation']['at_risk_over']} & "
        f"{e['manipulation']['under']} & {e['manipulation']['at_risk_under']} \\\\",
    ]
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{lrrrr}\n\\toprule\n"
        "task & over & at risk & under & at risk \\\\\n\\midrule\n"
        f"{body}\n\\bottomrule\n\\end{{tabular}}\n"
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
        "corpus & task & published & judge & PPI++ & 95\\% CI & $n_{\\text{gold}}$ \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _margins(d: dict[str, Any]) -> str:
    rows = []
    for key, comp in d["margin"]["comparisons"].items():
        other = _CORPUS_LABEL["G200-epic"] if "epic" in key else _CORPUS_LABEL["G200-ego4d"]
        for task, m in comp.items():
            inside = "yes" if m["published_inside_corrected_ci"] else "no"
            rows.append(
                f"{other} & {_TASK_LABEL[task]} & {m['published_margin_pp']:+.2f} & "
                f"{m['corrected_margin_pp']:+.2f} & "
                f"[{m['ci_pp']['lo']:+.2f}, {m['ci_pp']['hi']:+.2f}] & {inside} \\\\"
            )
    body = "\n".join(rows)
    return (
        "\\begin{tabular}{@{}llrrlc@{}}\n\\toprule\n"
        "vs. & task & published & corrected & 95\\% CI & published inside \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _design_effect(d: dict[str, Any]) -> str:
    rows = []
    for task, name in (
        ("hand_ge1", "$\\geq$1 hand"),
        ("hand_eq2", "2 hands"),
        ("active_manipulation", "active manipulation"),
    ):
        u = d["h2u"]["tasks"][task]
        s = d["h2s"]["tasks"][task]
        rows.append(f"{name} & {u['design_effect']:.2f} & {s['design_effect']:.2f} \\\\")
    body = "\n".join(rows)
    u_c = d["h2u"]["clusters"]["n_clusters"]
    s_c = d["h2s"]["clusters"]["n_clusters"]
    return (
        "\\begin{tabular}{lrr}\n\\toprule\n"
        f"figure & S10k-U ({u_c} clusters) & S10k-S ({s_c} clusters) \\\\\n"
        f"\\midrule\n{body}\n\\bottomrule\n\\end{{tabular}}\n"
    )


def _ledger(d: dict[str, Any]) -> str:
    """All eight pre-registered hypotheses with their outcome, before any result is discussed."""
    w, e5, r1, m = d["wave4"], d["e5"], d["rung1"], d["margin"]
    h2max = max(d["h2u"]["design_effect_max"], d["h2s"]["design_effect_max"])
    rows = [
        ("H8", "participant counts differ across corpora", "computable, no threshold",
         "58.2$\\times$", "reported"),
        ("H1", "all three figures reproduce within $\\pm$2\\,pp", "$\\pm$2\\,pp",
         f"{d['e2']['H1']['hand_eq2_rate']['diff_pp']:.2f}\\,pp on 2 hands", "fails"),
        ("H1b", "the two P0 prompts disagree by $\\geq$1\\,pp", "$\\geq$1\\,pp",
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
        ("H7", "calibration not measurable under the published protocol", "n/a",
         f"ECE {w['H7_calibration']['hand_count']['ece']:.3f}", "measured, degenerate"),
    ]
    body = "\n".join(f"{h} & {claim} & {thr} & {obs} & {verdict} \\\\" for h, claim, thr, obs, verdict in rows)
    em = m["comparisons"]["egocentric-10k_minus_epic-kitchens-100"]["manipulation"]
    body += (
        "\n\\midrule\n\\multicolumn{5}{l}{\\emph{Not pre-registered, reported as exploratory:}} \\\\\n"
        f"--- & gold-corrected margin vs.\\ EPIC-KITCHENS-100 & none & "
        f"{em['corrected_margin_pp']:+.2f}\\,pp & unresolved \\\\"
    )
    return (
        "\\begin{tabular}{@{}lp{0.34\\linewidth}p{0.15\\linewidth}p{0.20\\linewidth}l@{}}\n"
        "\\toprule\n"
        "id & pre-registered claim & threshold & observed & verdict \\\\\n"
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


def main() -> int:
    d = _load()
    _OUT.mkdir(parents=True, exist_ok=True)
    tables = {
        "replication": _replication(d),
        "error_direction": _error_direction(d),
        "prevalence": _prevalence(d),
        "margins": _margins(d),
        "design_effect": _design_effect(d),
        "ledger": _ledger(d),
    }
    for name, tex in tables.items():
        (_OUT / f"{name}.tex").write_text(tex)
    (_OUT / "provenance.tex").write_text(_provenance(d))
    print(f"wrote {len(tables) + 1} files to {_OUT.relative_to(_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
