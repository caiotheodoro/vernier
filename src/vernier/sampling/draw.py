"""Draws every sample fixed in ``docs/PRE-REGISTRATION.md``. Emits `FrameRef` records.

Owns: seed handling, stratification, the <=1-frame-per-clip constraint, and the `worker_id`
cluster assignment every downstream interval depends on. Depends on: the HF dataset metadata
only -- it never decodes a frame it was not asked for.

Seam: corpus-specific identifier mapping. Ego4D and EPIC-KITCHENS-100 name their participant
field differently; `normalize_worker_id` normalises into `worker_id` and records the original
in `corpus`.

Wave 1 is offline by design: this module never touches the network, `huggingface_hub`, or the
`datasets` library. `_candidate_frames` and `_factory_worker_hours` are the seams Wave 2
replaces with real HF/parquet wiring; everything else here -- stratification, the worker-hours
weighting, the per-clip cap, seeded determinism, the P2k/G200/R100 subset relationships, and
the revision-pin check -- is real and unit-tested against synthetic pools.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Literal

from vernier.models import FrameRef
from vernier.sampling.revisions import assert_pinned_revision

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

# docs/PRE-REGISTRATION.md "Samples" table.
_N: dict[SampleName, int] = {
    "E10k-ego": 10_000,
    "E10k-ego4d": 10_000,
    "E10k-epic": 10_000,
    "S10k-U": 10_000,
    "S10k-S": 10_000,
    "P2k": 2_000,
    "G200-ego": 200,
    "G200-ego4d": 200,
    "G200-epic": 200,
    "R100": 100,
}

# Every sample here is a random subset of exactly one other, already-drawn sample's membership
# (docs/PRE-REGISTRATION.md "Samples" table). R100 is the one exception -- a subset of the
# *union* of three parents -- and is handled separately below.
_PARENT: dict[SampleName, SampleName] = {
    "P2k": "E10k-ego",
    "G200-ego": "P2k",
    "G200-ego4d": "E10k-ego4d",
    "G200-epic": "E10k-epic",
}

_R100_PARENTS: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")

# docs/UPSTREAM-FINDINGS.md F5 / sampling/revisions.py: the evaluation release redistributes
# the Ego4D and EPIC-KITCHENS-100 frames directly, so this one HF repo id covers every corpus
# arm `draw_sample` draws from -- there is (so far) exactly one entry in `PINNED_REVISIONS`.
_EVAL_HF_REPO = "builddotai/Egocentric-10K-Evaluation"

# Where a subset sample's parent membership is read from. `write_membership`/`load_membership`
# take an explicit `path` (sampling/membership.py); `draw_sample`'s signature is frozen with no
# room for one, so this fixes a convention for the parent-membership lookup a subset draw needs.
# Reviewer note: this is this unit's own choice, not one taken from an existing convention
# elsewhere in the repo -- the real on-disk layout is an orchestration concern Wave 2 may need
# to revisit.
_MEMBERSHIP_ROOT = Path("data/membership")


def _membership_path(sample: SampleName) -> Path:
    return _MEMBERSHIP_ROOT / f"{sample}.json"


def _rng(seed: int, sample: SampleName) -> random.Random:
    """One independent, deterministic RNG stream per (seed, sample) pair."""
    return random.Random(f"{seed}:{sample}")


def _candidate_frames(sample: SampleName) -> list[FrameRef]:
    """Wave 2 seam: the pool `draw_sample` samples from.

    For `S10k-U`/`S10k-S` this is fresh Egocentric-10K corpus metadata; for the `E10k-*`
    family it is Build AI's evaluation-release frame list. Real HF/parquet wiring is Wave 2's
    job -- Wave 1 unit tests monkeypatch this with synthetic in-memory `FrameRef` pools.
    """
    raise NotImplementedError


def _factory_worker_hours(sample: SampleName) -> dict[str, float]:
    """Wave 2 seam: per-factory worker-hours used to weight `S10k-S`'s stratification.

    Not a `FrameRef` field -- Build AI's corpus metadata carries factory worker-hours
    separately from any single frame, so this is its own seam alongside `_candidate_frames`.
    Returns ``{factory_id: worker_hours}``. Real wiring is Wave 2's job.
    """
    raise NotImplementedError


def _apportion(weights: dict[str, float], total: int) -> dict[str, int]:
    """Largest-remainder apportionment of `total` units across `weights`, proportional to
    each key's weight. Deterministic tie-break: remainder units go to the largest fractional
    remainder first, ties broken by key so the result never depends on dict iteration order.
    """
    result = {k: 0 for k in weights}
    total_weight = sum(weights.values())
    if total <= 0 or total_weight <= 0:
        return result
    exact = {k: w / total_weight * total for k, w in weights.items()}
    floors = {k: int(v) for k, v in exact.items()}
    remainder = total - sum(floors.values())
    order = sorted(weights.keys(), key=lambda k: (-(exact[k] - floors[k]), k))
    for k in order[:remainder]:
        floors[k] += 1
    return floors


def _check_revision(sample: SampleName, frames: list[FrameRef]) -> None:
    """Enforce the HF revision pin against every distinct `corpus_rev` in `frames`."""
    revs = sorted({f.corpus_rev for f in frames})
    for rev in revs:
        assert_pinned_revision(_EVAL_HF_REPO, rev)


def _draw_uniform_corpus(sample: SampleName, seed: int) -> list[FrameRef]:
    pool = _candidate_frames(sample)
    n = min(_N[sample], len(pool))
    chosen = _rng(seed, sample).sample(pool, n)
    return [f.model_copy(update={"sample": sample, "stratum": "unstratified"}) for f in chosen]


def _draw_stratified_corpus(sample: SampleName, seed: int) -> list[FrameRef]:
    pool = _candidate_frames(sample)
    weights = _factory_worker_hours(sample)
    rng = _rng(seed, sample)

    by_factory: dict[str, list[FrameRef]] = {}
    for f in pool:
        assert f.factory_id is not None, "S10k-S draws from full-provenance corpus metadata"
        by_factory.setdefault(f.factory_id, []).append(f)

    # <=1 frame per clip, chosen deterministically (rng.choice, seeded) per clip.
    deduped: dict[str, list[FrameRef]] = {}
    for factory_id, frames in by_factory.items():
        by_clip: dict[str, list[FrameRef]] = {}
        for f in frames:
            assert f.clip_id is not None, "S10k-S draws from full-provenance corpus metadata"
            by_clip.setdefault(f.clip_id, []).append(f)
        deduped[factory_id] = [rng.choice(cf) for _, cf in sorted(by_clip.items())]

    total_available = sum(len(v) for v in deduped.values())
    n_target = min(_N[sample], total_available)
    alloc = _apportion({k: weights.get(k, 0.0) for k in deduped}, n_target)

    result: list[FrameRef] = []
    for factory_id, frames in deduped.items():
        k = min(alloc.get(factory_id, 0), len(frames))
        chosen = rng.sample(frames, k)
        result.extend(
            f.model_copy(update={"sample": sample, "stratum": f"factory-{factory_id}"})
            for f in chosen
        )
    return result


def _draw_evaluation_release(sample: SampleName) -> list[FrameRef]:
    # "Essentially all of them" -- not a fresh draw, so no RNG. Sorted by frame_id so the
    # result is deterministic regardless of the upstream pool's own ordering.
    pool = sorted(_candidate_frames(sample), key=lambda f: f.frame_id)
    n = min(_N[sample], len(pool))
    return [f.model_copy(update={"sample": sample}) for f in pool[:n]]


def _load_parent_membership(parent: SampleName) -> list[FrameRef]:
    # Local import: `membership.py` imports `SampleName` from this module at module scope, so
    # importing `membership` back at this module's top level would be circular. Deferred to
    # call time, by which point both modules are fully loaded.
    from vernier.sampling import membership

    return membership.load_membership(parent, _membership_path(parent))


def _draw_subset(sample: SampleName, seed: int) -> list[FrameRef]:
    parent = _PARENT[sample]
    pool = _load_parent_membership(parent)
    n = min(_N[sample], len(pool))
    chosen = _rng(seed, sample).sample(pool, n)
    return [f.model_copy(update={"sample": sample}) for f in chosen]


def _draw_r100(seed: int) -> list[FrameRef]:
    union = [f for parent in _R100_PARENTS for f in _load_parent_membership(parent)]
    n = min(_N["R100"], len(union))
    chosen = _rng(seed, "R100").sample(union, n)
    return [f.model_copy(update={"sample": "R100"}) for f in chosen]


def draw_sample(sample: SampleName, *, seed: int = PRE_REGISTRATION_SEED) -> list[FrameRef]:
    """Draw the named sample per its definition in `docs/PRE-REGISTRATION.md`.

    Must be called at most once per `sample` for the life of a run: membership is fixed at
    draw time and is never redrawn.
    """
    if sample == "S10k-U":
        frames = _draw_uniform_corpus(sample, seed)
    elif sample == "S10k-S":
        frames = _draw_stratified_corpus(sample, seed)
    elif sample in ("E10k-ego", "E10k-ego4d", "E10k-epic"):
        frames = _draw_evaluation_release(sample)
    elif sample == "R100":
        frames = _draw_r100(seed)
    else:
        frames = _draw_subset(sample, seed)

    _check_revision(sample, frames)
    return frames


def normalize_worker_id(corpus: str, raw_participant_field: str) -> str:
    """The corpus-adapter seam: map a corpus's native participant identifier to `worker_id`.

    TODO(Wave 2): Ego4D and EPIC-KITCHENS-100 name their participant field differently
    (docs/ARCHITECTURE.md's stated seam), but the exact upstream field names are not yet
    inspected anywhere in this repo (`docs/UPSTREAM-FINDINGS.md` documents the evaluation
    parquet schema, F9, but not the raw corpus-side participant field naming). Rather than
    guess a mapping and assert it is correct, this is the identity mapping for every corpus
    until that inspection happens: the caller's raw participant string is returned unchanged,
    and `corpus` disambiguates it downstream, exactly as `CONTRACTS.md` describes ("recorded
    in the same field with corpus disambiguating it").
    """
    return raw_participant_field
