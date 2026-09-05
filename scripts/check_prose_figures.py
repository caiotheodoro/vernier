"""Every figure in prose must still equal the file that produces it.

`AGENTS.md` rule 2 says so, and says `make validate` should catch it. Until now nothing did:
`scripts/check_stale_prose.py` forbids stale *design* phrases, and the numbers were hand-checked
(`docs/HANDOFF.md` said "by hand" in as many words). Two defects this session came from exactly
that gap -- D076, where the writeup claimed a seven-day retest separation the labels contradict,
and D078, where corrected labels moved figures the prose still quoted.

`MEASUREMENT_CARD.json` cannot serve as the source. A `Claim` carries `statement`,
`record_type`, `record_ref` and nothing else (`src/vernier/models.py`), so every figure lives
inside an English sentence and the card's own `intervals` array is empty. Pins therefore resolve
to the `data/*.json` files the card's `record_ref` points at, which is where the numbers are
actually produced.

Two directions, both load-bearing:

- **the literal must equal the source**, or the prose has gone stale;
- **the literal must still appear in the document**, or a figure was dropped and the pin is
  silently passing on a claim nobody makes any more.

Plus a coverage check over markdown tables, because a table is where numbers are densest and an
unregistered cell is exactly where the next drift will hide.

Shaped like `scripts/check_corpus_manifest.py`: it states what the prose says, states what the
artifact says, and exits nonzero on a mismatch rather than editing either.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parent.parent

# ── transforms ──────────────────────────────────────────────────────────────────────────────
# How a stored value is written when a human writes it down.

_Transform = Callable[[Any], str]

_TRANSFORMS: dict[str, _Transform] = {
    "pct1": lambda v: f"{float(v) * 100:.1f}",
    "pct2": lambda v: f"{float(v) * 100:.2f}",
    "ratio2": lambda v: f"{float(v):.2f}",
    "ratio3": lambda v: f"{float(v):.3f}",
    "pp2": lambda v: f"{float(v):.2f}",
    "pp1": lambda v: f"{float(v):.1f}",
    "int_comma": lambda v: f"{int(v):,}",
    "usd2": lambda v: f"{float(v):.2f}",
    "raw_int": lambda v: str(int(v)),
}


def _resolve(path: str, pointer: str, root: Path = _ROOT) -> Any:
    """`data/x.json` + `a.b.0.c` -> the value. Dotted, with integer segments indexing lists."""
    node: Any = json.loads((root / path).read_text())
    for segment in pointer.split("."):
        node = node[int(segment)] if isinstance(node, list) else node[segment]
    return node


# ── pins ────────────────────────────────────────────────────────────────────────────────────
# (document, literal as written, source file, pointer, transform)
# The literal is what a reader sees. If the two ever disagree, the artifact wins and the prose
# has a bug -- which is the rule `docs/WRITEUP.md` states about itself.

_W = "docs/WRITEUP.md"
_E2 = "data/e2_full_n10000.json"
_E100K = "data/e2_100k_eval.json"
_E5 = "data/e5_full_n2000.json"
_W4 = "data/wave4_analysis.json"
_H2U = "data/h2_design_effect.S10k-U.json"
_H2S = "data/h2_design_effect.S10k-S.json"
_RUNG1 = "data/rung1_distillation.json"
_MARGIN = "data/margin_exploratory.json"
_EPIC_MANIP = "comparisons.egocentric-10k_minus_epic-kitchens-100.manipulation"
_EPIC_HAND = "comparisons.egocentric-10k_minus_epic-kitchens-100.hand_count"

_PINS: tuple[tuple[str, str, str, str, str], ...] = (
    # H1, both releases
    (_W, "95.4", _E2, "H1.hand_ge1_rate.observed_P0a", "pct1"),
    (_W, "96.4", _E2, "H1.hand_ge1_rate.published", "pct1"),
    (_W, "0.97", _E2, "H1.hand_ge1_rate.diff_pp", "pp2"),
    (_W, "82.7", _E2, "H1.hand_eq2_rate.observed_P0a", "pct1"),
    (_W, "76.3", _E2, "H1.hand_eq2_rate.published", "pct1"),
    (_W, "6.32", _E2, "H1.hand_eq2_rate.diff_pp", "pp2"),
    (_W, "91.3", _E2, "H1.active_manipulation_rate.observed_P0a", "pct1"),
    (_W, "91.7", _E2, "H1.active_manipulation_rate.published", "pct1"),
    (_W, "0.38", _E2, "H1.active_manipulation_rate.diff_pp", "pp2"),
    (_W, "96.1", _E100K, "published_comparison.hand_ge1_rate.observed_P0a", "pct1"),
    (_W, "97.0", _E100K, "published_comparison.hand_ge1_rate.published", "pct1"),
    (_W, "0.86", _E100K, "published_comparison.hand_ge1_rate.diff_pp", "pp2"),
    (_W, "85.2", _E100K, "published_comparison.hand_eq2_rate.observed_P0a", "pct1"),
    (_W, "79.0", _E100K, "published_comparison.hand_eq2_rate.published", "pct1"),
    (_W, "6.14", _E100K, "published_comparison.hand_eq2_rate.diff_pp", "pp2"),
    (_W, "92.1", _E100K, "published_comparison.active_manipulation_rate.observed_P0a", "pct1"),
    (_W, "92.8", _E100K, "published_comparison.active_manipulation_rate.published", "pct1"),
    (_W, "0.62", _E100K, "published_comparison.active_manipulation_rate.diff_pp", "pp2"),
    # PPI, the headline correction
    (_W, "80.8", _W4, "ppi.G200-ego.manipulation.ppi.value", "pct1"),
    (_W, "70.1", _W4, "ppi.G200-ego.manipulation.ppi.ci.lo", "pct1"),
    (_W, "91.6", _W4, "ppi.G200-ego.manipulation.ppi.ci.hi", "pct1"),
    (_W, "90.0", _W4, "ppi.G200-ego.manipulation.naive.value", "pct1"),
    # H2 design effect, both arms
    (_W, "1.25", _H2U, "tasks.hand_ge1.design_effect", "ratio2"),
    (_W, "1.62", _H2U, "tasks.hand_eq2.design_effect", "ratio2"),
    (_W, "1.27", _H2U, "tasks.active_manipulation.design_effect", "ratio2"),
    (_W, "1.31", _H2S, "tasks.hand_ge1.design_effect", "ratio2"),
    (_W, "1.66", _H2S, "tasks.hand_eq2.design_effect", "ratio2"),
    (_W, "1.29", _H2S, "tasks.active_manipulation.design_effect", "ratio2"),
    # agreement, the figures D078 moved
    (_W, "0.876", _W4, "intra_rater.hand_count.ac1", "ratio3"),
    (_W, "0.899", _W4, "intra_rater.manipulation.ac1", "ratio3"),
    (_W, "0.795", _W4, "H4.hand_count.ac1", "ratio3"),
    (_W, "0.687", _W4, "H4.hand_count.ac1_ci.lo", "ratio3"),
    (_W, "0.894", _W4, "H4.hand_count.ac1_ci.hi", "ratio3"),
    (_W, "0.863", _W4, "H4.manipulation.ac1", "ratio3"),
    (_W, "0.760", _W4, "H4.manipulation.ac1_ci.lo", "ratio3"),
    (_W, "0.950", _W4, "H4.manipulation.ac1_ci.hi", "ratio3"),
    # H5, H3, H6
    (_W, "9.1", _W4, "H5.egocentric.error_rate", "pct1"),
    (_W, "3.3", _W4, "H5.epic_kitchens.error_rate", "pct1"),
    (_W, "1.25", _E5, "H3.manipulation_spread_pp", "pp2"),
    (_W, "0.25", _E5, "H3.hand_count_spread_pp", "pp2"),
    (_W, "0.69", _RUNG1, "fidelity_vs_gemini_2_5_flash", "ratio2"),
    # the exploratory margin (D079)
    (_W, "6.62", _MARGIN, f"{_EPIC_MANIP}.published_margin_pp", "pp2"),
    (_W, "-4.69", _MARGIN, f"{_EPIC_MANIP}.corrected_margin_pp", "pp2"),
    (_W, "-18.00", _MARGIN, f"{_EPIC_MANIP}.ci_pp.lo", "pp2"),
    (_W, "8.63", _MARGIN, f"{_EPIC_MANIP}.ci_pp.hi", "pp2"),
    (_W, "6.05", _MARGIN, f"{_EPIC_HAND}.published_margin_pp", "pp2"),
    (_W, "6.67", _MARGIN, f"{_EPIC_HAND}.corrected_margin_pp", "pp2"),
    (_W, "42", _MARGIN, f"{_EPIC_MANIP}.approx_gold_per_arm_to_exclude_published", "raw_int"),
)


def _check_pins(
    errors: list[str],
    pins: tuple[tuple[str, str, str, str, str], ...] = _PINS,
    root: Path = _ROOT,
) -> int:
    for doc, literal, source, pointer, transform in pins:
        expected = _TRANSFORMS[transform](_resolve(source, pointer, root))
        if expected != literal:
            errors.append(
                f"{doc}: pinned {literal!r} but {source}#{pointer} now reads {expected!r} "
                f"-- the artifact wins; fix the prose"
            )
            continue
        if literal not in (root / doc).read_text():
            errors.append(
                f"{doc}: pin {literal!r} ({source}#{pointer}) no longer appears in the document "
                f"-- either the figure was dropped or the pin is stale"
            )
    return len(pins)


# ── table coverage ──────────────────────────────────────────────────────────────────────────

_NUMERIC_CELL = re.compile(r"^\*{0,2}-?\d+(?:[.,]\d+)*\*{0,2}$")
# Cells that are labels or counts rather than measured figures, with the reason each is exempt.
_COVERAGE_ALLOWLIST: dict[str, str] = {
    "10": "table label: the 10K release",
    "100": "table label: the 100K release",
}


def _numeric_cells(doc: str, root: Path = _ROOT) -> list[tuple[int, str]]:
    cells: list[tuple[int, str]] = []
    for lineno, line in enumerate((root / doc).read_text().splitlines(), start=1):
        stripped = line.strip()
        if not stripped.startswith("|") or set(stripped) <= set("|-: "):
            continue
        for cell in (c.strip() for c in stripped.strip("|").split("|")):
            if _NUMERIC_CELL.match(cell):
                cells.append((lineno, cell.strip("*")))
    return cells


def _check_table_coverage(
    errors: list[str],
    pins: tuple[tuple[str, str, str, str, str], ...] = _PINS,
    root: Path = _ROOT,
) -> int:
    pinned = {literal for _, literal, _, _, _ in pins}
    checked = 0
    for doc in sorted({pin[0] for pin in pins}):
        for lineno, cell in _numeric_cells(doc, root):
            checked += 1
            bare = cell.rstrip("%")
            if bare in pinned or bare in _COVERAGE_ALLOWLIST:
                continue
            errors.append(
                f"{doc}:{lineno}: table cell {cell!r} is not pinned to a source file. "
                f"Add it to _PINS, or to _COVERAGE_ALLOWLIST with a reason."
            )
    return checked


def main() -> int:
    errors: list[str] = []
    n_pins = _check_pins(errors)
    n_cells = _check_table_coverage(errors)
    for error in errors:
        print(error, file=sys.stderr)
    if errors:
        print(
            f"\ncheck-prose-figures: {len(errors)} problem(s) across {n_pins} pins "
            f"and {n_cells} table cells",
            file=sys.stderr,
        )
        return 1
    print(f"check-prose-figures: {n_pins} pins and {n_cells} table cells agree with their sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
