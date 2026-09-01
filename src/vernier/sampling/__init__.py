"""Draws every sample fixed in ``docs/PRE-REGISTRATION.md`` and writes membership to disk
before anything else runs. Emits `FrameRef` records.

Two units, split for Wave 1 file-ownership (`docs/DECISIONS.md` D033): `draw.py` owns seed
handling, stratification, the <=1-frame-per-clip constraint, and the `worker_id` cluster
assignment (via the corpus-adapter seam `normalize_worker_id`); `membership.py` owns writing,
reading back, and the reserve-list swap for undecodable frames. This module re-exports both.
"""

from __future__ import annotations

from vernier.sampling.draw import (
    PRE_REGISTRATION_SEED,
    SampleName,
    draw_sample,
    normalize_worker_id,
)
from vernier.sampling.membership import load_membership, replace_undecodable, write_membership

__all__ = [
    "PRE_REGISTRATION_SEED",
    "SampleName",
    "draw_sample",
    "load_membership",
    "normalize_worker_id",
    "replace_undecodable",
    "write_membership",
]
