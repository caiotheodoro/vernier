"""`scripts/export_hf_dataset.py` -- the Hugging Face dataset release is regenerable from the
committed `data/` artifacts, its row counts equal the source counts, its README carries only
numbers that come from a result file (`AGENTS.md` rule 2), and nothing private or image-shaped
leaks into it (`docs/ETHICS.md` section 4)."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from export_hf_dataset import export  # noqa: E402

from vernier.models import FrameRef, HumanLabel, JudgeResponse

_REPO = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def release(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, dict[str, int]]:
    out = tmp_path_factory.mktemp("hf_dataset")
    return out, export(out)


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_row_counts_equal_the_committed_sources(release: tuple[Path, dict[str, int]]) -> None:
    out, counts = release
    n_labels = sum(
        len(json.loads((_REPO / "data" / "labels" / "caio" / f"{p}.json").read_text()))
        for p in ("primary", "retest")
    )
    n_gold = sum(
        len(json.loads(p.read_text())) for p in (_REPO / "data" / "gold_judged").glob("G200-*.P0b.json")
    )
    n_stored = len(json.loads((_REPO / "data" / "rung1_stored_labels.json").read_text()))
    n_members = sum(len(json.loads(p.read_text())) for p in (_REPO / "data" / "membership").glob("*.json"))
    n_claims = len(json.loads((_REPO / "MEASUREMENT_CARD.json").read_text())["claims"])

    assert counts == {
        "human_labels": n_labels,
        "gold_judged": n_gold,
        "stored_labels": n_stored,
        "membership": n_members,
        "results": n_claims,
    }
    for config, n in counts.items():
        assert len(_jsonl(out / "data" / f"{config}.jsonl")) == n


def test_rows_round_trip_through_the_frozen_contracts(release: tuple[Path, dict[str, int]]) -> None:
    out, _ = release
    for row in _jsonl(out / "data" / "human_labels.jsonl"):
        HumanLabel.model_validate(row)
    for row in _jsonl(out / "data" / "gold_judged.jsonl"):
        row = dict(row)
        assert str(row.pop("sample", "")).startswith("G200-")
        JudgeResponse.model_validate(row)
    for row in _jsonl(out / "data" / "membership.jsonl")[:500]:
        FrameRef.model_validate(row)


def test_readme_numbers_come_from_the_result_files(release: tuple[Path, dict[str, int]]) -> None:
    out, _ = release
    readme = (out / "README.md").read_text()
    e2 = json.loads((_REPO / "data" / "e2_full_n10000.json").read_text())["H1"]
    e2k = json.loads((_REPO / "data" / "e2_100k_eval.json").read_text())["published_comparison"]
    wave4 = json.loads((_REPO / "data" / "wave4_analysis.json").read_text())

    for block in (e2, e2k):
        for key in ("hand_ge1_rate", "hand_eq2_rate", "active_manipulation_rate"):
            assert f"{100 * block[key]['observed_P0a']:.1f}" in readme
            assert f"{block[key]['diff_pp']:.2f}" in readme
    assert f"{wave4['intra_rater']['manipulation']['ac1']:.3f}" in readme
    assert f"{wave4['H4']['hand_count']['ac1_ci']['lo']:.3f}" in readme
    ppi = wave4["ppi"]["G200-ego"]["manipulation"]["ppi"]
    assert f"{100 * ppi['value']:.1f}%" in readme
    assert f"n = {wave4['n_primary']} primary" in readme


def test_readme_front_matter_lists_every_config(release: tuple[Path, dict[str, int]]) -> None:
    out, counts = release
    front = (out / "README.md").read_text().split("---")[1]
    for config in counts:
        assert f"config_name: {config}" in front
        assert f"data_files: data/{config}.jsonl" in front
        assert (out / "data" / f"{config}.jsonl").is_file()


def test_release_is_self_describing(release: tuple[Path, dict[str, int]]) -> None:
    out, _ = release
    for name in ("RUBRIC.md", "PRE-REGISTRATION.md", "CONTRACTS.md", "MEASUREMENT_CARD.json"):
        assert (out / name).is_file()
    assert (out / "results" / "wave4_analysis.json").is_file()
    assert json.loads((out / "MEASUREMENT_CARD.json").read_text()) == json.loads(
        (_REPO / "MEASUREMENT_CARD.json").read_text()
    )


def test_nothing_private_and_no_image_bytes_leak(release: tuple[Path, dict[str, int]]) -> None:
    out, _ = release
    leak = re.compile(r"docs/private|HF_TOKEN=|hf_[A-Za-z0-9]{20,}|/Users/|data:image|\"image\"\s*:")
    for path in out.rglob("*"):
        if path.is_file():
            assert not leak.search(path.read_text()), path
