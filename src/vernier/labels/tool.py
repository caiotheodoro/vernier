"""The labelling tool. Presents frames in random order, records both tasks, edge-case tags,
difficulty and seconds spent, per `docs/RUBRIC.md`.

The tool never displays judge output -- there is no parameter here that accepts a
`JudgeResponse`, by construction, not by convention.

`_pending_frames` is real: `docs/PRE-REGISTRATION.md`'s 600 primary labels are
`G200-ego`/`G200-ego4d`/`G200-epic` (200 each); the 100 blind retest is `R100`. Both must
already be drawn and persisted (`scripts/draw_all_samples.py`) before this tool has anything to
serve -- reads real, on-disk membership (`sampling.membership.load_membership`), never
re-draws.
"""

from __future__ import annotations

import random
from datetime import datetime, timezone
from pathlib import Path

from vernier.labels.store import HumanLabelStore
from vernier.models import EdgeCaseTag, FrameRef, HumanLabel, PassType
from vernier.sampling.draw import SampleName
from vernier.sampling.membership import load_membership

# Deterministic order per (rater, pass_): a fixed constant folded into the RNG seed alongside
# both, so the same rater+pass_ always sees the same order for a given pending pool, and
# different raters/passes get independent streams. Not a caller-supplied parameter --
# `next_frame`'s signature is frozen -- so this mirrors `sampling/draw.py`'s `_rng` seam.
_SEED = 777

# Re-declared, not imported, matching `sampling/draw.py`'s own `_MEMBERSHIP_ROOT` -- D033's
# no-shared-file-edits convention already established across this codebase for small constants
# like this one.
_MEMBERSHIP_ROOT = Path("data/membership")

# HumanLabelStore.has_label's own docstring: "callers keep one store per rater" -- one
# subdirectory per rater under this root. Only one rater exists per the pre-registration
# ("one rater", Wave 3), but the store's own stated convention is per-rater regardless.
_LABEL_STORE_ROOT = Path("data/labels")

# docs/PRE-REGISTRATION.md's "Samples" table: 600 primary = 200 + 200 + 200 across the three
# G200-* sets; the 100 blind retest is R100 alone.
_PRIMARY_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")
_RETEST_SAMPLE: SampleName = "R100"


def _rng(rater: str, pass_: PassType) -> random.Random:
    """One independent, deterministic RNG stream per (rater, pass_) pair."""
    return random.Random(f"{_SEED}:{rater}:{pass_}")


def _label_store(rater: str) -> HumanLabelStore:
    return HumanLabelStore(_LABEL_STORE_ROOT / rater)


def _pending_frames(pass_: PassType, rater: str) -> list[FrameRef]:
    """The pool `next_frame` picks from: real sample membership for `pass_` minus whatever
    `HumanLabelStore.has_label` already reports for `rater`.

    Raises `sampling.membership.MembershipNotFoundError` if the underlying sample hasn't been
    drawn and persisted yet (`scripts/draw_all_samples.py`) -- there is no synthetic fallback;
    an empty or missing pool here means the real prerequisite is missing, not that labelling is
    done.
    """
    store = _label_store(rater)
    samples = _PRIMARY_SAMPLES if pass_ == "primary" else (_RETEST_SAMPLE,)
    pool = [f for sample in samples for f in load_membership(sample, _MEMBERSHIP_ROOT)]
    return [f for f in pool if not store.has_label(f.frame_id, pass_)]


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
