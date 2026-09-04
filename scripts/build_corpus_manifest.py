"""Builds the raw Egocentric-10K corpus's clip manifest -- the sampling frame `S10k-U` and
`S10k-S` are drawn from, and the source of `_factory_worker_hours`.

`docs/DECISIONS.md` D065 established that the raw corpus is 19,495 WebDataset `.tar` shards of
h265 video, that each clip's `.json` sidecar carries `factory_id`/`worker_id`/`duration_sec`/
`fps`, and that no per-frame `timestamp_s` or `frame_index` exists anywhere. It left the
adapter's scope explicitly unsized, on the grounds that one shard cannot license a corpus-wide
claim.

**This script never downloads a shard.** A `.tar` member header is 512 bytes at a computable
offset, so the whole manifest -- every clip's provenance and the exact byte window of its mp4
-- is reachable with a few small HTTP range requests per shard. The corpus is ~16 TB; the scan
that indexes it moves ~150 MB. That is what makes `S10k-U`/`S10k-S` affordable at all, and it
is why this is a separate artifact rather than something the draw recomputes.

The two functions the tests cover (`walk_tar_members`, `clip_records_from_shard`) are pure:
they take a `read_range(start, end)` callable, so a synthetic tar exercises them offline.
Everything network-facing is below them. Consuming the manifest -- pools, worker-hours, frame
extraction -- is `vernier.sampling.corpus_frames`, not this script.

Output is JSONL, appended per shard and resumable, following D069's pattern for the same
reason: a multi-hour run that loses everything on interruption gets re-spent, and this one
cannot be cheaply re-spent from a laptop.

Usage:
    python3 scripts/build_corpus_manifest.py --out data/corpus_manifest_10k.jsonl --limit 0
    python3 scripts/build_corpus_manifest.py --limit 20      # smoke, the repo's own discipline
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterator

# Set before any `huggingface_hub` import that might download: `docs/HANDOFF.md` records the
# Xet transfer backend hanging indefinitely at a fixed byte count, twice, reproducibly, in this
# environment. This script uses plain ranged GETs against the resolved CDN URL and never calls
# `hf_hub_download`, but the flag costs nothing and removes the trap for anyone who adds one.
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")

REPO_ID = "builddotai/Egocentric-10K"

_BLOCK = 512
_TAR_NAME = slice(0, 100)
_TAR_SIZE = slice(124, 136)
_TAR_TYPEFLAG = 156
_TAR_PREFIX = slice(345, 500)
# Regular-file typeflags. Everything else (directories, GNU long-name extensions, symlinks) is
# skipped rather than guessed at -- the real corpus uses none of them, and silently
# mis-parsing one would produce a byte offset that decodes to garbage.
_REGULAR = {b"0", b"\x00"}
# A sidecar is a few hundred bytes; anything larger under `.json` is not a per-clip record.
_MAX_SIDECAR_BYTES = 10_000

ReadRange = Callable[[int, int], bytes]


# --------------------------------------------------------------------------------------
# Pure: tar walking and record building
# --------------------------------------------------------------------------------------


def _round_up_block(size: int) -> int:
    return ((size + _BLOCK - 1) // _BLOCK) * _BLOCK


def walk_tar_members(read_range: ReadRange) -> Iterator[tuple[str, int, int]]:
    """Yield `(name, data_offset, size)` for every regular file in a tar, reading only its
    512-byte headers.

    Stops at the first all-zero header (tar's end-of-archive marker) or at a short read, so a
    truncated or range-capped stream terminates cleanly instead of raising.
    """
    offset = 0
    while True:
        header = read_range(offset, offset + _BLOCK - 1)
        if len(header) < _BLOCK or not header.strip(b"\0"):
            return
        raw_size = header[_TAR_SIZE].rstrip(b"\0 ").strip()
        try:
            size = int(raw_size, 8) if raw_size else 0
        except ValueError:
            return
        data_offset = offset + _BLOCK
        if bytes(header[_TAR_TYPEFLAG : _TAR_TYPEFLAG + 1]) in _REGULAR:
            name = header[_TAR_NAME].rstrip(b"\0").decode("utf-8", "replace")
            prefix = header[_TAR_PREFIX].rstrip(b"\0").decode("utf-8", "replace")
            yield (f"{prefix}/{name}" if prefix else name), data_offset, size
        offset = data_offset + _round_up_block(size)


def clip_records_from_shard(shard: str, read_range: ReadRange) -> list[dict[str, Any]]:
    """One record per `<stem>.mp4` that has a matching `<stem>.json` sidecar.

    An mp4 with no sidecar is dropped, not half-recorded. `CONTRACTS.md`'s null-together rule
    means a clip without `worker_id` could never produce a valid `FrameRef`, and a manifest row
    that cannot become a frame is worse than an absent one -- it would silently shrink the
    denominator of any draw that trusted the manifest's length.
    """
    videos: dict[str, tuple[int, int]] = {}
    sidecars: dict[str, tuple[int, int]] = {}
    for name, data_offset, size in walk_tar_members(read_range):
        stem, _, ext = name.rpartition(".")
        if ext == "mp4":
            videos[stem] = (data_offset, size)
        elif ext == "json" and size <= _MAX_SIDECAR_BYTES:
            sidecars[stem] = (data_offset, size)

    records: list[dict[str, Any]] = []
    for stem in sorted(videos):
        if stem not in sidecars:
            continue
        json_offset, json_size = sidecars[stem]
        payload = json.loads(read_range(json_offset, json_offset + json_size - 1))
        if "worker_id" not in payload or "duration_sec" not in payload:
            continue
        mp4_offset, mp4_size = videos[stem]
        records.append(
            {
                "shard": shard,
                "clip_id": stem,
                "factory_id": payload["factory_id"],
                "worker_id": payload["worker_id"],
                "video_index": payload.get("video_index"),
                "duration_sec": float(payload["duration_sec"]),
                "fps": float(payload["fps"]),
                "width": int(payload["width"]),
                "height": int(payload["height"]),
                "codec": payload["codec"],
                "mp4_offset": mp4_offset,
                "mp4_size": mp4_size,
            }
        )
    return records


# --------------------------------------------------------------------------------------
# Network: resolved CDN URLs, ranged reads, block cache
# --------------------------------------------------------------------------------------


class ShardReader:
    """A `read_range` over one shard's resolved CDN URL.

    Two things earn their keep here. **Block caching**: a header read is 512 bytes but a
    sidecar sits immediately after its mp4 and the next header immediately after that, so
    fetching an aligned window serves several logical reads per request -- measured at roughly
    a third of the requests a naive reader makes, and the difference between a ~50-minute scan
    and a multi-hour one. **URL refresh**: HF hands back a CloudFront-signed URL with an
    `Expires` claim, and a multi-hour scan outlives it; a 403 mid-scan is a stale signature,
    not a permissions failure, and must not be reported as one.
    """

    def __init__(self, repo_id: str, shard: str, token: str | None, window: int = 8192) -> None:
        self._repo_id = repo_id
        self._shard = shard
        self._token = token
        self._window = window
        self._url: str | None = None
        self._cache: dict[int, bytes] = {}

    def _resolve(self) -> str:
        from huggingface_hub import get_hf_file_metadata, hf_hub_url

        url = hf_hub_url(self._repo_id, self._shard, repo_type="dataset")
        return str(get_hf_file_metadata(url, token=self._token).location)

    def _fetch(self, start: int, end: int) -> bytes:
        import urllib.error
        import urllib.request

        for attempt in range(4):
            if self._url is None:
                self._url = self._resolve()
            request = urllib.request.Request(
                self._url, headers={"Range": f"bytes={start}-{end}"}
            )
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    return bytes(response.read())
            except urllib.error.HTTPError as exc:
                if exc.code in (403, 401):
                    self._url = None  # expired signature, not a permissions failure
                elif exc.code == 416:
                    return b""  # past end of object
                elif exc.code not in (429, 500, 502, 503, 504):
                    raise
                time.sleep(2**attempt)
            except (TimeoutError, OSError):
                time.sleep(2**attempt)
        raise RuntimeError(f"range {start}-{end} of {self._shard} failed after 4 attempts")

    def read_range(self, start: int, end_inclusive: int) -> bytes:
        out = bytearray()
        position = start
        while position <= end_inclusive:
            block_start = (position // self._window) * self._window
            block = self._cache.get(block_start)
            if block is None:
                block = self._fetch(block_start, block_start + self._window - 1)
                self._cache[block_start] = block
            chunk = block[position - block_start : end_inclusive - block_start + 1]
            if not chunk:
                break
            out += chunk
            position += len(chunk)
        return bytes(out)


def list_shards(repo_id: str, token: str | None) -> tuple[list[str], str]:
    from huggingface_hub import HfApi

    api = HfApi(token=token)
    info = api.dataset_info(repo_id)
    shards = sorted(s.rfilename for s in (info.siblings or []) if s.rfilename.endswith(".tar"))
    return shards, str(info.sha)


# --------------------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------------------


def _already_scanned(out_path: Path) -> set[str]:
    if not out_path.exists():
        return set()
    done: set[str] = set()
    with out_path.open() as handle:
        for line in handle:
            line = line.strip()
            if line:
                done.add(str(json.loads(line)["shard"]))
    return done


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/corpus_manifest_10k.jsonl")
    parser.add_argument("--repo-id", default=REPO_ID)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="shards to scan; small by default on purpose -- pass 0 for the whole corpus only "
        "after a smoke run has actually printed records (this repo's standing discipline, and "
        "the thing that caught D066's and D067's real bugs)",
    )
    args = parser.parse_args(argv)

    token = os.environ.get("HF_TOKEN") or None
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    shards, sha = list_shards(args.repo_id, token)
    done = _already_scanned(out_path)
    pending = [s for s in shards if s not in done]
    if args.limit:
        pending = pending[: args.limit]

    print(
        f"{args.repo_id} @ {sha}: {len(shards)} shards, {len(done)} already scanned, "
        f"{len(pending)} this run",
        flush=True,
    )

    lock = threading.Lock()
    started = time.time()
    counts = {"shards": 0, "clips": 0, "failed": 0}

    def scan(shard: str) -> None:
        try:
            reader = ShardReader(args.repo_id, shard, token)
            records = clip_records_from_shard(shard, reader.read_range)
        except Exception as exc:  # noqa: BLE001 -- one bad shard must not end a 1-hour run
            with lock:
                counts["failed"] += 1
                print(f"  FAILED {shard}: {type(exc).__name__} {exc}", file=sys.stderr, flush=True)
            return
        with lock, out_path.open("a") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
            counts["shards"] += 1
            counts["clips"] += len(records)
            if counts["shards"] % 200 == 0:
                rate = counts["shards"] / max(time.time() - started, 1e-9)
                remaining = (len(pending) - counts["shards"]) / max(rate, 1e-9)
                print(
                    f"  {counts['shards']}/{len(pending)} shards, {counts['clips']} clips, "
                    f"{rate:.2f} shards/s, ~{remaining / 60:.0f} min left",
                    flush=True,
                )

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(scan, pending))

    elapsed = time.time() - started
    print(
        f"done: {counts['shards']} shards, {counts['clips']} clips, {counts['failed']} failed, "
        f"{elapsed / 60:.1f} min -> {out_path}",
        flush=True,
    )
    return 1 if counts["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
