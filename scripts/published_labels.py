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

from vernier.sampling.draw import _EVAL_100K_BATCH_SIZE, synthetic_frame_id
from vernier.sampling.revisions import PINNED_REVISIONS

_EVAL_HF_REPO = "builddotai/Egocentric-10K-Evaluation"

# docs/DECISIONS.md D066: Build AI's current-product evaluation release -- a second, separate
# repo, not a file within `_EVAL_HF_REPO`.
_EVAL_HF_REPO_100K = "builddotai/Egocentric-100K-Evaluation"

_EVAL_HF_REPO_FOR_SAMPLE: dict[str, str] = {
    "E10k-ego": _EVAL_HF_REPO,
    "E10k-ego4d": _EVAL_HF_REPO,
    "E10k-epic": _EVAL_HF_REPO,
    "E100k-ego": _EVAL_HF_REPO_100K,
}

# Each root E10k-* sample draws from its own file within the one pinned evaluation-release
# repo -- confirmed live via `HfApi().list_repo_files`, same mapping `sampling/draw.py` uses.
_PARQUET_FILENAME: dict[str, str] = {
    "E10k-ego": "egocentric_10k.parquet",
    "E10k-ego4d": "ego4d.parquet",
    "E10k-epic": "epic_kitchens.parquet",
    "E100k-ego": "egocentric_100k.parquet",
}

# Real arms with no `frame_id` column (docs/UPSTREAM-FINDINGS.md F10) -- same disjoint set
# `sampling/draw.py` uses, duplicated here per this file's existing non-shared-constant pattern.
_SYNTHETIC_FRAME_ID_SAMPLES: frozenset[str] = frozenset({"E100k-ego"})


def published_labels_for_sample(
    sample: str, frame_ids: set[str] | None = None
) -> dict[str, tuple[int, bool]]:
    """Real `frame_id -> (hand_count, active_labor)` for one root evaluation-release sample's
    parquet. `frame_ids`, if given, filters the result to just those ids; omit to get every
    real label in the file.

    `E100k-ego` (D066) has no `frame_id` column -- keys are `synthetic_frame_id(image_bytes)`,
    computed via the SAME imported function `sampling/draw.py` uses to build its `FrameRef`
    pool, so the join key space matches exactly. A drifted second implementation here would
    silently join every frame to nothing, not raise -- this import is deliberate, not
    incidental, unlike this file's other constants.

    Reads the 100K-eval arm via `ParquetFile.iter_batches`, not `pq.read_table` -- the same
    real pyarrow limitation `sampling/draw.py`'s `_frames_from_eval_parquet_100k` documents
    (a dictionary-encoded `image.path` struct-child field can't be materialized in one batch
    spanning the whole file); `_EVAL_100K_BATCH_SIZE` is the same checked-safe value, imported
    rather than re-derived so the two files can never drift to different thresholds."""
    from huggingface_hub import hf_hub_download

    repo_id = _EVAL_HF_REPO_FOR_SAMPLE[sample]
    path = hf_hub_download(
        repo_id=repo_id,
        repo_type="dataset",
        revision=PINNED_REVISIONS[repo_id],
        filename=_PARQUET_FILENAME[sample],
    )
    if sample in _SYNTHETIC_FRAME_ID_SAMPLES:
        out: dict[str, tuple[int, bool]] = {}
        for batch in pq.ParquetFile(path).iter_batches(
            columns=["image", "hand_count", "active_labor"], batch_size=_EVAL_100K_BATCH_SIZE
        ):
            for image, hc, al in zip(
                batch.column("image").to_pylist(),
                batch.column("hand_count").to_pylist(),
                batch.column("active_labor").to_pylist(),
                strict=True,
            ):
                image_bytes = image.get("bytes") if isinstance(image, dict) else None
                if not image_bytes:
                    continue
                fid = synthetic_frame_id(image_bytes)
                if frame_ids is None or fid in frame_ids:
                    out[fid] = (hc, al == "yes")
        return out

    table = pq.read_table(path, columns=["frame_id", "hand_count", "active_labor"])
    out = {}
    for fid, hc, al in zip(
        table.column("frame_id").to_pylist(),
        table.column("hand_count").to_pylist(),
        table.column("active_labor").to_pylist(),
        strict=True,
    ):
        if frame_ids is None or fid in frame_ids:
            out[fid] = (hc, al == "yes")
    return out
