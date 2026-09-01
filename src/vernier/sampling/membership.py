"""Writes and reads back sample membership, and the reserve-list swap for undecodable frames.

Membership is written to disk before any judge is called on it -- the fixed point everything
downstream depends on never being silently redrawn.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from vernier.models import FrameRef
from vernier.sampling.draw import SampleName

_FRAME_LIST_ADAPTER = TypeAdapter(list[FrameRef])


class MembershipNotFoundError(LookupError):
    """Raised when `path` holds no membership record for the requested sample."""


class ReserveExhaustedError(RuntimeError):
    """Raised when `replace_undecodable` is called with an empty reserve list."""


def _member_path(sample: SampleName, path: Path) -> Path:
    return path / f"{sample}.json"


def write_membership(sample: SampleName, frames: list[FrameRef], path: Path) -> None:
    """Persist sample membership to disk before any judge is called on it.

    On-disk layout: one JSON file per sample, `<path>/<sample>.json`, holding a JSON array of
    `FrameRef` objects (each shaped per `FrameRef.model_dump(mode="json")`). One file per sample
    means writing one sample never touches another sample's file, and `load_membership` reads
    the array back with `TypeAdapter(list[FrameRef]).validate_json`.
    """
    path.mkdir(parents=True, exist_ok=True)
    _member_path(sample, path).write_bytes(_FRAME_LIST_ADAPTER.dump_json(frames))


def load_membership(sample: SampleName, path: Path) -> list[FrameRef]:
    """Read back a previously written sample. Raises if `path` holds no record of `sample`."""
    member_path = _member_path(sample, path)
    if not member_path.is_file():
        raise MembershipNotFoundError(f"no membership recorded for sample {sample!r} at {path}")
    return _FRAME_LIST_ADAPTER.validate_json(member_path.read_bytes())


def replace_undecodable(frame: FrameRef, reserve: list[FrameRef]) -> FrameRef:
    """Swap an undecodable frame for the next reserve frame. Every replacement is logged.

    Pops and returns the frame at the front of `reserve` (mutating `reserve` in place), leaving
    `frame` untouched -- the caller logs the swap using `frame` (what was replaced) and the
    returned `FrameRef` (its replacement), since this function has no I/O side-channel of its
    own to log through.
    """
    if not reserve:
        raise ReserveExhaustedError("reserve list is exhausted, no frame left to substitute")
    return reserve.pop(0)
