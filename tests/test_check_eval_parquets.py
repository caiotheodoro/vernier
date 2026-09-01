from __future__ import annotations

import json
import sys
from pathlib import Path

import pyarrow as pa
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_eval_parquets  # noqa: E402
from check_eval_parquets import find_missing_frames, load_membership_frame_ids  # noqa: E402


def _table(rows: list[dict[str, object]]) -> pa.Table:
    return pa.Table.from_pylist(rows)


def test_all_frames_present_and_decodable() -> None:
    table = _table(
        [
            {"frame_id": "a", "image": {"bytes": b"\x89PNG", "path": "a.png"}},
            {"frame_id": "b", "image": {"bytes": b"\x89PNG", "path": "b.png"}},
        ]
    )
    assert find_missing_frames(table, ["a", "b"]) == []


def test_frame_not_in_parquet_reported() -> None:
    table = _table([{"frame_id": "a", "image": {"bytes": b"\x89PNG", "path": "a.png"}}])
    missing = find_missing_frames(table, ["a", "c"])
    assert len(missing) == 1
    assert missing[0].frame_id == "c"
    assert missing[0].reason == "not_in_parquet"


def test_empty_image_bytes_reported_distinctly_from_missing() -> None:
    table = _table(
        [
            {"frame_id": "a", "image": {"bytes": b"", "path": "a.png"}},
            {"frame_id": "b", "image": {"bytes": None, "path": "b.png"}},
        ]
    )
    missing = find_missing_frames(table, ["a", "b"])
    assert {m.frame_id: m.reason for m in missing} == {
        "a": "empty_image_bytes",
        "b": "empty_image_bytes",
    }


def test_missing_and_empty_are_both_reported_never_collapsed() -> None:
    table = _table([{"frame_id": "a", "image": {"bytes": b"", "path": "a.png"}}])
    missing = find_missing_frames(table, ["a", "z"])
    assert {m.frame_id: m.reason for m in missing} == {
        "a": "empty_image_bytes",
        "z": "not_in_parquet",
    }


def test_missing_required_columns_raises() -> None:
    table = _table([{"frame_id": "a", "hand_count": 1}])
    with pytest.raises(ValueError, match="frame_id/image"):
        find_missing_frames(table, ["a"])


def test_load_membership_frame_ids(tmp_path: Path) -> None:
    membership_path = tmp_path / "membership.json"
    membership_path.write_text(
        json.dumps([{"frame_id": "a", "sample": "G200-ego"}, {"frame_id": "b", "sample": "G200-ego"}])
    )
    assert load_membership_frame_ids(membership_path) == ["a", "b"]


def test_cli_passes_a_remote_uri_through_unmangled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Regression test: --parquet was originally `type=Path`, which collapses a URI's "//" --
    # `Path("hf://a/b")` stringifies back to "hf:/a/b", a single slash, which pyarrow's
    # filesystem resolver then rejects outright. Caught only by actually running the CLI
    # against a real `hf://` URI (see docs/DECISIONS.md, Wave 2 prep) -- this fixture data
    # never exercised the CLI's own argument parsing, only the pure functions it calls.
    uri = "hf://datasets/builddotai/Egocentric-10K-Evaluation@deadbeef/egocentric_10k.parquet"
    seen: dict[str, object] = {}

    def fake_read_table(source: object, columns: list[str]) -> pa.Table:
        seen["source"] = source
        return _table([{"frame_id": "a", "image": {"bytes": b"\x89PNG", "path": "a.png"}}])

    monkeypatch.setattr(check_eval_parquets.pq, "read_table", fake_read_table)  # type: ignore[attr-defined]

    membership_path = tmp_path / "membership.json"
    membership_path.write_text(json.dumps([{"frame_id": "a"}]))

    exit_code = check_eval_parquets.main(["--parquet", uri, "--membership", str(membership_path)])

    assert exit_code == 0
    assert seen["source"] == uri  # exact string, not a Path-mangled "hf:/..."
