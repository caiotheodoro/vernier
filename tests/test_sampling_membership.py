"""Behavioural tests for `vernier.sampling.membership`, written before the bodies exist.

Covers the round-trip contract `write_membership`/`load_membership` must hold (PRE-REGISTRATION.md:
"Membership is written to disk before any judge is called and is never redrawn") and the reserve
swap `replace_undecodable` performs for undecodable frames.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.fixtures import make_frame_ref
from vernier.sampling.membership import (
    MembershipNotFoundError,
    ReserveExhaustedError,
    load_membership,
    replace_undecodable,
    write_membership,
)


def test_round_trip_write_then_load_is_equal(tmp_path: Path) -> None:
    frames = [
        make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000418", frame_index=418),
        make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000419", frame_index=419),
    ]

    write_membership("S10k-U", frames, tmp_path)
    loaded = load_membership("S10k-U", tmp_path)

    assert loaded == frames


def test_write_does_not_clobber_a_different_sample_at_the_same_path(tmp_path: Path) -> None:
    frames_a = [make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000418", sample="S10k-U")]
    frames_b = [
        make_frame_ref(
            frame_id="ego10k/f0099/w00001/v0002/000001",
            factory_id="0099",
            worker_id="00001",
            clip_id="0002",
            frame_index=1,
            sample="S10k-S",
            stratum="factory-0099",
        )
    ]

    write_membership("S10k-U", frames_a, tmp_path)
    write_membership("S10k-S", frames_b, tmp_path)

    assert load_membership("S10k-U", tmp_path) == frames_a
    assert load_membership("S10k-S", tmp_path) == frames_b


def test_load_membership_raises_when_sample_was_never_written(tmp_path: Path) -> None:
    with pytest.raises(MembershipNotFoundError):
        load_membership("S10k-U", tmp_path)


def test_load_membership_raises_for_unwritten_sample_when_other_samples_exist(
    tmp_path: Path,
) -> None:
    write_membership("S10k-U", [make_frame_ref()], tmp_path)

    with pytest.raises(MembershipNotFoundError):
        load_membership("P2k", tmp_path)


def test_replace_undecodable_pops_next_reserve_frame_and_preserves_original(
    tmp_path: Path,
) -> None:
    original = make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000418")
    reserve_head = make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000900", frame_index=900)
    reserve_tail = make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000901", frame_index=901)
    reserve = [reserve_head, reserve_tail]

    replacement = replace_undecodable(original, reserve)

    assert replacement == reserve_head
    assert reserve == [reserve_tail]
    assert original == make_frame_ref(frame_id="ego10k/f0051/w00243/v0007/000418")


def test_replace_undecodable_on_empty_reserve_raises(tmp_path: Path) -> None:
    original = make_frame_ref()

    with pytest.raises(ReserveExhaustedError):
        replace_undecodable(original, [])
