from __future__ import annotations

import pytest

from vernier.sampling.revisions import PINNED_REVISIONS, assert_pinned_revision


def test_pinned_revision_matches_provenance_snapshot() -> None:
    # Sourced from docs/upstream/PROVENANCE.json -- not invented.
    assert (
        PINNED_REVISIONS["builddotai/Egocentric-10K-Evaluation"]
        == "d74b7883c998dd360e3f051830fcc792a83985e6"
    )


def test_assert_pinned_revision_accepts_matching_revision() -> None:
    assert_pinned_revision(
        "builddotai/Egocentric-10K-Evaluation", "d74b7883c998dd360e3f051830fcc792a83985e6"
    )


def test_assert_pinned_revision_rejects_drifted_revision() -> None:
    with pytest.raises(ValueError, match="corpus_rev mismatch"):
        assert_pinned_revision("builddotai/Egocentric-10K-Evaluation", "deadbeef")


def test_assert_pinned_revision_rejects_unknown_corpus() -> None:
    with pytest.raises(ValueError, match="no pinned revision"):
        assert_pinned_revision("builddotai/some-other-dataset", "whatever")


def test_pinned_revision_100k_eval_matches_provenance_snapshot() -> None:
    # Sourced from docs/upstream/PROVENANCE-100k-eval.json -- not invented (docs/DECISIONS.md D066).
    assert (
        PINNED_REVISIONS["builddotai/Egocentric-100K-Evaluation"]
        == "d0f69a56b0525c1bead80d918dc57ef83dcac899"
    )


def test_assert_pinned_revision_accepts_matching_100k_eval_revision() -> None:
    assert_pinned_revision(
        "builddotai/Egocentric-100K-Evaluation", "d0f69a56b0525c1bead80d918dc57ef83dcac899"
    )


def test_assert_pinned_revision_rejects_drifted_100k_eval_revision() -> None:
    with pytest.raises(ValueError, match="corpus_rev mismatch"):
        assert_pinned_revision("builddotai/Egocentric-100K-Evaluation", "deadbeef")
