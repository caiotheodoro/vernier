"""D016: verify Build AI's evaluation parquets actually contain the frames a sample's
membership refers to, with non-empty (decodable) image bytes -- not a manual eyeball, an
assertion (docs/DECISIONS.md D016, docs/WAVES.md Wave 2 acceptance).

The schema, read from the real parquet footers (`docs/UPSTREAM-FINDINGS.md` F9):

    frame_id        string        # UUID4
    image           struct<bytes: binary, path: string>
    source_dataset  string
    hand_count      int32
    active_labor    string        # "yes" / "no"

`find_missing_frames` is pure and offline-testable against a small synthetic pyarrow Table
(see `tests/test_check_eval_parquets.py`) -- it never needs the real ~5.5GB evaluation
parquets (`docs/UPSTREAM-FINDINGS.md` F5) to be exercised. Only the CLI entry point touches a
real file, and that only runs once Wave 2 draws real sample membership.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import NamedTuple

import pyarrow as pa
import pyarrow.parquet as pq


class MissingFrame(NamedTuple):
    frame_id: str
    reason: str  # "not_in_parquet" | "empty_image_bytes"


def find_missing_frames(table: pa.Table, expected_frame_ids: list[str]) -> list[MissingFrame]:
    """Every `expected_frame_ids` entry must appear in `table` with non-empty `image.bytes`.

    Absence is explicit (`CONTRACTS.md` rule 2): a frame_id missing from the parquet and a
    frame_id present with empty image bytes are two different, both-reported failure modes,
    never collapsed into one silent "not found."
    """
    if "frame_id" not in table.column_names or "image" not in table.column_names:
        raise ValueError(
            f"parquet is missing required columns frame_id/image; has {table.column_names}"
        )

    present: dict[str, bytes | None] = {}
    frame_ids = table.column("frame_id").to_pylist()
    images = table.column("image").to_pylist()
    for frame_id, image in zip(frame_ids, images, strict=True):
        image_bytes = image.get("bytes") if isinstance(image, dict) else None
        present[frame_id] = image_bytes

    missing: list[MissingFrame] = []
    for frame_id in expected_frame_ids:
        if frame_id not in present:
            missing.append(MissingFrame(frame_id, "not_in_parquet"))
        elif not present[frame_id]:
            missing.append(MissingFrame(frame_id, "empty_image_bytes"))
    return missing


def load_membership_frame_ids(membership_path: Path) -> list[str]:
    """Read a `sampling.membership`-written JSON file and return its `frame_id`s.

    Format matches `write_membership`'s output: a JSON list of `FrameRef`-shaped objects.
    """
    payload = json.loads(membership_path.read_text())
    return [row["frame_id"] for row in payload]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--parquet",
        type=str,
        required=True,
        help=(
            "path (or fsspec URI, e.g. hf://datasets/<repo>@<rev>/<file>.parquet) to an "
            "evaluation parquet -- kept as a plain str, not Path: Path() collapses a URI's "
            "'//' and breaks pyarrow's filesystem resolution for anything but a local file"
        ),
    )
    parser.add_argument(
        "--membership", type=Path, required=True, help="path to a written sample-membership JSON"
    )
    args = parser.parse_args(argv)

    table = pq.read_table(args.parquet, columns=["frame_id", "image"])
    expected = load_membership_frame_ids(args.membership)
    missing = find_missing_frames(table, expected)

    if missing:
        print(f"REFUSING: {len(missing)}/{len(expected)} frames not verifiable in {args.parquet}:")
        for m in missing[:20]:
            print(f"  {m.frame_id}: {m.reason}")
        if len(missing) > 20:
            print(f"  ... and {len(missing) - 20} more")
        return 1

    print(f"check-eval-parquets: all {len(expected)} frames present and decodable in {args.parquet}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
