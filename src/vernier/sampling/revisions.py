"""HF revision pins, and the pure check that enforces them.

Sourced from `docs/upstream/PROVENANCE.json`, never invented -- a revision pin that isn't
independently reproducible from the pinned snapshot is exactly the "prose only" gap this
module closes (`docs/HANDOFF.md` P1 tier). `docs/UPSTREAM-FINDINGS.md` F5: the evaluation
release redistributes the Ego4D and EPIC-KITCHENS-100 frames directly, so one dataset's
revision covers every corpus arm `sampling` draws from.

Wiring this into `draw_sample()` itself (`sampling/draw.py`) is Wave 1 unit 1's job, not this
module's -- this only has to exist so that unit imports and calls it rather than re-deriving
the pin.
"""

from __future__ import annotations

PINNED_REVISIONS: dict[str, str] = {
    "builddotai/Egocentric-10K-Evaluation": "d74b7883c998dd360e3f051830fcc792a83985e6",
    # docs/DECISIONS.md D066: Build AI's current-product evaluation release. Real revision sha,
    # live-resolved via HfApi().dataset_info(...).sha, sourced from
    # docs/upstream/PROVENANCE-100k-eval.json, never invented.
    "builddotai/Egocentric-100K-Evaluation": "d0f69a56b0525c1bead80d918dc57ef83dcac899",
    # docs/DECISIONS.md D065/D071: the RAW corpus S10k-U/S10k-S draw from -- a different repo
    # and a different format (WebDataset tars of h265 video) from the two evaluation releases
    # above. Real revision sha, live-resolved via HfApi().dataset_info(...).sha, sourced from
    # docs/upstream/PROVENANCE-10k-raw.json, never invented.
    "builddotai/Egocentric-10K": "3e5f87c88c54ce8343865d8e2a8c171f18385a05",
}


def assert_pinned_revision(corpus: str, corpus_rev: str) -> None:
    """Raise if `corpus_rev` does not match the pin recorded for `corpus`.

    `corpus` here is the HF dataset repo id (e.g. `builddotai/Egocentric-10K-Evaluation`), not
    `FrameRef.corpus`'s short label (e.g. `egocentric-10k`) -- callers map between the two at
    the draw-time seam, since that mapping is `draw_sample`'s concern, not this one's.
    """
    pinned = PINNED_REVISIONS.get(corpus)
    if pinned is None:
        raise ValueError(f"no pinned revision recorded for corpus {corpus!r}")
    if corpus_rev != pinned:
        raise ValueError(
            f"corpus_rev mismatch for {corpus!r}: pinned {pinned!r}, got {corpus_rev!r}"
        )
