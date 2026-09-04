"""`judge_responses_io` -- the per-call JSONL persistence both live runners now share
(docs/DECISIONS.md D069). Round-trip exactness, first-occurrence dedupe on
`(frame_id, prompt_variant)`, truncation on resume, and sane behaviour on a missing file.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from judge_responses_io import append_response, read_responses, truncate_to_lines  # noqa: E402

from vernier.models import Confidence, JudgeResponse

def _resp(uid: str, variant: str = "P0a", status: str = "ok") -> JudgeResponse:
    ok = status == "ok"
    return JudgeResponse.model_validate(
        {
            "frame_id": f"uuid-{uid}",
            "judge": "fake",
            "judge_rev": "fake-rev",
            "prompt_variant": variant,
            "hands_visible": 1 if ok else None,
            "manipulation": True if ok else None,
            "confidence": Confidence(kind="none", value=None),
            "raw": "raw",
            "status": status,
            "latency_ms": 10,
            "cost_usd": 0.0001,
        }
    )

def test_append_then_read_round_trips_exactly(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    originals = [_resp("0"), _resp("1", status="unparseable"), _resp("2", variant="P0b")]
    with path.open("w") as fh:
        for resp in originals:
            append_response(fh, resp)

    assert len(path.read_text().splitlines()) == 3
    assert read_responses(path) == originals

def test_each_line_is_a_bare_model_dump_with_no_extra_keys(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    with path.open("w") as fh:
        append_response(fh, _resp("0"))

    record = json.loads(path.read_text())
    assert set(record) == set(JudgeResponse.model_fields)

def test_read_responses_dedupes_on_frame_and_variant_keeping_the_first(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    first = _resp("0")
    second = first.model_copy(update={"hands_visible": 2, "raw": "the retried call"})
    with path.open("w") as fh:
        append_response(fh, first)
        append_response(fh, second)  # same (frame_id, prompt_variant) -- a resume re-judge
        append_response(fh, _resp("0", variant="P0b"))  # same frame, other variant: distinct

    out = read_responses(path)

    assert len(out) == 2
    assert out[0] == first  # the first occurrence wins, the retry is dropped
    assert out[1].prompt_variant == "P0b"

def test_read_responses_on_a_missing_file_is_empty(tmp_path: Path) -> None:
    assert read_responses(tmp_path / "absent.jsonl") == []

def test_truncate_to_lines_keeps_exactly_n(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    with path.open("w") as fh:
        for i in range(7):
            append_response(fh, _resp(str(i)))

    truncate_to_lines(path, 4)

    kept = read_responses(path)
    assert [r.frame_id for r in kept] == [f"uuid-{i}" for i in range(4)]
    assert path.read_text().endswith("\n")  # still a well-formed jsonl to append to

def test_truncate_to_lines_is_a_no_op_when_short_enough_or_missing(tmp_path: Path) -> None:
    path = tmp_path / "r.jsonl"
    with path.open("w") as fh:
        for i in range(3):
            append_response(fh, _resp(str(i)))
    before = path.read_text()

    truncate_to_lines(path, 3)
    assert path.read_text() == before
    truncate_to_lines(path, 10)
    assert path.read_text() == before

    truncate_to_lines(tmp_path / "absent.jsonl", 5)
    assert not (tmp_path / "absent.jsonl").exists()
