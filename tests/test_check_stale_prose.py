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


def test_llms_txt_is_scanned_even_though_it_is_not_markdown(tmp_path: Path) -> None:
    # Regression guard: llms.txt carried a real "documentation only" claim, invisible to this
    # scan until a scorecard review found it by hand -- the same scope gap D064 already fixed
    # once for Makefile.
    (tmp_path / "llms.txt").write_text("Status: documentation only.\n")

    hits = find_stale_prose(tmp_path)

    assert hits == {"llms.txt": [(1, "documentation only")]}


def test_makefile_is_scanned_even_though_it_is_not_markdown(tmp_path: Path) -> None:
    (tmp_path / "Makefile").write_text("# this repository is documentation only for now\n")

    hits = find_stale_prose(tmp_path)

    assert hits == {"Makefile": [(1, "documentation only")]}


def test_gemini_2_5_flash_alone_is_not_flagged(tmp_path: Path) -> None:
    # Deliberate deviation from docs/REVIEW.md R10's literal pattern list -- see module
    # docstring: a bare model-name match would false-positive on legitimate current text.
    (tmp_path / "MODEL_CARD.md").write_text(
        "Trained on gemini-2.5-flash's own stored labels, never a live call.\n"
    )

    assert find_stale_prose(tmp_path) == {}


def test_catches_the_pre_d065_gated_access_claims(tmp_path: Path) -> None:
    """D065 granted raw-corpus access; D068 fixed the card but left five prose files still
    asserting the opposite. None of the pre-existing patterns saw them -- this is the
    regression test for that gap, not a hypothetical case."""
    (tmp_path / "AGENTS.md").write_text(
        "H2 and Result 2 remain blocked on gated corpus access.\n"
        "this account is not authorized for the raw, gated corpus\n"
        "the still-inaccessible gated raw corpus (D044)\n"
        "Nothing here is an engineering gap.\n"
    )

    hits = find_stale_prose(tmp_path)

    assert hits == {
        "AGENTS.md": [
            (1, "blocked on gated corpus"),
            (2, "not authorized for the raw"),
            (3, "still-inaccessible gated raw corpus"),
            (4, "Nothing here is an engineering gap"),
        ]
    }


def test_catches_the_pre_d072_two_items_blocked_claims(tmp_path: Path) -> None:
    """D072 measured H2 and left Result 2 as the only unmet item; six public files kept saying
    two were blocked or that the corpus draws did not exist. None of the pre-existing patterns
    saw them (the third-judge phrase hid behind a capital letter). Regression test for that gap."""
    (tmp_path / "README.md").write_text(
        "Status: results in, two items blocked on external access.\n"
        "Two items remain blocked -- see HANDOFF.\n"
        "Two hypotheses remain in what_could_not_be_checked.\n"
        "S10k-U/S10k-S are still not drawn.\n"
        "the raw corpus is inaccessible, EPIC-KITCHENS-100 needs an email\n"
        "Not testable on the published protocol.\n"
        "Three judges are not three independent opinions.\n"
    )

    hits = find_stale_prose(tmp_path)

    assert hits == {
        "README.md": [
            (1, "two items blocked"),
            (2, "Two items remain"),
            (3, "Two hypotheses remain"),
            (4, "still not drawn"),
            (5, "raw corpus is inaccessible"),
            (6, "Not testable on the published protocol"),
            (7, "Three judges are not three"),
        ]
    }
