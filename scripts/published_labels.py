"""Shared helper: Build AI's own stored per-frame `hand_count`/`active_labor` labels, read
directly from the pinned evaluation parquets -- the real `gemini-2.5-flash` judge output behind
the published figures (`docs/UPSTREAM-FINDINGS.md` F9), verified live to reproduce them exactly
to two decimal places on all three corpora (`docs/DECISIONS.md` D040, D042). Never a live call.

Used by `scripts/e2_replication.py` (comparison against a live judge on the same frames) and
`scripts/generate_rung1_labels.py` (the real, free, zero-latency rung-1 distillation teacher,
`docs/review.md` R1).
"""

from __future__ import annotations

import pyarrow.parquet as pq

from vernier.sampling.revisions import PINNED_REVISIONS

_EVAL_HF_REPO = "builddotai/Egocentric-10K-Evaluation"

# Each root E10k-* sample draws from its own file within the one pinned evaluation-release
# repo -- confirmed live via `HfApi().list_repo_files`, same mapping `sampling/draw.py` uses.
_PARQUET_FILENAME: dict[str, str] = {
    "E10k-ego": "egocentric_10k.parquet",
    "E10k-ego4d": "ego4d.parquet",
    "E10k-epic": "epic_kitchens.parquet",
}


def published_labels_for_sample(
    sample: str, frame_ids: set[str] | None = None
) -> dict[str, tuple[int, bool]]:
    """Real `frame_id -> (hand_count, active_labor)` for one root `E10k-*` sample's evaluation
    parquet. `frame_ids`, if given, filters the result to just those ids; omit to get every
    real label in the file."""
    from huggingface_hub import hf_hub_download

    path = hf_hub_download(
        repo_id=_EVAL_HF_REPO,
        repo_type="dataset",
        revision=PINNED_REVISIONS[_EVAL_HF_REPO],
        filename=_PARQUET_FILENAME[sample],
    )
    table = pq.read_table(path, columns=["frame_id", "hand_count", "active_labor"])
    out: dict[str, tuple[int, bool]] = {}
    for fid, hc, al in zip(
        table.column("frame_id").to_pylist(),
        table.column("hand_count").to_pylist(),
        table.column("active_labor").to_pylist(),
        strict=True,
    ):
        if frame_ids is None or fid in frame_ids:
            out[fid] = (hc, al == "yes")
    return out
