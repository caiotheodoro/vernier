"""The labelling tool. Presents frames in random order, records both tasks, edge-case tags,
difficulty and seconds spent, per `docs/RUBRIC.md`.

The tool never displays judge output -- there is no parameter here that accepts a
`JudgeResponse`, by construction, not by convention.
"""

from __future__ import annotations

from vernier.models import EdgeCaseTag, FrameRef, HumanLabel, PassType


def next_frame(pass_: PassType, rater: str) -> FrameRef | None:
    """Return the next frame to label in random order, or None when the pass is complete."""
    raise NotImplementedError


def record_label(
    frame: FrameRef,
    rater: str,
    pass_: PassType,
    rubric_rev: str,
    hands_visible: int,
    manipulation: bool,
    edge_case: list[EdgeCaseTag],
    difficulty: str,
    note: str,
    seconds_spent: int,
) -> HumanLabel:
    """Build and store one `HumanLabel`. `difficulty` is recorded before any judge answer
    could be displayed, because none ever is."""
    raise NotImplementedError
