"""D066 Step 0a: does `Egocentric-100K-Evaluation`'s `ego4d.parquet`/`epic_kitchens.parquet`
carry the same real content as `Egocentric-10K-Evaluation`'s, or were they re-judged?

`docs/UPSTREAM-FINDINGS.md` F10 already confirms, from the vendor's own Hub commit history,
that both files "were deleted and replaced" in the 100K-eval repo -- what F10 does NOT settle is
whether the replacement is content-identical to the original. Compared by CONTENT (a multiset of
`(sha256(image_bytes), hand_count, active_labor)` per row), never by row position (order isn't
guaranteed preserved across a delete+re-upload) and never by `frame_id` (the 100K-eval schema
has none, per F10).

This determines whether re-judging `E100k-ego4d`/`E100k-epic` as new sample arms would produce
new information or just re-spend ~$8.56/arm reproducing an already-on-record result
(`docs/DECISIONS.md` D066).
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import NamedTuple

import pyarrow.parquet as pq


class ParquetComparison(NamedTuple):
    filename: str
    rows_a: int
    rows_b: int
    identical_multiset: bool
    only_in_a: int
    only_in_b: int


def _row_multiset(path: str) -> Counter[tuple[str, int, str]]:
    table = pq.read_table(path, columns=["image", "hand_count", "active_labor"])
    images = table.column("image").to_pylist()
    hand_counts = table.column("hand_count").to_pylist()
    active_labors = table.column("active_labor").to_pylist()
    rows: list[tuple[str, int, str]] = []
    for image, hand_count, active_labor in zip(images, hand_counts, active_labors, strict=True):
        image_bytes = image.get("bytes") if isinstance(image, dict) else None
        image_hash = hashlib.sha256(image_bytes or b"").hexdigest()
        rows.append((image_hash, hand_count, active_labor))
    return Counter(rows)


def compare_parquets(filename: str, path_a: str, path_b: str) -> ParquetComparison:
    multiset_a = _row_multiset(path_a)
    multiset_b = _row_multiset(path_b)
    diff_a_minus_b = multiset_a - multiset_b
    diff_b_minus_a = multiset_b - multiset_a
    return ParquetComparison(
        filename=filename,
        rows_a=sum(multiset_a.values()),
        rows_b=sum(multiset_b.values()),
        identical_multiset=(not diff_a_minus_b and not diff_b_minus_a),
        only_in_a=sum(diff_a_minus_b.values()),
        only_in_b=sum(diff_b_minus_a.values()),
    )


def main(argv: list[str] | None = None) -> int:
    import os

    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    from huggingface_hub import hf_hub_download

    from vernier.sampling.revisions import PINNED_REVISIONS

    repo_10k = "builddotai/Egocentric-10K-Evaluation"
    repo_100k = "builddotai/Egocentric-100K-Evaluation"
    rev_10k = PINNED_REVISIONS[repo_10k]
    rev_100k = PINNED_REVISIONS[repo_100k]

    results = []
    for filename in ("ego4d.parquet", "epic_kitchens.parquet"):
        path_a = hf_hub_download(repo_id=repo_10k, repo_type="dataset", revision=rev_10k, filename=filename)
        path_b = hf_hub_download(repo_id=repo_100k, repo_type="dataset", revision=rev_100k, filename=filename)
        results.append(compare_parquets(filename, path_a, path_b))

    output = {r.filename: r._asdict() for r in results}
    out_path = Path("data/eval_baseline_comparison.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
