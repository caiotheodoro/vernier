"""Draws every sample fixed in ``docs/PRE-REGISTRATION.md``. Emits `FrameRef` records.

Owns: seed handling, stratification, the <=1-frame-per-clip constraint, and the `worker_id`
cluster assignment every downstream interval depends on. Depends on: the HF dataset metadata
only -- it never decodes a frame it was not asked for.

Seam: corpus-specific identifier mapping. Ego4D and EPIC-KITCHENS-100 name their participant
field differently; `normalize_worker_id` normalises into `worker_id` and records the original
in `corpus`.
"""

from __future__ import annotations

from typing import Literal

from vernier.models import FrameRef

SampleName = Literal[
    "E10k-ego",
    "E10k-ego4d",
    "E10k-epic",
    "S10k-U",
    "S10k-S",
    "P2k",
    "G200-ego",
    "G200-ego4d",
    "G200-epic",
    "R100",
]

PRE_REGISTRATION_SEED = 777


def draw_sample(sample: SampleName, *, seed: int = PRE_REGISTRATION_SEED) -> list[FrameRef]:
    """Draw the named sample per its definition in `docs/PRE-REGISTRATION.md`.

    Must be called at most once per `sample` for the life of a run: membership is fixed at
    draw time and is never redrawn.
    """
    raise NotImplementedError


def normalize_worker_id(corpus: str, raw_participant_field: str) -> str:
    """The corpus-adapter seam: map a corpus's native participant identifier to `worker_id`."""
    raise NotImplementedError
