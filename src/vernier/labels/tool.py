"""The labelling tool. Presents frames in random order, records both tasks, edge-case tags,
difficulty and seconds spent, per `docs/RUBRIC.md`.

The tool never displays judge output -- there is no parameter here that accepts a
`JudgeResponse`, by construction, not by convention.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from vernier.models import EdgeCaseTag, FrameRef, HumanLabel, PassType

# Deterministic order per (rater, pass_): a fixed constant folded into the RNG seed alongside
# both, so the same rater+pass_ always sees the same order for a given pending pool, and
# different raters/passes get independent streams. Not a caller-supplied parameter --
# `next_frame`'s signature is frozen -- so this mirrors `sampling/draw.py`'s `_rng` seam.
_SEED = 777


def _rng(rater: str, pass_: PassType) -> random.Random:
    """One independent, deterministic RNG stream per (rater, pass_) pair."""
    return random.Random(f"{_SEED}:{rater}:{pass_}")


def _pending_frames(pass_: PassType, rater: str) -> list[FrameRef]:
    """Wave 2 seam: the pool `next_frame` picks from -- sample membership for `pass_` minus
    whatever `HumanLabelStore.has_label` already reports for `rater`. Real wiring is Wave 2's
    job; Wave 1 unit tests monkeypatch this with synthetic in-memory `FrameRef` pools.
    """
    raise NotImplementedError


def next_frame(pass_: PassType, rater: str) -> FrameRef | None:
    """Return the next frame to label in random order, or None when the pass is complete.

    Calling this repeatedly with no intervening label recorded returns the SAME frame each
    time -- `_pending_frames`' pool only shrinks once `HumanLabelStore.write` has actually
    recorded a label for it. The intended flow is `next_frame` -> label it -> `record_label` ->
    `HumanLabelStore.write` -> `next_frame` again, not two `next_frame` calls back to back.
    """
    pending = _pending_frames(pass_, rater)
    if not pending:
        return None
    return _rng(rater, pass_).choice(pending)


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
    """Build and return one `HumanLabel`. `difficulty` is recorded before any judge answer
    could ever be shown -- this function has no read path to `vernier.judges` output.

    Does not persist the record; a caller writes it via `HumanLabelStore.write`.
    """
    payload: dict[str, object] = dict(
        frame_id=frame.frame_id,
        rater=rater,
        pass_=pass_,
        rubric_rev=rubric_rev,
        hands_visible=hands_visible,
        manipulation=manipulation,
        edge_case=tuple(edge_case),
        difficulty=difficulty,
        note=note,
        labelled_at=datetime.now(timezone.utc),
        seconds_spent=seconds_spent,
    )
    return HumanLabel.model_validate(payload)
