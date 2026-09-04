"""Shared helper: persist every real `JudgeResponse` a run makes, one JSON line per judge call,
so the per-frame record outlives the aggregate that summarised it (`docs/DECISIONS.md` D069).

Why this exists: D067 could not backfill a corrected `active_labor_agreement_rate` for the
already-collected `data/e2_100k_eval.json` because `scripts/e2_replication.py` and
`scripts/e5_prompt_sweep.py` discarded each `JudgeResponse` the moment its fields were folded
into a running total -- a $9/~9h run left behind nothing a later analysis could re-read.
`scripts/judge_gold_sets.py` had already been persisting `response.model_dump(mode="json")` per
frame, and `scripts/wave4_analysis.py` reads those back with `JudgeResponse.model_validate`, so
the round-trip is load-bearing and proven; this module gives the two aggregate-only runners the
same durability without changing what they compute.

Used by `scripts/e2_replication.py` and `scripts/e5_prompt_sweep.py`. Forward-only: today's
committed aggregates were produced before this existed and are not re-run to get a jsonl.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TextIO

from vernier.models import JudgeResponse


def append_response(fh: TextIO, resp: JudgeResponse) -> None:
    """Write `resp` as exactly one JSON line and flush, so a crash between calls loses at
    most the call in flight, never a buffered tail. `JudgeResponse` is frozen with
    `extra="forbid"` and only after-validators, so `model_dump(mode="json")` ->
    `model_validate` round-trips exactly; nothing is added to the dumped dict (it would be
    rejected on read), and `frame_id`/`prompt_variant` -- the identity a reader needs -- are
    already inside it."""
    fh.write(json.dumps(resp.model_dump(mode="json")) + "\n")
    fh.flush()


def read_responses(path: Path) -> list[JudgeResponse]:
    """Every response in `path`, one `model_validate` per line, deduplicated on
    `(frame_id, prompt_variant)` keeping the FIRST occurrence. A missing file reads as `[]`.

    Duplicates are expected, not a bug: `scripts/run_full_e2_e5.sh` re-invokes the same
    command with `--resume` up to 6 times on a nonzero exit, and each resume re-judges from the
    last *checkpoint* (written every N frames), not from the last line appended here -- so the
    frames between the two are legitimately judged twice. The runners truncate on resume to
    keep the file behind the checkpoint, but a reader should never depend on that having
    happened; first-occurrence-wins makes a re-read deterministic regardless.

    A line that does not parse raises rather than being skipped: a torn or hand-edited record is
    a real problem to surface, not one to paper over silently."""
    if not path.is_file():
        return []
    seen: set[tuple[str, str]] = set()
    out: list[JudgeResponse] = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        resp = JudgeResponse.model_validate(json.loads(line))
        key = (resp.frame_id, resp.prompt_variant)
        if key in seen:
            continue
        seen.add(key)
        out.append(resp)
    return out


def truncate_to_lines(path: Path, n: int) -> None:
    """Keep only the first `n` lines of `path`. No-op if the file is missing or already has
    `<= n` lines. Used on resume so the jsonl never *leads* the checkpoint it was written
    alongside: `e2_replication.py` checkpoints every N frames but appends here every frame,
    so a crash leaves up to N-1 lines past `n_processed` that the resumed loop is about to
    re-judge and re-append."""
    if not path.is_file():
        return
    lines = path.read_text().splitlines(keepends=True)
    if len(lines) <= n:
        return
    path.write_text("".join(lines[:n]))
