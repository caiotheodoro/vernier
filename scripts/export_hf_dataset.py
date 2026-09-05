"""Build the Hugging Face dataset release, `caiotheodoro/vernier`, from the committed `data/`
artifacts -- labels, membership, judge output, and results. No image bytes, ever
(`docs/ETHICS.md` section 4): the release is identifiers, labels, and statistics only.

Regenerable and testable: `python3 scripts/export_hf_dataset.py` writes `hf/dataset/`
(gitignored, it is derived), and `tests/test_export_hf_dataset.py` asserts row counts equal the
source counts and that every number in the generated README comes from a result file --
`AGENTS.md` rule 2 ("no transcribed numbers") applies to the dataset card the same way it
applies to `MEASUREMENT_CARD.json`.

Configs (one `.jsonl` each, listed in the README front matter so `load_dataset` finds them):

    human_labels   data/labels/caio/{primary,retest}.json      -> HumanLabel records
    gold_judged    data/gold_judged/G200-*.P0b.json            -> JudgeResponse (qwen3-vl, live)
    stored_labels  data/rung1_stored_labels.json               -> JudgeResponse (gemini, Build AI's own)
    membership     data/membership/*.json                      -> FrameRef records
    results        MEASUREMENT_CARD.json claims                -> one row per claim

Plus the raw result JSONs under `results/`, and copies of `RUBRIC.md`, `PRE-REGISTRATION.md`,
`CONTRACTS.md` and `MEASUREMENT_CARD.json` so the release is self-describing.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from vernier.models import FrameRef, HumanLabel, JudgeResponse

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA = _REPO_ROOT / "data"

_RESULT_FILES = (
    "wave4_analysis.json",
    "e2_full_n10000.json",
    "e5_full_n2000.json",
    "e2_100k_eval.json",
    "rung1_distillation.json",
    "eval_baseline_comparison.json",
    "judge_test_retest.json",
)

_DOC_COPIES = {
    "docs/RUBRIC.md": "RUBRIC.md",
    "docs/PRE-REGISTRATION.md": "PRE-REGISTRATION.md",
    "CONTRACTS.md": "CONTRACTS.md",
    "MEASUREMENT_CARD.json": "MEASUREMENT_CARD.json",
}

_REPO_URL = "https://github.com/caiotheodoro/vernier"
_SPACE_URL = "https://huggingface.co/spaces/caiotheodoro/vernier"
_MODEL_URL = "https://huggingface.co/caiotheodoro/vernier-rung1-probe"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as fh:
        for row in rows:
            fh.write(json.dumps(row) + "\n")
    return len(rows)


def _human_labels() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pass_ in ("primary", "retest"):
        for raw in json.loads((_DATA / "labels" / "caio" / f"{pass_}.json").read_text()):
            # Validate against the frozen contract, then dump with the public field name
            # (`pass`, not the Python-safe `pass_` alias) so the jsonl matches CONTRACTS.md.
            rows.append(HumanLabel.model_validate(raw).model_dump(mode="json", by_alias=True))
    return rows


def _gold_judged() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((_DATA / "gold_judged").glob("G200-*.P0b.json")):
        sample = path.name.split(".")[0]
        for raw in json.loads(path.read_text()):
            record = JudgeResponse.model_validate(raw).model_dump(mode="json")
            record["sample"] = sample  # which G200-* pool the frame came from; not a model field
            rows.append(record)
    return rows


def _stored_labels() -> list[dict[str, Any]]:
    return [
        JudgeResponse.model_validate(raw).model_dump(mode="json")
        for raw in json.loads((_DATA / "rung1_stored_labels.json").read_text())
    ]


def _membership() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted((_DATA / "membership").glob("*.json")):
        for raw in json.loads(path.read_text()):
            rows.append(FrameRef.model_validate(raw).model_dump(mode="json"))
    return rows


def _results(card: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "record_type": claim["record_type"],
            "record_ref": claim["record_ref"],
            "statement": claim["statement"],
        }
        for claim in card["claims"]
    ]


def _pct(x: float) -> str:
    return f"{100 * x:.1f}"


def _readme(card: dict[str, Any], counts: dict[str, int]) -> str:
    """The dataset card. Every figure is read from a result file here, never typed."""
    e2 = json.loads((_DATA / "e2_full_n10000.json").read_text())
    e2_100k = json.loads((_DATA / "e2_100k_eval.json").read_text())
    wave4 = json.loads((_DATA / "wave4_analysis.json").read_text())
    rung1 = json.loads((_DATA / "rung1_distillation.json").read_text())

    h1 = e2["H1"]
    h1k = e2_100k["published_comparison"]
    intra = wave4["intra_rater"]
    h4 = wave4["H4"]
    h5 = wave4["H5"]
    ppi_ego_m = wave4["ppi"]["G200-ego"]["manipulation"]
    n_primary = wave4["n_primary"]
    n_pairs = intra["manipulation"]["n_pairs"]
    ece = wave4["H7_calibration"]
    n_claims = len(card["claims"])
    n_unchecked = len(card["what_could_not_be_checked"])

    def h1_row(name: str, block: dict[str, Any], label: str) -> str:
        b = block[name]
        ok = "yes" if b["within_2pp_tolerance"] else "**no**"
        return (
            f"| {label} | {_pct(b['observed_P0a'])} | {_pct(b['published'])} | "
            f"{b['diff_pp']:.2f} | {ok} |"
        )

    return f"""---
license: apache-2.0
pretty_name: vernier
language:
  - en
task_categories:
  - image-classification
size_categories:
  - 10K<n<100K
source_datasets:
  - builddotai/Egocentric-10K-Evaluation
  - builddotai/Egocentric-100K-Evaluation
tags:
  - egocentric
  - dataset-audit
  - llm-as-judge
  - prediction-powered-inference
  - hand-detection
  - build-ai
configs:
  - config_name: human_labels
    data_files: data/human_labels.jsonl
  - config_name: gold_judged
    data_files: data/gold_judged.jsonl
  - config_name: stored_labels
    data_files: data/stored_labels.jsonl
  - config_name: membership
    data_files: data/membership.jsonl
  - config_name: results
    data_files: data/results.jsonl
---

# vernier

Error bars on a dataset vendor's quality claim. Build AI publishes hand-visibility and
active-manipulation rates for `Egocentric-10K` / `Egocentric-100K`, judged once by
`gemini-2.5-flash` with no human gold, no interval, and no test that the judge scores a factory
floor and a home kitchen on the same scale. This release is the data behind an independent,
pre-registered measurement of that claim: human labels against a written rubric, a live
open-weights judge on the same frames, Build AI's own stored labels, and every computed
result. **No image is redistributed in this dataset** -- frames are identified by `frame_id` and fetched from
the vendor's own release.

Code, protocol and decision log: [{_REPO_URL}]({_REPO_URL}). Frame-by-frame view:
[Space]({_SPACE_URL}). Distilled probe (negative result): [model]({_MODEL_URL}).
Machine-checked verdict: `MEASUREMENT_CARD.json` in this repo -- {n_claims} claims,
{n_unchecked} items that could not be checked, verdict `{card["verdict"]}`.

## What was found

Live judge: `Qwen/Qwen3-VL-8B-Instruct-FP8`, self-hosted, temperature 0, prompt `P0a`
(Build AI's own wording), N = 10,000 frames per release.

| figure | measured | published | diff (pp) | within ±2 pp |
|---|---:|---:|---:|---|
{h1_row("hand_ge1_rate", h1, "Egocentric-10K, ≥1 hand")}
{h1_row("hand_eq2_rate", h1, "Egocentric-10K, 2 hands")}
{h1_row("active_manipulation_rate", h1, "Egocentric-10K, active manipulation")}
{h1_row("hand_ge1_rate", h1k, "Egocentric-100K, ≥1 hand")}
{h1_row("hand_eq2_rate", h1k, "Egocentric-100K, 2 hands")}
{h1_row("active_manipulation_rate", h1k, "Egocentric-100K, active manipulation")}

Same judge, same gap on the same figure (2 hands) on both the superseded and the current
release. The 100K rows are a disclosed extension, not pre-registered.

Against human gold (one rater, n = {n_primary} primary labels, rubric v1.2.0):

- Rubric is decidable: intra-rater AC1 {intra["hand_count"]["ac1"]:.3f} (hand count),
  {intra["manipulation"]["ac1"]:.3f} (manipulation), n = {n_pairs} blind re-labels, gate 0.70.
- Judge–human AC1 {h4["hand_count"]["ac1"]:.3f} (hand count, 95% CI
  [{h4["hand_count"]["ac1_ci"]["lo"]:.3f}, {h4["hand_count"]["ac1_ci"]["hi"]:.3f}]),
  {h4["manipulation"]["ac1"]:.3f} (manipulation, 95% CI
  [{h4["manipulation"]["ac1_ci"]["lo"]:.3f}, {h4["manipulation"]["ac1_ci"]["hi"]:.3f}]).
- PPI++-corrected active-manipulation prevalence, Egocentric-10K:
  {_pct(ppi_ego_m["ppi"]["value"])}% (95% CI [{_pct(ppi_ego_m["ppi"]["ci"]["lo"])},
  {_pct(ppi_ego_m["ppi"]["ci"]["hi"])}]) vs published {_pct(ppi_ego_m["published"])}%;
  judge alone {_pct(ppi_ego_m["naive"]["value"])}%. Not clustered by worker (no worker id on
  these frames) -- a lower bound on the true width.
- Domain bias (H5): judge error on manipulation {_pct(h5["egocentric"]["error_rate"])}%
  (Egocentric, n = {h5["egocentric"]["n"]}) vs {_pct(h5["epic_kitchens"]["error_rate"])}%
  (EPIC-KITCHENS-100, n = {h5["epic_kitchens"]["n"]}). Underpowered by design at this n;
  reported, not concluded.
- Calibration (H7): ECE {ece["hand_count"]["ece"]:.3f} / {ece["manipulation"]["ece"]:.3f};
  greedy decoding puts ~all confidence in one bin, so this is a weak curve by construction.
- Distillation (H6): DINOv2-small linear probe, teacher fidelity
  {rung1["fidelity_vs_gemini_2_5_flash"]:.3f} vs target 0.90; the 0.80 agreement floor is
  unreachable at 95% confidence on n = {rung1["n_calibration_gold"]} calibration gold.
  Negative result, shipped as such.

Every statement above is one row of the `results` config, with the file and key it came from.

## Configs

| config | rows | one row is |
|---|---:|---|
| `human_labels` | {counts["human_labels"]} | a `HumanLabel`: `frame_id, rater, pass, rubric_rev, hands_visible, manipulation, edge_case, difficulty, note, labelled_at, seconds_spent` |
| `gold_judged` | {counts["gold_judged"]} | a `JudgeResponse` from the live judge on the three 200-frame gold pools (`sample` added) |
| `stored_labels` | {counts["stored_labels"]} | a `JudgeResponse` reconstructed from Build AI's own published `gemini-2.5-flash` labels (`P0b`) |
| `membership` | {counts["membership"]} | a `FrameRef`: which pre-registered sample each frame belongs to, with the provenance the source release does (not) ship |
| `results` | {counts["results"]} | one `MEASUREMENT_CARD.json` claim: `record_type, record_ref, statement` |

Schemas are the pydantic models in `CONTRACTS.md` (copied here). Raw result files are under
`results/`. `RUBRIC.md` is the annotation rubric the human labels follow;
`PRE-REGISTRATION.md` is the protocol, frozen before any data was drawn.

## Limitations

One rater, so no inter-rater agreement -- the blind re-label is the substitute. The rater had
read the audited prompt before writing the rubric. Human gold is n = {n_primary}, reduced from
the pre-registered 600; every interval is correspondingly wide and every negative result is
ambiguous between "no effect" and "cannot see one". No cluster-robust interval exists yet: the
evaluation release ships no worker id. All of this is in the repo's `docs/RED-TEAM.md`.

## Contributing a second rater

Re-label `G200-ego` (200 frames, ids in `membership`) against `RUBRIC.md` with the repo's
`make human-labels RATER=<you>`, and open a discussion here with the file. Inter-rater
agreement is the one number this project cannot produce alone.

## License

Apache-2.0 for labels, records and code. Source frames remain under Build AI's release terms
and are not included.
"""


def export(out_dir: Path) -> dict[str, int]:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    card = json.loads((_REPO_ROOT / "MEASUREMENT_CARD.json").read_text())
    counts = {
        "human_labels": _write_jsonl(out_dir / "data" / "human_labels.jsonl", _human_labels()),
        "gold_judged": _write_jsonl(out_dir / "data" / "gold_judged.jsonl", _gold_judged()),
        "stored_labels": _write_jsonl(out_dir / "data" / "stored_labels.jsonl", _stored_labels()),
        "membership": _write_jsonl(out_dir / "data" / "membership.jsonl", _membership()),
        "results": _write_jsonl(out_dir / "data" / "results.jsonl", _results(card)),
    }

    (out_dir / "results").mkdir()
    for name in _RESULT_FILES:
        shutil.copy(_DATA / name, out_dir / "results" / name)
    for src, dst in _DOC_COPIES.items():
        shutil.copy(_REPO_ROOT / src, out_dir / dst)

    (out_dir / "README.md").write_text(_readme(card, counts))
    return counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=_REPO_ROOT / "hf" / "dataset")
    args = parser.parse_args(argv)
    counts = export(args.out)
    print(json.dumps({"out": str(args.out), "rows": counts}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
