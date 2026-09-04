"""Behavioural tests for `scripts/build_corpus_manifest.py`.

The tar walk is the load-bearing part and it is pure: it takes a `read_range(start, end)`
callable, so a synthetic tar in `tmp_path` exercises it with no network. The golden case
checks the walk against Python's own `tarfile.getmembers()` -- a hand-computable expected
answer would just be a re-implementation of the same offset arithmetic, whereas `tarfile` is
an independent oracle for exactly this format (`docs/WAVES.md` mandates a golden case for
statistical units; this is the equivalent for a parser).
"""

from __future__ import annotations

import io
import json
import sys
import tarfile
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from build_corpus_manifest import clip_records_from_shard, walk_tar_members  # noqa: E402


def _build_tar(path: Path, members: dict[str, bytes]) -> None:
    with tarfile.open(path, "w") as tar:
        for name, payload in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            tar.addfile(info, io.BytesIO(payload))


def _reader(path: Path) -> Callable[[int, int], bytes]:
    def read_range(start: int, end_inclusive: int) -> bytes:
        with path.open("rb") as handle:
            handle.seek(start)
            return handle.read(end_inclusive - start + 1)

    return read_range


def _sidecar(factory: str, worker: str, index: int, duration: float) -> bytes:
    return json.dumps(
        {
            "factory_id": factory,
            "worker_id": worker,
            "video_index": index,
            "duration_sec": duration,
            "width": 1920,
            "height": 1080,
            "fps": 30.0,
            "size_bytes": 123,
            "codec": "h265",
        }
    ).encode()


def test_walk_recovers_the_same_offsets_and_sizes_as_tarfile(tmp_path: Path) -> None:
    """Golden case. `tarfile` reads the whole file locally; `walk_tar_members` reads 512 bytes
    at a time through a range callable. They must agree exactly, or every byte offset the
    adapter later hands to ffmpeg is wrong."""
    path = tmp_path / "shard.tar"
    _build_tar(
        path,
        {
            "factory001_worker001_00000.mp4": b"\xde\xad" * 900,
            "factory001_worker001_00000.json": _sidecar("factory_001", "worker_001", 0, 180.0),
            "factory001_worker001_00001.mp4": b"\xbe\xef" * 1500,
            "factory001_worker001_00001.json": _sidecar("factory_001", "worker_001", 1, 433.4),
        },
    )

    walked = list(walk_tar_members(_reader(path)))

    with tarfile.open(path) as tar:
        expected = [(m.name, m.offset_data, m.size) for m in tar.getmembers()]
    assert walked == expected


def test_walk_stops_at_the_end_of_archive_marker(tmp_path: Path) -> None:
    path = tmp_path / "shard.tar"
    _build_tar(path, {"only.mp4": b"x" * 10})

    assert [name for name, _, _ in walk_tar_members(_reader(path))] == ["only.mp4"]


def test_clip_records_pair_each_mp4_with_its_sidecar(tmp_path: Path) -> None:
    path = tmp_path / "shard.tar"
    _build_tar(
        path,
        {
            "factory001_worker001_00000.mp4": b"\x00" * 2048,
            "factory001_worker001_00000.json": _sidecar("factory_001", "worker_001", 0, 180.0),
        },
    )

    records = clip_records_from_shard("f/w/shard.tar", _reader(path))

    assert len(records) == 1
    record = records[0]
    assert record["shard"] == "f/w/shard.tar"
    assert record["clip_id"] == "factory001_worker001_00000"
    assert record["factory_id"] == "factory_001"
    assert record["worker_id"] == "worker_001"
    assert record["duration_sec"] == 180.0
    assert record["fps"] == 30.0
    assert record["codec"] == "h265"
    assert record["width"] == 1920
    assert record["height"] == 1080
    assert record["mp4_size"] == 2048
    # The byte window ffmpeg's `subfile` protocol is handed. Off by one here and every
    # extracted frame is garbage, so it is asserted against tarfile's own offset.
    with tarfile.open(path) as tar:
        assert record["mp4_offset"] == tar.getmember("factory001_worker001_00000.mp4").offset_data


def test_an_mp4_with_no_sidecar_is_dropped_not_half_recorded(tmp_path: Path) -> None:
    """`CONTRACTS.md`: absence is explicit. A clip whose provenance JSON is missing has no
    `worker_id`, and a `FrameRef` built from it could not satisfy the null-together validator,
    so it must not reach the manifest at all."""
    path = tmp_path / "shard.tar"
    _build_tar(path, {"orphan.mp4": b"\x00" * 512})

    assert clip_records_from_shard("f/w/shard.tar", _reader(path)) == []


def test_non_clip_json_members_are_ignored(tmp_path: Path) -> None:
    path = tmp_path / "shard.tar"
    _build_tar(
        path,
        {
            "intrinsics.json": json.dumps({"model": "fisheye", "fx": 1.0}).encode(),
            "factory001_worker001_00000.mp4": b"\x00" * 512,
            "factory001_worker001_00000.json": _sidecar("factory_001", "worker_001", 0, 90.0),
        },
    )

    records = clip_records_from_shard("f/w/shard.tar", _reader(path))

    assert [r["clip_id"] for r in records] == ["factory001_worker001_00000"]
