"""Behavioural tests for `scripts/check_stale_prose.py`.

`find_stale_prose` is pure and offline-testable against a synthetic directory tree
(`tmp_path`) -- the real, live scan of this repo's own `.md` files is exercised by `make
validate` (`Makefile`), not duplicated here.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_stale_prose import find_stale_prose  # noqa: E402


def test_finds_a_stale_pattern_in_a_live_file(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("This runs a three-judge panel today.\n")

    hits = find_stale_prose(tmp_path)

    assert hits == {"README.md": [(1, "three-judge panel")]}


def test_clean_file_produces_no_hits(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("This runs a single self-hosted judge.\n")

    assert find_stale_prose(tmp_path) == {}


def test_exempt_files_are_skipped(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "DECISIONS.md").write_text("D001: was documentation only, then wasn't.\n")

    assert find_stale_prose(tmp_path) == {}


def test_private_and_upstream_dirs_are_skipped(tmp_path: Path) -> None:
    private = tmp_path / "docs" / "private"
    private.mkdir(parents=True)
    (private / "notes.md").write_text("three judges, documentation only\n")

    upstream = tmp_path / "docs" / "upstream"
    upstream.mkdir(parents=True)
    (upstream / "snapshot.md").write_text("three judges, documentation only\n")

    assert find_stale_prose(tmp_path) == {}


def test_reports_multiple_hits_in_one_file_with_correct_line_numbers(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text(
        "line one is fine\ndocumentation only\nline three is fine\nJUDGES=gemini here\n"
    )

    hits = find_stale_prose(tmp_path)

    assert hits == {
        "AGENTS.md": [(2, "documentation only"), (4, "JUDGES=gemini")]
    }


def test_gemini_2_5_flash_alone_is_not_flagged(tmp_path: Path) -> None:
    # Deliberate deviation from docs/REVIEW.md R10's literal pattern list -- see module
    # docstring: a bare model-name match would false-positive on legitimate current text.
    (tmp_path / "MODEL_CARD.md").write_text(
        "Trained on gemini-2.5-flash's own stored labels, never a live call.\n"
    )

    assert find_stale_prose(tmp_path) == {}
