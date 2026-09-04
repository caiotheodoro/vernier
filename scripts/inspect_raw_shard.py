"""D065: a real, throwaway, read-only inspection of ONE real Egocentric-10K raw-corpus
WebDataset shard -- the first time this project has ever opened one.

`docs/DECISIONS.md` D044 found (via `HfApi().list_repo_files` metadata only, before gated
access was granted) that the raw corpus ships as `.tar` shards, not a parquet, and explicitly
flagged its own claim as unverified: "a different, still-ungated-in-this-repo dataset whose
real schema hasn't been inspected yet." Access is now granted. This script does the actual
inspection D044's own reversal clause called for, so `S10k-U`/`S10k-S`'s real adapter (still
NOT built here -- see module docstring bottom) can eventually be scoped against real facts
instead of filenames.

This is investigative, not production code: no `FrameRef` construction, no `SampleName`
wiring, no test file -- matches this repo's own convention that `scripts/` holds untested CLI
entry points while `src/vernier/` holds tested library code. A human reads the stdout once.

**What this script deliberately does NOT do**: decide or build the real `S10k-U`/`S10k-S`
adapter. One shard out of ~19,500 cannot license a corpus-wide claim; its findings go into a
`docs/DECISIONS.md` entry as real, bounded, disclosed facts, and the adapter itself is planned
separately once those facts exist.
"""

from __future__ import annotations

import io
import json
import os
import sys
import tarfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

# Must be set before the first `hf_hub_download` of a large file in this environment --
# docs/HANDOFF.md records the Xet transfer backend hanging indefinitely, twice, on real
# multi-hundred-MB downloads here; the plain HTTP path (forced by this flag) completed
# reliably with its own automatic resume-on-timeout.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

_REPO_ID_DEFAULT = "builddotai/Egocentric-10K"
_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mkv", ".avi", ".mov"}
_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def _list_candidate_shards(repo_id: str) -> tuple[list[str], str | None]:
    """Real `.tar` shard paths (sorted, deterministic) plus the repo's real resolved commit
    sha -- a candidate value for `sampling/revisions.py`'s `PINNED_REVISIONS` once a real
    adapter exists (not added there by this script)."""
    from huggingface_hub import HfApi

    api = HfApi()
    files = api.list_repo_files(repo_id, repo_type="dataset")
    shards = sorted(f for f in files if f.endswith(".tar"))
    sha = api.dataset_info(repo_id).sha
    return shards, sha


def _pick_one_shard(shards: list[str], all_files: list[str]) -> tuple[str, str | None]:
    """First shard alphabetically (deterministic, cheap -- shards are already known from
    corpus-wide totals to be roughly uniform in size, so there is no real reason to rank by
    size for a single-sample spike). Its sibling `intrinsics.json` is the one JSON file
    sharing the same worker-directory prefix."""
    shard = shards[0]
    worker_dir = str(PurePosixPath(shard).parent)
    siblings = [f for f in all_files if f.startswith(worker_dir + "/") and f.endswith(".json")]
    return shard, (siblings[0] if siblings else None)


def _download(repo_id: str, filename: str) -> str:
    from huggingface_hub import hf_hub_download

    return hf_hub_download(repo_id=repo_id, repo_type="dataset", filename=filename)


def inspect_tar(path: str) -> dict[str, Any]:
    """Real member listing, extension histogram, and a check for the WebDataset `<key>.<ext>`
    same-basename pairing convention -- reports what's real, asserts nothing."""
    with tarfile.open(path) as tf:
        members = tf.getmembers()
        names = [m.name for m in members]
        extensions = Counter(PurePosixPath(n).suffix for n in names)
        stems = Counter(PurePosixPath(n).stem for n in names)
        paired = sum(1 for count in stems.values() if count >= 2)
        return {
            "member_count": len(members),
            "extension_histogram": dict(extensions),
            "first_20_names": names[:20],
            "distinct_stems": len(stems),
            "stems_with_2plus_members": paired,
        }


def inspect_one_media_member(path: str) -> dict[str, Any]:
    """Real format/size/mode for one media member if it's a still image; just the real
    extension if it looks like a video container (no new heavy video-decode dependency for a
    one-shot spike -- the extension alone answers the video-vs-stills question)."""
    with tarfile.open(path) as tf:
        members = tf.getmembers()
        media = [
            m
            for m in members
            if PurePosixPath(m.name).suffix.lower() in (_IMAGE_EXTENSIONS | _VIDEO_EXTENSIONS)
        ]
        if not media:
            return {"found": False}
        member = media[0]
        ext = PurePosixPath(member.name).suffix.lower()
        extracted = tf.extractfile(member)
        data = extracted.read() if extracted is not None else b""
        if ext in _VIDEO_EXTENSIONS:
            return {"found": True, "name": member.name, "kind": "video", "extension": ext, "bytes": len(data)}
        from PIL import Image

        image = Image.open(io.BytesIO(data))
        return {
            "found": True,
            "name": member.name,
            "kind": "still_image",
            "extension": ext,
            "format": image.format,
            "size": image.size,
            "mode": image.mode,
        }


def inspect_companion_json(path: str) -> dict[str, Any]:
    """If a same-stem `.json` sits next to a media member (WebDataset key-pair convention),
    report its real key set -- specifically whether frame_index/timestamp/worker/clip_id are
    present, which is the crux fact for whether FrameRef's per-frame fields are recoverable."""
    with tarfile.open(path) as tf:
        members = tf.getmembers()
        by_stem: dict[str, list[str]] = {}
        for m in members:
            by_stem.setdefault(PurePosixPath(m.name).stem, []).append(m.name)
        for stem, names in by_stem.items():
            json_names = [n for n in names if n.endswith(".json")]
            media_names = [n for n in names if n not in json_names]
            if json_names and media_names:
                extracted = tf.extractfile(json_names[0])
                payload = json.loads(extracted.read()) if extracted is not None else {}
                return {"found": True, "name": json_names[0], "keys": sorted(payload.keys()) if isinstance(payload, dict) else None, "sample": payload}
        return {"found": False}


def inspect_intrinsics_json(path: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text())
    if isinstance(payload, dict):
        return {"shape": "dict", "keys": sorted(payload.keys())}
    if isinstance(payload, list):
        return {"shape": "list", "length": len(payload), "first_item_keys": sorted(payload[0].keys()) if payload and isinstance(payload[0], dict) else None}
    return {"shape": type(payload).__name__}


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-id", default=_REPO_ID_DEFAULT)
    args = parser.parse_args(argv)

    from huggingface_hub import HfApi

    all_files = HfApi().list_repo_files(args.repo_id, repo_type="dataset")
    shards, sha = _list_candidate_shards(args.repo_id)
    print(f"repo: {args.repo_id}  resolved sha: {sha}  total .tar shards: {len(shards)}")

    shard_path, intrinsics_path_in_repo = _pick_one_shard(shards, all_files)
    print(f"chosen shard: {shard_path}")
    print(f"chosen intrinsics.json: {intrinsics_path_in_repo}")

    local_shard = _download(args.repo_id, shard_path)
    print(f"downloaded shard: {local_shard} ({Path(local_shard).stat().st_size} bytes)")

    tar_report = inspect_tar(local_shard)
    media_report = inspect_one_media_member(local_shard)
    companion_report = inspect_companion_json(local_shard)

    intrinsics_report: dict[str, Any] = {"found": False}
    if intrinsics_path_in_repo:
        local_intrinsics = _download(args.repo_id, intrinsics_path_in_repo)
        intrinsics_report = {"found": True, **inspect_intrinsics_json(local_intrinsics)}

    summary = {
        "repo_id": args.repo_id,
        "resolved_sha": sha,
        "total_shards_in_repo": len(shards),
        "shard_path": shard_path,
        "shard_size_bytes": Path(local_shard).stat().st_size,
        "tar": tar_report,
        "one_media_member": media_report,
        "one_companion_json": companion_report,
        "intrinsics_json": intrinsics_report,
    }
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
