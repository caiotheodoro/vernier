"""Writes and reads back sample membership, and the reserve-list swap for undecodable frames.

Membership is written to disk before any judge is called on it -- the fixed point everything
downstream depends on never being silently redrawn.
"""

from __future__ import annotations

from pathlib import Path

from vernier.models import FrameRef
from vernier.sampling.draw import SampleName


def write_membership(sample: SampleName, frames: list[FrameRef], path: Path) -> None:
    """Persist sample membership to disk before any judge is called on it."""
    raise NotImplementedError


def load_membership(sample: SampleName, path: Path) -> list[FrameRef]:
    """Read back a previously written sample. Raises if `path` holds no record of `sample`."""
    raise NotImplementedError


def replace_undecodable(frame: FrameRef, reserve: list[FrameRef]) -> FrameRef:
    """Swap an undecodable frame for the next reserve frame. Every replacement is logged."""
    raise NotImplementedError
