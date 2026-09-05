"""Build the Space's sprite atlas of human-labelled Egocentric-10K frames.

`docs/ETHICS.md` section 4 (D073): this project republishes frames only where a human
judgment attaches to them, and only from the corpus whose owner licensed them for it. That
is exactly the Egocentric-10K frames carrying a `HumanLabel` in `data/labels/caio/primary.json`
-- Build AI's own recordings, released under Apache-2.0. Ego4D's licence restricts
redistribution to research and academic publication contexts and EPIC-KITCHENS-100 is held to
the same rule regardless, so neither corpus's frames are ever written here. That restriction is
an assertion in `_select`, not a comment: a frame from any other corpus raises.

Reads the pinned evaluation parquet from the local huggingface_hub cache and never starts a
download; with a cold cache this is a clean no-op that leaves the committed atlas and index
untouched. There is no meaningful degraded atlas -- silently shipping a smaller one would break
the counts section 4 states -- so it writes nothing rather than writing something partial.

Writes two files, both committed:
  space/public/atlas/<name>.webp    the only binary this project serves
  data/space_thumbnails.json       the index, read by scripts/export_space_data.py

Usage: python3 scripts/export_space_thumbnails.py [--exclude FRAME_ID ...] [--check]
`--exclude` is the withdrawal path section 4 promises: the frame leaves the atlas and the
omission is recorded in the index. `--check` rebuilds in memory and diffs against the committed
raster digest without writing.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any, Literal

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "src"))
sys.path.insert(0, str(_ROOT / "scripts"))

from vernier.models import FrameRef, HumanLabel  # noqa: E402
from vernier.sampling.draw import _EVAL_HF_REPO, _EVAL_PARQUET_FILENAME  # noqa: E402
from vernier.sampling.revisions import PINNED_REVISIONS  # noqa: E402

# The one corpus whose frames may be written here. Build AI's own recordings, Apache-2.0.
_CORPUS: Literal["egocentric-10k"] = "egocentric-10k"
_SAMPLE = "G200-ego"
_E10K_SAMPLE = "E10k-ego"
_SOURCE_DATASET = "egocentric_10k"

_PRIMARY_LABELS_PATH = _ROOT / "data" / "labels" / "caio" / "primary.json"
_MEMBERSHIP_ROOT = _ROOT / "data" / "membership"
_INDEX_PATH = _ROOT / "data" / "space_thumbnails.json"
_ATLAS_DIR = _ROOT / "space" / "public" / "atlas"
_ATLAS_NAME = "e10k-256.webp"

_TILE_W = 256
_QUALITY = 82
_METHOD = 6
# Blank cells are painted this, and a test decodes the committed atlas and asserts every blank
# cell equals it -- the only check that can show no extra frame is hiding in the padding.
_BACKGROUND = (248, 248, 247)  # --color-bg-subtle


# Frames withheld because a person other than the camera wearer is visible in them.
#
# `docs/ETHICS.md` section 4's likeness argument is independent of the licence: Apache-2.0 is
# Build AI's grant to make, not a recorded worker's consent, and section 2 records that the
# consent instrument is not published and so is not knowable. Three of these frames carry a
# clearly identifiable face; the rest show a bystander's body or a distant figure. The rule
# applied is the conservative one -- any person other than the wearer, identifiable or not.
#
# This list is a MANUAL VISUAL REVIEW of all 33 candidate tiles (2026-09-04), not a mechanical
# test, and no test can confirm it. The rater's `other-person` edge-case tag is NOT a substitute:
# it marks frames where a third party affects the hand count, and it catches only one of the nine
# below -- not `d8876fdb`, which carries the most identifiable face in the set. If the gold sample
# is ever redrawn, this review must be redone by eye before the atlas ships.
_PRIVACY_EXCLUDED: dict[str, str] = {
    "0291c4da-e558-48d8-a23e-e465827e8eec": "identifiable face, worker looking toward the camera",
    "0fc24c81-ec3f-4dbf-a990-e8e6bc444877": "a second worker at the conveyor, mid-frame",
    "1c696b5a-795b-4cb3-a9e5-2c0f4753bedb": "figures at the top edge of the walkway",
    "1d24c2f6-d16b-4fa0-9e29-c2007d3616d2": "a bystander's arm and torso, right of frame",
    "4266c389-9ba4-43af-a292-e8595f83f7c3": "a second worker's head, lower right",
    "66f3d326-664c-4f1a-9c31-5e3ff61106af": "a bystander at the right edge",
    "715f008d-46ea-429d-9a07-13f2858ebc88": "two bystanders, one identifiable face (rater tagged other-person)",
    "7801bb78-b711-4859-bf14-eb725fbda0cd": "a second worker's head, lower centre",
    "d8876fdb-eb0a-4ae3-8fce-55f5771969be": "identifiable face, close and unobstructed",
}


# The frames a human has actually looked at for the likeness rule above.
#
# `docs/ETHICS.md` section 4 says the review "must be redone by eye" if the gold sample is ever
# redrawn, and D085 redrew it: 60 primary labels were added after the first atlas shipped, 30 of
# them on this corpus. Without this list `_select` would have republished all 30 on the next
# build, because "labelled" was standing in for "reviewed" and those were the same set exactly
# once. They are not the same set any more. A frame reaches the atlas only if it appears here.
#
# Reviewed 2026-09-04, the 33 candidates that existed then. Growing this list is a human act.
_LIKENESS_REVIEWED: frozenset[str] = frozenset({
    "0291c4da-e558-48d8-a23e-e465827e8eec",
    "0fc24c81-ec3f-4dbf-a990-e8e6bc444877",
    "1655745b-a95d-4cd7-b523-ecb0d0668e8a",
    "1c696b5a-795b-4cb3-a9e5-2c0f4753bedb",
    "1d24c2f6-d16b-4fa0-9e29-c2007d3616d2",
    "236865e2-2da9-47ed-9abd-0bec01120832",
    "36ff84fb-27c9-41ed-9303-e4025d6b133b",
    "3b24f0ea-6ee3-4615-981f-9ce7df13d4b1",
    "4266c389-9ba4-43af-a292-e8595f83f7c3",
    "43561fa5-f907-41aa-a2cd-537f59e12c55",
    "5985bb92-b342-4272-8583-5274c744d1a7",
    "66f3d326-664c-4f1a-9c31-5e3ff61106af",
    "6fe7ffba-fc88-4793-8f44-8221fd4ee0ef",
    "715f008d-46ea-429d-9a07-13f2858ebc88",
    "7801bb78-b711-4859-bf14-eb725fbda0cd",
    "782c1345-7ce8-4a53-99a6-be388a424729",
    "7d9f3379-4d7c-4189-9716-b637dd3469f6",
    "8e715a4b-5942-4cdd-add8-7edad86c0a85",
    "923b77b6-4bed-42e4-aa98-9335717a4985",
    "9858d9a8-cf39-4b3a-a8c4-059abbdc9d40",
    "98b95d40-29ff-4e33-aa90-8516a5422c86",
    "beaffe6e-6547-47e3-8e1c-f037c3fddadb",
    "c7afbcf2-cac2-4efc-b7c9-11695ca2dc04",
    "c9da980c-f545-4285-a63d-302b4958c590",
    "d28e2e28-53d0-4e0a-a6b1-40c777b14949",
    "d2d272e7-1aeb-43fa-9b6a-ddb3e7b15cae",
    "d5ba6fcf-6500-422c-b535-5e97837bab07",
    "d7e64dad-7436-4177-b5d9-1e890f5c697a",
    "d8876fdb-eb0a-4ae3-8fce-55f5771969be",
    "ebb3db47-db29-4680-b13c-20d9d40dc3bb",
    "f54e2f11-f304-4e00-8821-2493e067fc05",
    "f5d5c09d-4053-47e1-8955-2459fb3c784d",
    "ff727f46-3eb4-456e-a6e0-b111705b5829",
})

def _load_primary() -> list[HumanLabel]:
    return [HumanLabel.model_validate(r) for r in json.loads(_PRIMARY_LABELS_PATH.read_text())]


def _load_membership(sample: str) -> list[FrameRef]:
    return [FrameRef.model_validate(r) for r in json.loads((_MEMBERSHIP_ROOT / f"{sample}.json").read_text())]


def _select(exclude: frozenset[str]) -> list[str]:
    """The frame ids that may be shipped: Egocentric-10K gold frames carrying a human label."""
    gold = {ref.frame_id: ref for ref in _load_membership(_SAMPLE)}
    for ref in gold.values():
        if ref.corpus != _CORPUS:
            raise ValueError(
                f"{_SAMPLE} membership carries a {ref.corpus!r} frame ({ref.frame_id}); "
                f"only {_CORPUS!r} frames may reach the atlas (docs/ETHICS.md#4, D073)"
            )
    unknown = set(_PRIVACY_EXCLUDED) - set(gold)
    if unknown:
        raise ValueError(
            f"_PRIVACY_EXCLUDED names {len(unknown)} frame(s) not in {_SAMPLE}, e.g. {sorted(unknown)[:2]}; "
            "the manual review is stale -- redo it against the current sample before shipping"
        )
    labelled = {label.frame_id for label in _load_primary()}
    withheld = set(_PRIVACY_EXCLUDED) | exclude
    awaiting = sorted(fid for fid in gold if fid in labelled and fid not in _LIKENESS_REVIEWED)
    if awaiting:
        print(
            f"export_space_thumbnails: {len(awaiting)} labelled frame(s) have not had the "
            "likeness review and are NOT in the atlas; docs/ETHICS.md section 4 requires that "
            "review by eye before any of them ships",
            file=sys.stderr,
        )
    return sorted(
        fid
        for fid in gold
        if fid in labelled and fid in _LIKENESS_REVIEWED and fid not in withheld
    )


def _parquet_path() -> Path | None:
    try:
        from huggingface_hub import hf_hub_download
    except ImportError as exc:
        print(f"export_space_thumbnails: huggingface_hub unavailable ({exc})", file=sys.stderr)
        return None
    filename = _EVAL_PARQUET_FILENAME[_E10K_SAMPLE]
    try:
        return Path(
            hf_hub_download(
                repo_id=_EVAL_HF_REPO,
                repo_type="dataset",
                revision=PINNED_REVISIONS[_EVAL_HF_REPO],
                filename=filename,
                local_files_only=True,
            )
        )
    except Exception as exc:  # LocalEntryNotFoundError and friends
        print(
            f"export_space_thumbnails: {filename} is not in the local HF cache "
            f"({type(exc).__name__}); the committed atlas and data/space_thumbnails.json are "
            "left untouched. Re-run where the pinned evaluation parquets are cached, or "
            "`make check-eval-parquets` to populate them.",
            file=sys.stderr,
        )
        return None


def _read_frames(path: Path, wanted: list[str]) -> dict[str, bytes]:
    """Pull just these frames' JPEG bytes, one row group at a time."""
    import pyarrow.parquet as pq

    want = set(wanted)
    out: dict[str, bytes] = {}
    pf = pq.ParquetFile(path)
    for rg in range(pf.metadata.num_row_groups):
        table = pf.read_row_group(rg, columns=["frame_id", "source_dataset", "image"])
        sources = set(table.column("source_dataset").to_pylist())
        if sources != {_SOURCE_DATASET}:
            raise ValueError(f"{path.name} row group {rg}: source_dataset {sources} != {_SOURCE_DATASET!r}")
        ids = table.column("frame_id").to_pylist()
        for i, fid in enumerate(ids):
            if fid in want and fid not in out:
                cell = table.column("image")[i].as_py()
                out[fid] = bytes(cell["bytes"])
        if len(out) == len(want):
            break
    missing = want - set(out)
    if missing:
        raise ValueError(f"{path.name}: {len(missing)} selected frames not found, e.g. {sorted(missing)[:3]}")
    return out


def _grid(n: int) -> tuple[int, int]:
    """Squarest cols x rows that holds n tiles."""
    cols = 1
    while cols * cols < n:
        cols += 1
    rows = (n + cols - 1) // cols
    return cols, rows


def build(exclude: frozenset[str]) -> dict[str, Any] | None:
    import PIL
    from PIL import Image, features

    path = _parquet_path()
    if path is None:
        return None
    ids = _select(exclude)
    raw = _read_frames(path, ids)

    sizes = {Image.open(io.BytesIO(raw[fid])).size for fid in ids}
    if len(sizes) != 1:
        raise ValueError(
            f"the {len(ids)} selected frames carry {len(sizes)} distinct pixel sizes {sorted(sizes)}; "
            "the uniform-grid packing below assumes one. Emit one atlas per geometry instead."
        )
    src_w, src_h = sizes.pop()
    tile_h = round(_TILE_W * src_h / src_w)

    cols, rows = _grid(len(ids))
    atlas = Image.new("RGB", (cols * _TILE_W, rows * tile_h), _BACKGROUND)
    tiles: dict[str, dict[str, int]] = {}
    for i, fid in enumerate(ids):
        col, row = i % cols, i // cols
        x, y = col * _TILE_W, row * tile_h
        frame = Image.open(io.BytesIO(raw[fid])).convert("RGB")
        atlas.paste(frame.resize((_TILE_W, tile_h), Image.Resampling.LANCZOS), (x, y))
        tiles[fid] = {"x": x, "y": y, "w": _TILE_W, "h": tile_h}

    raster = hashlib.sha256(atlas.tobytes()).hexdigest()
    buf = io.BytesIO()
    atlas.save(buf, "WEBP", quality=_QUALITY, method=_METHOD)
    blob = buf.getvalue()

    return {
        "atlas": {
            "file": f"atlas/{_ATLAS_NAME}",
            "cols": cols,
            "rows": rows,
            "w": cols * _TILE_W,
            "h": rows * tile_h,
            "n_tiles": len(ids),
            "n_blank": cols * rows - len(ids),
            "background": list(_BACKGROUND),
            "bytes": len(blob),
            "file_sha256": hashlib.sha256(blob).hexdigest(),
            "raster_sha256": raster,
        },
        "corpus": _CORPUS,
        "n": len(ids),
        "tile": {"w": _TILE_W, "h": tile_h},
        "tiles": tiles,
        "excluded_on_request": sorted(exclude),
        "withheld_for_likeness": dict(sorted(_PRIVACY_EXCLUDED.items())),
        "source": {
            "dataset": _EVAL_HF_REPO,
            "revision": PINNED_REVISIONS[_EVAL_HF_REPO],
            "license": "apache-2.0",
            "source_dataset": _SOURCE_DATASET,
        },
        "built_with": {
            "pillow": PIL.__version__,
            "webp": features.version("webp") or "unknown",
            "resample": "LANCZOS",
            "quality": _QUALITY,
            "method": _METHOD,
        },
        "_blob": blob,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exclude", action="append", default=[], metavar="FRAME_ID")
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff, write nothing")
    args = ap.parse_args(argv)

    built = build(frozenset(args.exclude))
    if built is None:
        return 0
    blob: bytes = built.pop("_blob")

    if args.check:
        if not _INDEX_PATH.exists():
            print("export_space_thumbnails: no committed index to check against", file=sys.stderr)
            return 1
        committed = json.loads(_INDEX_PATH.read_text())
        same = committed.get("atlas", {}).get("raster_sha256") == built["atlas"]["raster_sha256"]
        print(f"raster {'matches' if same else 'DIFFERS FROM'} the committed index")
        return 0 if same else 1

    _ATLAS_DIR.mkdir(parents=True, exist_ok=True)
    (_ATLAS_DIR / _ATLAS_NAME).write_bytes(blob)
    _INDEX_PATH.write_text(json.dumps(built, indent=1, sort_keys=True) + "\n")
    a = built["atlas"]
    print(
        f"export_space_thumbnails: {built['n']} {_CORPUS} frames -> "
        f"{a['w']}x{a['h']} ({a['cols']}x{a['rows']}, {a['n_blank']} blank), "
        f"{a['bytes'] / 1024:.0f} KB -> space/public/atlas/{_ATLAS_NAME}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
