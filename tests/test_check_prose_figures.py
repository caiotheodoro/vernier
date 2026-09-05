"""`scripts/check_prose_figures.py` -- the check AGENTS.md rule 2 has always promised (D081)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_prose_figures import (  # noqa: E402
    _PINS,
    _TRANSFORMS,
    _check_pins,
    _check_table_coverage,
    _resolve,
    main,
)

_PIN = ("doc.md", "80.8", "data/x.json", "a.b", "pct1")


def _fixture(root: Path, doc: str, value: float) -> None:
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / "data" / "x.json").write_text(json.dumps({"a": {"b": value}}))
    (root / "doc.md").write_text(doc)


def test_a_pin_that_matches_its_source_passes(tmp_path: Path) -> None:
    _fixture(tmp_path, "the rate is 80.8 percent\n", 0.808)
    errors: list[str] = []
    assert _check_pins(errors, (_PIN,), tmp_path) == 1
    assert errors == []


def test_a_source_that_moved_under_the_prose_is_caught(tmp_path: Path) -> None:
    """The D078 case: labels corrected, artifact moved, prose still quoting the old figure."""
    _fixture(tmp_path, "the rate is 80.8 percent\n", 0.855)
    errors: list[str] = []
    _check_pins(errors, (_PIN,), tmp_path)
    assert len(errors) == 1
    assert "now reads '85.5'" in errors[0]
    assert "the artifact wins" in errors[0]


def test_a_figure_dropped_from_the_prose_is_caught(tmp_path: Path) -> None:
    """A one-way check would pass here: the pin still resolves, but nobody makes the claim."""
    _fixture(tmp_path, "the rate is not stated any more\n", 0.808)
    errors: list[str] = []
    _check_pins(errors, (_PIN,), tmp_path)
    assert len(errors) == 1
    assert "no longer appears in the document" in errors[0]


def test_an_unpinned_table_cell_is_caught(tmp_path: Path) -> None:
    _fixture(tmp_path, "| figure | value |\n|---|---:|\n| rate | 80.8 |\n| other | 12.3 |\n", 0.808)
    errors: list[str] = []
    checked = _check_table_coverage(errors, (_PIN,), tmp_path)
    assert checked == 2
    assert len(errors) == 1
    assert "'12.3' is not pinned" in errors[0]


def test_table_coverage_ignores_the_separator_row(tmp_path: Path) -> None:
    _fixture(tmp_path, "| a | b |\n|---|---:|\n| rate | 80.8 |\n", 0.808)
    errors: list[str] = []
    assert _check_table_coverage(errors, (_PIN,), tmp_path) == 1
    assert errors == []


def test_bolded_cells_are_still_matched(tmp_path: Path) -> None:
    """The writeup bolds the figures it wants read first; bold must not hide a cell."""
    _fixture(tmp_path, "| a | b |\n|---|---:|\n| rate | **80.8** |\n", 0.808)
    errors: list[str] = []
    assert _check_table_coverage(errors, (_PIN,), tmp_path) == 1
    assert errors == []


def test_transforms_write_values_the_way_a_person_writes_them() -> None:
    assert _TRANSFORMS["pct1"](0.9544954495449545) == "95.4"
    assert _TRANSFORMS["pct2"](0.9642) == "96.42"
    assert _TRANSFORMS["ratio2"](1.6550195166543795) == "1.66"
    assert _TRANSFORMS["ratio3"](0.8757234236978373) == "0.876"
    assert _TRANSFORMS["int_comma"](2144) == "2,144"


def test_resolve_walks_lists_by_integer_segment(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "x.json").write_text(json.dumps({"bins": [{"n": 7}, {"n": 92}]}))
    assert _resolve("data/x.json", "bins.1.n", tmp_path) == 92


def test_the_real_pins_all_pass() -> None:
    """The production configuration, against the real committed artifacts."""
    assert main() == 0
    assert len(_PINS) > 30
