"""Export the static Space's data (`space/SPEC.md`): `space/public/data/frames.json` (the
600-frame gold grid index) and `space/public/data/stats.json` (every number the page shows).

Reads only committed `data/*.json` files, `MEASUREMENT_CARD.json`, and `docs/PRE-REGISTRATION.md`'s
frozen headline table; never a live judge, never the network. Deterministic: running it twice
is a no-op diff (`tests/test_export_space_data.py` asserts the committed output equals a fresh
build, and that every figure equals `MEASUREMENT_CARD.json`'s / `data/wave4_analysis.json`'s --
the same rule as `tests/test_emit_card.py`, AGENTS.md rule 2).

**This script writes no image bytes** (`docs/ETHICS.md` section 4; the 24 frames the Space
ships are packed by `scripts/export_space_thumbnails.py`, D073): `frames.json` carries identifiers,
labels and one integer per frame -- `row`, the frame's offset in the datasets-server `train`
split of `builddotai/Egocentric-10K-Evaluation` -- so the Space can address a frame in the
rows API without a full scan. Image bytes never pass through here.

`row` is computed by scanning the `frame_id` column of the pinned evaluation parquets already
in the local `huggingface_hub` cache (`local_files_only=True`, never a fresh multi-GB
download; `scripts/check_eval_parquets.py` reads the same column). The datasets-server split
concatenates the three parquet files in filename order -- `ego4d.parquet` (rows 0-9999),
`egocentric_10k.parquet` (10000-19999), `epic_kitchens.parquet` (20000-29999) -- verified
live against `/rows` at every file boundary on 2026-09-04, and encoded as
`_ROWS_API_FILE_ORDER` rather than assumed. The same scan yields Build AI's stored
`gemini-2.5-flash` P0b label for each gold frame (`frames.json`'s `g`), which
`data/rung1_stored_labels.json` deliberately excludes (its 29,400 rows are disjoint from the
600 gold frames). If the parquets are not cached, `row` falls back to the membership file's
`frame_index` (verified equal to the parquet row index for every G200 frame) and `g` is null
for every frame, with a loud stderr notice -- `tests/test_export_space_data.py` then fails on
the committed file's `g` count rather than letting a degraded grid ship silently.
"""

from __future__ import annotations

import json
import math
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Literal, TypedDict

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))

from wave4_analysis import _PUBLISHED as _WAVE4_PUBLISHED  # noqa: E402

from vernier.models import FrameRef, HumanLabel, JudgeResponse, PrevalenceEstimate  # noqa: E402
from vernier.sampling.draw import _EVAL_HF_REPO, _EVAL_PARQUET_FILENAME  # noqa: E402
from vernier.sampling.revisions import PINNED_REVISIONS  # noqa: E402

Corpus = Literal["egocentric-10k", "ego4d", "epic-kitchens-100"]
Task = Literal["hand_count", "hand_eq2", "manipulation"]

_OUT_DIR = _ROOT / "space" / "public" / "data"
_CARD_PATH = _ROOT / "MEASUREMENT_CARD.json"
_WAVE4_PATH = _ROOT / "data" / "wave4_analysis.json"
_E2_PATH = _ROOT / "data" / "e2_full_n10000.json"
_E5_PATH = _ROOT / "data" / "e5_full_n2000.json"
_E2_100K_PATH = _ROOT / "data" / "e2_100k_eval.json"
_STORED_LABELS_PATH = _ROOT / "data" / "rung1_stored_labels.json"
_PRIMARY_LABELS_PATH = _ROOT / "data" / "labels" / "caio" / "primary.json"
_REVIEW_LABELS_PATH = _ROOT / "data" / "labels" / "caio" / "review.json"
_MEMBERSHIP_ROOT = _ROOT / "data" / "membership"
_GOLD_JUDGED_ROOT = _ROOT / "data" / "gold_judged"
_PREREG_PATH = _ROOT / "docs" / "PRE-REGISTRATION.md"
_DECISIONS_PATH = _ROOT / "docs" / "DECISIONS.md"
_TESTS_ROOT = _ROOT / "tests"
_TEST_RETEST_PATH = _ROOT / "data" / "judge_test_retest.json"
_THUMBS_PATH = _ROOT / "data" / "space_thumbnails.json"
_H2_PATHS = {
    "S10k-U": _ROOT / "data" / "h2_design_effect.S10k-U.json",
    "S10k-S": _ROOT / "data" / "h2_design_effect.S10k-S.json",
}

_GOLD_SAMPLES: dict[str, Corpus] = {
    "G200-ego": "egocentric-10k",
    "G200-ego4d": "ego4d",
    "G200-epic": "epic-kitchens-100",
}
_E10K_SAMPLES: dict[Corpus, str] = {
    "egocentric-10k": "E10k-ego",
    "ego4d": "E10k-ego4d",
    "epic-kitchens-100": "E10k-epic",
}
# Real `source_dataset` string values in the evaluation parquets / rows API, read live
# (2026-09-04) at the split boundaries, not assumed from the corpus names.
_ROWS_API_SOURCE: dict[Corpus, str] = {
    "egocentric-10k": "egocentric_10k",
    "ego4d": "ego4d",
    "epic-kitchens-100": "epic_kitchens",
}
_PREREG_ROW_LABEL: dict[str, Corpus] = {
    "Egocentric-10K": "egocentric-10k",
    "Ego4D": "ego4d",
    "EPIC-KITCHENS-100": "epic-kitchens-100",
}
_CORPUS_100K = "egocentric-100k"
# The 10k replication files name the same three rates under two different keys: E2 puts them
# under "H1", the 100K re-run under "published_comparison" (it was not pre-registered, D066).
_H1_BLOCKS = {"egocentric-10k": (_E2_PATH, "H1"), _CORPUS_100K: (_E2_100K_PATH, "published_comparison")}
# The rate keys the E2 runs use, mapped to this project's task names. One definition: _h1()
# and _published() both read it.
_E2_KEYS = {"hand_ge1_rate": "hand_count", "hand_eq2_rate": "hand_eq2", "active_manipulation_rate": "manipulation"}
_TASKS: tuple[Task, ...] = ("hand_count", "hand_eq2", "manipulation")
_JUDGE = "qwen3-vl"
_VARIANT = "P0b"

# datasets-server concatenates a config's parquet files in filename order when it builds
# the `train` split. Verified live 2026-09-04: /rows offset 0 -> ego4d, 10000 ->
# egocentric_10k, 20000 -> epic_kitchens, each file's first/last frame_id matching the local
# parquet exactly.
_ROWS_API_FILE_ORDER: tuple[Corpus, ...] = tuple(
    sorted(_E10K_SAMPLES, key=lambda c: _EVAL_PARQUET_FILENAME[_E10K_SAMPLES[c]])
)

_ACTIVE_LABOR_TRUE = frozenset({"yes", "true"})
_ACTIVE_LABOR_FALSE = frozenset({"no", "false"})


class ParquetIndex(TypedDict):
    """Everything the export needs from the pinned parquets: per corpus, the ordered
    `frame_id` list (position = row within that file) and Build AI's stored label per id."""

    order: list[str]
    frame_ids: dict[str, list[str]]
    stored: dict[str, dict[str, tuple[int, bool]]]


def load_parquet_index() -> ParquetIndex | None:
    """Scan the cached parquets' `frame_id`/`hand_count`/`active_labor` columns (never the
    `image` column). Returns None -- loudly -- if any file is not already in the local
    huggingface_hub cache; this script never starts a multi-GB download."""
    try:
        import pyarrow.parquet as pq
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        print(f"export_space_data: parquet scan unavailable ({exc}); using fallback", file=sys.stderr)
        return None
    frame_ids: dict[str, list[str]] = {}
    stored: dict[str, dict[str, tuple[int, bool]]] = {}
    for corpus in _ROWS_API_FILE_ORDER:
        filename = _EVAL_PARQUET_FILENAME[_E10K_SAMPLES[corpus]]
        try:
            path = hf_hub_download(
                repo_id=_EVAL_HF_REPO,
                repo_type="dataset",
                revision=PINNED_REVISIONS[_EVAL_HF_REPO],
                filename=filename,
                local_files_only=True,
            )
        except Exception as exc:  # LocalEntryNotFoundError and friends
            print(
                f"export_space_data: {filename} is not in the local HF cache ({type(exc).__name__}); "
                "row falls back to membership frame_index and stored gemini labels (g) are null",
                file=sys.stderr,
            )
            return None
        table = pq.read_table(path, columns=["frame_id", "source_dataset", "hand_count", "active_labor"])
        sources = set(table.column("source_dataset").to_pylist())
        if sources != {_ROWS_API_SOURCE[corpus]}:
            raise ValueError(f"{filename}: source_dataset values {sources} != {_ROWS_API_SOURCE[corpus]!r}")
        ids = table.column("frame_id").to_pylist()
        labels: dict[str, tuple[int, bool]] = {}
        for fid, hc, al in zip(
            ids, table.column("hand_count").to_pylist(), table.column("active_labor").to_pylist(), strict=True
        ):
            if al in _ACTIVE_LABOR_TRUE:
                active = True
            elif al in _ACTIVE_LABOR_FALSE:
                active = False
            else:
                raise ValueError(f"{filename}: unrecognized active_labor {al!r}")
            labels[fid] = (int(hc), active)
        frame_ids[corpus] = ids
        stored[corpus] = labels
    return {"order": list(_ROWS_API_FILE_ORDER), "frame_ids": frame_ids, "stored": stored}


def _load_membership(sample: str) -> list[FrameRef]:
    return [FrameRef.model_validate(r) for r in json.loads((_MEMBERSHIP_ROOT / f"{sample}.json").read_text())]


def _load_judged(sample: str) -> list[JudgeResponse]:
    return [
        JudgeResponse.model_validate(r)
        for r in json.loads((_GOLD_JUDGED_ROOT / f"{sample}.{_VARIANT}.json").read_text())
    ]


def _load_review() -> dict[str, HumanLabel]:
    """The re-read, keyed by frame. The rater's current answer where one exists -- shown on
    the page, but NOT used for any statistic: every number still comes from the pre-registered
    primary pass, because the review set was selected by disagreement and a set selected that way
    can only move agreement one direction.

    Empty between attempts, and that is the intended state rather than a missing file: D077
    discarded the first review pass (its control arm was added after the labels were written) and
    archived it to `review_first_unblinded.json`, which is deliberately not a `PassType` and so is
    never read here. The page shows the primary answer alone until the re-planned pass is
    labelled."""
    if not _REVIEW_LABELS_PATH.exists():
        return {}
    return {
        label.frame_id: label
        for label in (HumanLabel.model_validate(r) for r in json.loads(_REVIEW_LABELS_PATH.read_text()))
    }


def _load_primary() -> list[HumanLabel]:
    return [HumanLabel.model_validate(r) for r in json.loads(_PRIMARY_LABELS_PATH.read_text())]


def _load_thumbnails() -> dict[str, Any]:
    """The atlas index built by `scripts/export_space_thumbnails.py`. Committed, so this stays a
    pure-JSON read: no Pillow, no parquet, no network, and a cold HF cache changes nothing."""
    payload: dict[str, Any] = json.loads(_THUMBS_PATH.read_text())
    return payload


def _thumbnails() -> dict[str, Any]:
    index = _load_thumbnails()
    return {
        "n": index["n"],
        "corpus": index["corpus"],
        "tile": index["tile"],
        "atlas": {k: index["atlas"][k] for k in ("file", "w", "h", "cols", "rows", "n_tiles", "bytes")},
        "n_withheld_for_likeness": len(index["withheld_for_likeness"]),
        "source": index["source"],
    }


def _h1() -> dict[str, Any]:
    """Build AI's published figure against vernier's own 10,000-frame run, per task, with the
    pre-registered tolerance verdict. `tolerance_pp` is parsed out of the source key name rather
    than typed (AGENTS.md rule 2)."""
    out: dict[str, Any] = {}
    for corpus, (path, key) in _H1_BLOCKS.items():
        if not path.exists():
            continue
        block = json.loads(path.read_text())[key]
        tasks: dict[str, Any] = {}
        tolerances: set[float] = set()
        for src, task in _E2_KEYS.items():
            entry = block[src]
            verdict = next(k for k in entry if k.startswith("within_") and k.endswith("_tolerance"))
            tolerances.add(float(verdict.removeprefix("within_").removesuffix("pp_tolerance")))
            tasks[task] = {
                "published": entry["published"],
                "observed": entry["observed_P0a"],
                "diff_pp": entry["diff_pp"],
                "within_tolerance": entry[verdict],
            }
        if len(tolerances) != 1:
            raise ValueError(f"{path.name}#{key}: mixed tolerances {tolerances}")
        out[corpus] = {
            "tasks": tasks,
            "tolerance_pp": tolerances.pop(),
            "n": 10000,
            "pre_registered": key == "H1",
        }
    return out


def _h2() -> dict[str, Any]:
    """The cluster bootstrap over `worker_id` (D072). Both arms are read; they differ in cluster
    count and n, so templating one onto the other would silently invent numbers."""
    arms: dict[str, Any] = {}
    effects: list[float] = []
    for arm, path in sorted(_H2_PATHS.items()):
        if not path.exists():
            continue
        block = json.loads(path.read_text())
        tasks = {t: block["tasks"][t] for t in ("hand_ge1", "hand_eq2", "active_manipulation")}
        effects.extend(float(v["design_effect"]) for v in tasks.values())
        arms[arm] = {
            "n_ok": block["n_ok"],
            "clusters": block["clusters"],
            "tasks": tasks,
        }
    if not arms:
        return {}
    first = json.loads(next(iter(sorted(_H2_PATHS.values()))).read_text())
    lo, hi = min(effects), max(effects)
    return {
        "arms": arms,
        "threshold": first["h2_threshold"],
        "holds": bool(first["h2_holds"]),
        "cluster_by": first["cluster_by"],
        "seed": first["seed"],
        "B": first["B"],
        "design_effect_min": lo,
        "design_effect_max": hi,
        # sqrt(deff) - 1: how much narrower an iid interval is than the cluster-aware one. The
        # page states this; it does NOT widen any published interval, which would be a new
        # estimator nobody pre-registered (docs/RED-TEAM.md A13).
        "width_understatement_pct": {"lo": (lo**0.5 - 1) * 100, "hi": (hi**0.5 - 1) * 100},
    }


def _test_retest() -> dict[str, Any]:
    """The judge's agreement with itself -- the companion to the human intra-rater number."""
    block = json.loads(_TEST_RETEST_PATH.read_text())
    return {
        "n_frames": block["n_frames"],
        "repeats_per_frame": block["repeats_per_frame"],
        "judge_rev": block["judge_rev"],
        # Verbatim: this run did not pin temperature/top_p/seed, unlike D053's greedy decoding
        # elsewhere. A self-agreement of 1.0 under unpinned sampling is a stronger result than
        # under greedy decoding, and the page must not present it as the latter.
        "judge_config": block["judge_config"],
        "hand_count_self_agreement_rate": block["hand_count_self_agreement_rate"],
        "manipulation_self_agreement_rate": block["manipulation_self_agreement_rate"],
        "per_frame": block["per_frame"],
    }


def row_base(corpus: Corpus, rows_per_file: dict[str, int]) -> int:
    """Offset of `corpus`'s file within the concatenated datasets-server split."""
    base = 0
    for c in _ROWS_API_FILE_ORDER:
        if c == corpus:
            return base
        base += rows_per_file[c]
    raise KeyError(corpus)


def build_frames(index: ParquetIndex | None) -> list[dict[str, Any]]:
    """The grid index: one record per gold frame (600), sorted by corpus then row."""
    primary = {label.frame_id: label for label in _load_primary()}
    review = _load_review()
    thumbs = _load_thumbnails()["tiles"]
    if index is not None:
        rows_per_file = {c: len(ids) for c, ids in index["frame_ids"].items()}
    else:
        rows_per_file = {c: len(_load_membership(_E10K_SAMPLES[c])) for c in _E10K_SAMPLES}
    frames: list[dict[str, Any]] = []
    for sample, corpus in _GOLD_SAMPLES.items():
        judged = {r.frame_id: r for r in _load_judged(sample)}
        base = row_base(corpus, rows_per_file)
        position: dict[str, int] | None = None
        if index is not None:
            position = {fid: i for i, fid in enumerate(index["frame_ids"][corpus])}
        for ref in _load_membership(sample):
            if position is not None:
                if ref.frame_id not in position:
                    raise KeyError(f"{ref.frame_id} ({sample}) not in {corpus} parquet")
                row = base + position[ref.frame_id]
            else:
                row = base + ref.frame_index
            q = judged[ref.frame_id]
            g: dict[str, Any] | None = None
            if index is not None:
                hc, active = index["stored"][corpus][ref.frame_id]
                g = {"h": hc, "m": active}
            r: dict[str, Any] | None = None
            label = primary.get(ref.frame_id)
            if label is not None:
                r = {
                    "h": label.hands_visible,
                    "m": label.manipulation,
                    "d": label.difficulty,
                    "note": label.note or None,
                    # `edge_case` is a closed list (docs/RUBRIC.md, models.EdgeCaseTag); the
                    # model validation above already rejects anything outside it.
                    "e": list(label.edge_case),
                    "s": label.seconds_spent,
                    "at": label.labelled_at.isoformat(),
                }
                reread = review.get(ref.frame_id)
                if reread is not None:
                    r["rr"] = {
                        "h": reread.hands_visible,
                        "m": reread.manipulation,
                        "d": reread.difficulty,
                        "e": list(reread.edge_case),
                        "s": reread.seconds_spent,
                        "at": reread.labelled_at.isoformat(),
                        "changed": (reread.hands_visible, reread.manipulation)
                        != (label.hands_visible, label.manipulation),
                    }
            frames.append(
                {
                    "id": ref.frame_id,
                    "corpus": corpus,
                    "w": ref.width,
                    "h": ref.height,
                    "row": row,
                    "q": {
                        "h": q.hands_visible,
                        "m": q.manipulation,
                        "c": q.confidence.value,
                        "s": q.status,
                        # The judge's literal output. Six distinct strings across 600 calls --
                        # showing it is the cheapest way to demystify what an LLM judge emits.
                        "raw": q.raw,
                        "lat": q.latency_ms,
                        "cost": q.cost_usd,
                    },
                    "g": g,
                    "r": r,
                    # Where this frame's thumbnail sits in the atlas, or null. The null is the
                    # flag: the UI never infers "is this instant?" from the corpus name, because
                    # the rule is not "which corpus" but "which corpus AND is anyone else in
                    # shot" (docs/ETHICS.md section 4, D073).
                    "t": thumbs.get(ref.frame_id),
                }
            )
    frames.sort(key=lambda f: (str(f["corpus"]), int(f["row"])))
    return frames


def parse_prereg_published(text: str) -> dict[Corpus, dict[str, float]]:
    """`docs/PRE-REGISTRATION.md`'s frozen headline table (the only place all three corpora's
    `2 hands` figures live in this repo): `| Dataset | Frames | 0 hands | >=1 hand | 2 hands |
    Active manipulation |`."""
    out: dict[Corpus, dict[str, float]] = {}
    for line in text.splitlines():
        cells = [c.strip().strip("*").strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] not in _PREREG_ROW_LABEL:
            continue
        corpus = _PREREG_ROW_LABEL[cells[0]]
        pct = [float(c.rstrip("%")) / 100 for c in cells[2:]]
        out[corpus] = {
            "hand_count": round(pct[1], 4),
            "hand_eq2": round(pct[2], 4),
            "manipulation": round(pct[3], 4),
        }
    if set(out) != set(_PREREG_ROW_LABEL.values()):
        raise ValueError(f"PRE-REGISTRATION headline table: found rows for {sorted(out)}, expected all three corpora")
    return out


def _published() -> dict[str, dict[str, float]]:
    prereg = parse_prereg_published(_PREREG_PATH.read_text())
    # Cross-check the parsed table against the constants the analysis scripts actually used.
    for sample, corpus in _GOLD_SAMPLES.items():
        for task in ("hand_count", "manipulation"):
            if prereg[corpus][task] != _WAVE4_PUBLISHED[sample][task]:
                raise ValueError(f"published {corpus}/{task}: PRE-REGISTRATION {prereg[corpus][task]} != wave4 {_WAVE4_PUBLISHED[sample][task]}")
    e2 = json.loads(_E2_PATH.read_text())
    for key, task in _E2_KEYS.items():
        if e2["H1"][key]["published"] != prereg["egocentric-10k"][task]:
            raise ValueError(f"published egocentric-10k/{task}: PRE-REGISTRATION != e2_full_n10000.json")
    published: dict[str, dict[str, float]] = {c: dict(v) for c, v in prereg.items()}
    if _E2_100K_PATH.exists():
        e100k = json.loads(_E2_100K_PATH.read_text())
        published[_CORPUS_100K] = {
            task: float(e100k["published_comparison"][key]["published"]) for key, task in _E2_KEYS.items()
        }
    return published


def _ppi(wave4: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for by_task in wave4["ppi"].values():
        for task, estimate_dict in by_task.items():
            est = PrevalenceEstimate.model_validate(estimate_dict)
            out.setdefault(est.corpus, {})[task] = {
                "naive": est.naive.value,
                "n_judged": est.naive.n,
                "value": est.ppi.value,
                "lo": est.ppi.ci.lo,
                "hi": est.ppi.ci.hi,
                "level": est.ppi.ci.level,
                "n_gold": est.ppi.n_gold,
                "n_unlabelled": est.ppi.n_unlabelled,
                "method": est.ppi.method,
                "clustered": est.ppi.clustered,
                "why_not_clustered": est.ppi.why_not_clustered,
                "judge": est.judge,
                "prompt_variant": est.prompt_variant,
            }
    return out


def _judge_alone(frames: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Judge-only rates on the 200-frame gold sets (P0b, status ok), all three tasks -- the
    `hand_count`/`manipulation` entries must equal the PPI `naive` values (asserted in tests);
    `hand_eq2` has no PPI estimate (no pre-registered gold task), so the hero shows this alone."""
    out: dict[str, dict[str, Any]] = {}
    for corpus in _GOLD_SAMPLES.values():
        ok = [f for f in frames if f["corpus"] == corpus and f["q"]["s"] == "ok"]
        n = len(ok)
        out[corpus] = {
            "hand_count": {"rate": sum(1 for f in ok if f["q"]["h"] >= 1) / n, "n": n},
            "hand_eq2": {"rate": sum(1 for f in ok if f["q"]["h"] == 2) / n, "n": n},
            "manipulation": {"rate": sum(1 for f in ok if f["q"]["m"]) / n, "n": n},
            "judge": _JUDGE,
            "prompt_variant": _VARIANT,
            "sample": next(s for s, c in _GOLD_SAMPLES.items() if c == corpus),
        }
    if _E2_100K_PATH.exists():
        e100k = json.loads(_E2_100K_PATH.read_text())
        p0a = e100k["per_variant"]["P0a"]
        out[_CORPUS_100K] = {
            "hand_count": {"rate": p0a["hand_ge1_rate"], "n": p0a["n_ok"]},
            "hand_eq2": {"rate": p0a["hand_eq2_rate"], "n": p0a["n_ok"]},
            "manipulation": {"rate": p0a["active_manipulation_rate"], "n": p0a["n_ok"]},
            "judge": _JUDGE,
            "prompt_variant": "P0a",
            "sample": e100k["sample"],
        }
    return out


def _agreement(wave4: dict[str, Any]) -> dict[str, Any]:
    h4 = {
        task: {
            "ac1": v["ac1"],
            "lo": v["ac1_ci"]["lo"],
            "hi": v["ac1_ci"]["hi"],
            "ci_method": v["ac1_ci"]["method"],
            "kappa": v["kappa"],
            "raw": v["raw_agreement"],
            "n": wave4["n_primary"],
        }
        for task, v in wave4["H4"].items()
        if task in ("hand_count", "manipulation")
    }
    intra = {
        task: {
            "ac1": v["ac1"],
            "lo": v["ac1_ci"]["lo"],
            "hi": v["ac1_ci"]["hi"],
            "ci_method": v["ac1_ci"]["method"],
            "kappa": v["kappa"],
            "n_pairs": v["n_pairs"],
        }
        for task, v in wave4["intra_rater"].items()
    }
    h5 = wave4["H5"]
    return {
        "h4": h4,
        "intra_rater": intra,
        # D076: the separation the retest actually ran at, so the Space's "the rubric is
        # decidable" line carries what that check does and does not cover.
        "retest_separation": wave4["retest_separation"],
        "h5": {
            "egocentric-10k": {"n": h5["egocentric"]["n"], "error_rate": h5["egocentric"]["error_rate"]},
            "epic-kitchens-100": {"n": h5["epic_kitchens"]["n"], "error_rate": h5["epic_kitchens"]["error_rate"]},
            "diff_pp": h5["diff_pp"],
            "holds": h5["holds"],
        },
    }


def _confusion(frames: list[dict[str, Any]]) -> dict[str, Any]:
    """Judge rows x rater columns over the primary-labelled frames with an ok judge answer."""
    labelled = [f for f in frames if f["r"] is not None and f["q"]["s"] == "ok"]
    hands = [[0, 0, 0] for _ in range(3)]
    manipulation = [[0, 0], [0, 0]]
    for f in labelled:
        hands[f["q"]["h"]][f["r"]["h"]] += 1
        manipulation[int(f["q"]["m"])][int(f["r"]["m"])] += 1
    # D083: the direction of every judge error, derived here rather than in prose. A frame the
    # rater scored 2 cannot be over-counted and one scored 0 cannot be under-counted, so the
    # at-risk denominators are carried too; a bare count would overstate the asymmetry.
    over_hands = sum(hands[j][r] for j in range(3) for r in range(3) if j > r)
    under_hands = sum(hands[j][r] for j in range(3) for r in range(3) if j < r)
    at_risk_over_hands = sum(hands[j][r] for j in range(3) for r in range(3) if r < 2)
    at_risk_under_hands = sum(hands[j][r] for j in range(3) for r in range(3) if r > 0)
    error_direction: dict[str, Any] = {
        "hand_count": {
            "over": over_hands,
            "under": under_hands,
            "at_risk_over": at_risk_over_hands,
            "at_risk_under": at_risk_under_hands,
        },
        "manipulation": {
            "over": manipulation[1][0],
            "under": manipulation[0][1],
            "at_risk_over": manipulation[0][0] + manipulation[1][0],
            "at_risk_under": manipulation[0][1] + manipulation[1][1],
        },
    }
    error_direction["total_errors"] = (
        over_hands + under_hands + manipulation[1][0] + manipulation[0][1]
    )
    return {
        "hands": hands,
        "manipulation": manipulation,
        "n": len(labelled),
        "error_direction": error_direction,
    }


def _calibration(wave4: dict[str, Any]) -> dict[str, Any]:
    return {
        task: {"ece": v["ece"], "n": v["n"], "confidence_kind": v["confidence_kind"], "bins": v["bins"]}
        for task, v in wave4["H7_calibration"].items()
    }


def _coverage() -> dict[str, dict[str, Any]]:
    """Per-corpus label distributions from the 29,400 stored gemini-2.5-flash P0b labels
    (`data/rung1_stored_labels.json`), corpus resolved through the E10k-* membership files."""
    corpus_of: dict[str, Corpus] = {}
    for corpus, sample in _E10K_SAMPLES.items():
        for ref in _load_membership(sample):
            corpus_of[ref.frame_id] = corpus
    out: dict[str, dict[str, Any]] = {
        c: {"hands": [0, 0, 0], "manipulation": [0, 0], "n": 0, "source": "gemini-2.5-flash P0b, stored in the evaluation parquet"}
        for c in _E10K_SAMPLES
    }
    for raw in json.loads(_STORED_LABELS_PATH.read_text()):
        resp = JudgeResponse.model_validate(raw)
        if resp.status != "ok" or resp.hands_visible is None or resp.manipulation is None:
            continue
        entry = out[corpus_of[resp.frame_id]]
        entry["hands"][resp.hands_visible] += 1
        entry["manipulation"][int(resp.manipulation)] += 1
        entry["n"] += 1
    if _E2_100K_PATH.exists():
        e100k = json.loads(_E2_100K_PATH.read_text())
        p0a = e100k["per_variant"]["P0a"]
        n_ok = int(p0a["n_ok"])
        h2 = round(p0a["hand_eq2_rate"] * n_ok)
        h_ge1 = round(p0a["hand_ge1_rate"] * n_ok)
        m_yes = round(p0a["active_manipulation_rate"] * n_ok)
        out[_CORPUS_100K] = {
            "hands": [n_ok - h_ge1, h_ge1 - h2, h2],
            "manipulation": [n_ok - m_yes, m_yes],
            "n": n_ok,
            "source": "qwen3-vl P0a, live judge (D066); no stored per-frame labels are committed for this release",
        }
    return out


def _prompt_sweep(e5: dict[str, Any]) -> dict[str, Any]:
    return {
        "hand_count": e5["hand_count_rates_by_variant"],
        "manipulation": e5["manipulation_rates_by_variant"],
        "n": e5["n_frames_drawn"],
        "hand_count_spread_pp": e5["H3"]["hand_count_spread_pp"],
        "manipulation_spread_pp": e5["H3"]["manipulation_spread_pp"],
    }


def _runs(e2: dict[str, Any], e5: dict[str, Any]) -> list[dict[str, Any]]:
    runs: list[dict[str, Any]] = []
    for variant in ("P0a", "P0b"):
        v = e2["per_variant"][variant]
        runs.append(
            {
                "id": f"E2 {variant}",
                "sample": "E10k-ego",
                "corpus": "egocentric-10k",
                "n_requested": v["n_total"],
                "n_ok": v["n_ok"],
                "status_counts": v["status_counts"],
                "cost_usd": v["total_cost_usd"],
                "judge_time_ms": v["total_latency_ms"],
                "latency_ms": None,
                "notes": "D054/D055. judge_time_ms is summed per-call latency, not wall time.",
            }
        )
    if _E2_100K_PATH.exists():
        e100k = json.loads(_E2_100K_PATH.read_text())
        for variant in ("P0a", "P0b"):
            v = e100k["per_variant"][variant]
            runs.append(
                {
                    "id": f"E100k {variant}",
                    "sample": e100k["sample"],
                    "corpus": _CORPUS_100K,
                    "n_requested": v["n_total"],
                    "n_ok": v["n_ok"],
                    "status_counts": v["status_counts"],
                    "cost_usd": v["total_cost_usd"],
                    "judge_time_ms": v["total_latency_ms"],
                    "latency_ms": None,
                    "notes": "D066/D067, not pre-registered. judge_time_ms is summed per-call latency, not wall time.",
                }
            )
    n_drawn = int(e5["n_frames_drawn"])
    for task_key, variants in (("hand_count", e5["hand_count_rates_by_variant"]), ("manipulation", e5["manipulation_rates_by_variant"])):
        all_ok = int(e5[f"{task_key}_ipr_par"]["n_frames_with_all_variants_ok"])
        n_ok = all_ok if all_ok == n_drawn else None
        for variant in variants:
            runs.append(
                {
                    "id": f"E5 {variant} ({task_key})",
                    "sample": "P2k",
                    "corpus": "egocentric-10k",
                    "n_requested": n_drawn,
                    "n_ok": n_ok,
                    "status_counts": {"ok": n_ok} if n_ok is not None else None,
                    "cost_usd": None,
                    "judge_time_ms": None,
                    "latency_ms": None,
                    "notes": "D055. Per-variant cost and latency were not persisted by the sweep; only rates are committed.",
                }
            )
    for sample, corpus in _GOLD_SAMPLES.items():
        judged = _load_judged(sample)
        status_counts: dict[str, int] = {}
        for r in judged:
            status_counts[r.status] = status_counts.get(r.status, 0) + 1
        runs.append(
            {
                "id": f"Gold {sample} {_VARIANT}",
                "sample": sample,
                "corpus": corpus,
                "n_requested": len(judged),
                "n_ok": status_counts.get("ok", 0),
                "status_counts": dict(sorted(status_counts.items())),
                # math.fsum, not sum: Python 3.12+ changed float sum() to compensated summation,
                # so 3.13 locally and 3.11 in CI disagreed by one ulp here and the committed
                # snapshot could not equal a fresh build on both. fsum is exactly rounded everywhere.
                "cost_usd": math.fsum(r.cost_usd for r in judged),
                "judge_time_ms": sum(r.latency_ms for r in judged),
                "latency_ms": [r.latency_ms for r in judged],
                "notes": "D059. The judge ran on preemptible Modal capacity (D055); a call that spans a preemption is retried and its latency includes the wait.",
            }
        )
    return runs


def _health(e2: dict[str, Any], runs: list[dict[str, Any]]) -> dict[str, Any]:
    p0a = e2["per_variant"]["P0a"]
    p0b = e2["per_variant"]["P0b"]
    gold_latencies = [ms for run in runs if run["latency_ms"] is not None for ms in run["latency_ms"]]
    return {
        "e2_frames": p0a["n_total"],
        "e2_cost_both_arms_usd": p0a["total_cost_usd"] + p0b["total_cost_usd"],
        "e2_judge_time_both_arms_h": (p0a["total_latency_ms"] + p0b["total_latency_ms"]) / 3_600_000,
        "e2_arms": {
            "P0a": {"cost_usd": p0a["total_cost_usd"], "judge_time_h": p0a["total_latency_ms"] / 3_600_000},
            "P0b": {"cost_usd": p0b["total_cost_usd"], "judge_time_h": p0b["total_latency_ms"] / 3_600_000},
        },
        "gold_calls": {
            "n": len(gold_latencies),
            "p50_ms": statistics.median(gold_latencies),
            "p95_ms": statistics.quantiles(gold_latencies, n=20)[18],
            "max_ms": max(gold_latencies),
            # The array the percentiles above were computed from. Health.tsx used to plot
            # `runs.find(r => r.latency_ms)` -- the FIRST gold run's 200 points -- under a
            # caption reading n=600, so the chart and its own summary described different
            # populations. Emitting the list makes them provably the same one.
            "latency_ms": gold_latencies,
        },
    }


def _provenance() -> dict[str, dict[str, str]]:
    return {
        "published": {"claim_ref": "docs/PRE-REGISTRATION.md#headline-table", "decision": "D001"},
        "ppi": {"claim_ref": "data/wave4_analysis.json#ppi", "decision": "D059"},
        "h4": {"claim_ref": "data/wave4_analysis.json#H4", "decision": "D059"},
        "h5": {"claim_ref": "data/wave4_analysis.json#H5", "decision": "D059"},
        "intra_rater": {"claim_ref": "data/wave4_analysis.json#intra_rater", "decision": "D058"},
        "retest_separation": {"claim_ref": "data/wave4_analysis.json#retest_separation", "decision": "D076"},
        "calibration": {"claim_ref": "data/wave4_analysis.json#H7_calibration", "decision": "D060"},
        "coverage": {"claim_ref": "data/rung1_stored_labels.json", "decision": "D047"},
        "coverage_100k": {"claim_ref": "data/e2_100k_eval.json#per_variant", "decision": "D066"},
        "e2": {"claim_ref": "data/e2_full_n10000.json#H1", "decision": "D054"},
        "e100k": {"claim_ref": "data/e2_100k_eval.json#published_comparison", "decision": "D067"},
        "prompt_sweep": {"claim_ref": "data/e5_full_n2000.json#H3", "decision": "D055"},
        "gold_sets": {"claim_ref": "data/gold_judged/G200-*.P0b.json", "decision": "D059"},
        "no_worker_ids": {"claim_ref": "CONTRACTS.md#FrameRef", "decision": "D039"},
        # Was cited as D040 since the Space landed. D040 is "FrameRef.fps/codec join the
        # eval-arm null-together group" and has nothing to do with republication.
        "frames_republished": {"claim_ref": "docs/ETHICS.md#4", "decision": "D073"},
        "h1": {"claim_ref": "data/e2_full_n10000.json#H1", "decision": "D054"},
        "h2": {"claim_ref": "data/h2_design_effect.S10k-S.json", "decision": "D072"},
        "test_retest": {"claim_ref": "data/judge_test_retest.json", "decision": "D059"},
        "thumbnails": {"claim_ref": "data/space_thumbnails.json", "decision": "D073"},
    }


def _repo_counts() -> dict[str, int]:
    n_tests = 0
    # rglob, not glob: tests/{agreement,calibration,distil,estimation}/ hold 97 more tests
    # that a non-recursive scan silently dropped, so the footer under-reported for months.
    for path in sorted(_TESTS_ROOT.rglob("test_*.py")):
        n_tests += len(re.findall(r"^def test_", path.read_text(), flags=re.MULTILINE))
    n_decisions = len(re.findall(r"^## D\d+", _DECISIONS_PATH.read_text(), flags=re.MULTILINE))
    return {"n_tests": n_tests, "n_decisions": n_decisions}


def _card_rev() -> str:
    try:
        rev = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "MEASUREMENT_CARD.json"],
            cwd=_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return rev or "unknown"


def build_stats(frames: list[dict[str, Any]]) -> dict[str, Any]:
    wave4 = json.loads(_WAVE4_PATH.read_text())
    e2 = json.loads(_E2_PATH.read_text())
    e5 = json.loads(_E5_PATH.read_text())
    card = json.loads(_CARD_PATH.read_text())
    corpora: list[str] = list(_GOLD_SAMPLES.values())
    if _E2_100K_PATH.exists():
        corpora.append(_CORPUS_100K)
    runs = _runs(e2, e5)
    return {
        "generated_from": {
            "card_digest": card["content_digest"],
            "git_rev": _card_rev(),
            "judge": _JUDGE,
            "judge_rev": next(iter(_load_judged("G200-ego"))).judge_rev,
            "prompt_variant": _VARIANT,
            "dataset": _EVAL_HF_REPO,
            "dataset_rev": PINNED_REVISIONS[_EVAL_HF_REPO],
            "n_gold_frames": len(frames),
            "n_rater_labels": sum(1 for f in frames if f["r"] is not None),
        },
        "corpora": corpora,
        "rows_api": {
            "dataset": _EVAL_HF_REPO,
            "config": "default",
            "split": "train",
            "source_dataset": {c: _ROWS_API_SOURCE[c] for c in _GOLD_SAMPLES.values()},
            "file_order": list(_ROWS_API_FILE_ORDER),
        },
        "published": _published(),
        "h1": _h1(),
        "h2": _h2(),
        "test_retest": _test_retest(),
        "thumbnails": _thumbnails(),
        "ppi": _ppi(wave4),
        "judge_alone": _judge_alone(frames),
        "agreement": _agreement(wave4),
        "confusion": _confusion(frames),
        "calibration": _calibration(wave4),
        "coverage": _coverage(),
        "prompt_sweep": _prompt_sweep(e5),
        "runs": runs,
        "health": _health(e2, runs),
        "provenance": _provenance(),
        "repo": _repo_counts(),
    }


def _dump(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    index = load_parquet_index()
    frames = build_frames(index)
    stats = build_stats(frames)
    _OUT_DIR.mkdir(parents=True, exist_ok=True)
    _dump(_OUT_DIR / "frames.json", frames)
    _dump(_OUT_DIR / "stats.json", stats)
    source = "parquet scan" if index is not None else "membership frame_index FALLBACK (g is null)"
    print(f"wrote {_OUT_DIR / 'frames.json'} ({len(frames)} frames, row from {source})")
    print(f"wrote {_OUT_DIR / 'stats.json'} (corpora {stats['corpora']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
