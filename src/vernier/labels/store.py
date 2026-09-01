"""The human annotation store.

Hard constraint, enforced here rather than by discipline: this store has no read path to
`vernier.judges` output. The `retest` pass additionally has no read path to the `primary` pass.
"""

from __future__ import annotations

from pathlib import Path

from vernier.models import HumanLabel, PassType


class HumanLabelStore:
    """Persists `HumanLabel` records. Never imports, calls, or exposes `vernier.judges`."""

    def __init__(self, path: Path) -> None:
        raise NotImplementedError

    def write(self, label: HumanLabel) -> None:
        """Append one label. Raises if a label for this `(frame_id, rater, pass_)` already exists --
        no frame is revisited within a pass."""
        raise NotImplementedError

    def read_pass(self, pass_: PassType) -> list[HumanLabel]:
        raise NotImplementedError

    def has_label(self, frame_id: str, pass_: PassType) -> bool:
        raise NotImplementedError
