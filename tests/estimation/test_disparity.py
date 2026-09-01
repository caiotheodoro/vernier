"""Behavioural tests for `vernier.estimation.disparity`, written before the body exists.

H8 is a pass-through report of public participant counts, not an ICC-adjusted effective N
(docs/DECISIONS.md D031) -- these tests check the round-trip and the validation contract
(`CONTRACTS.md` rule 2: absence/nonsense must be explicit, never silently passed through),
not any statistical computation.
"""

from __future__ import annotations

import pytest

from vernier.estimation.disparity import participant_count_disparity

# Corrected figures per docs/DECISIONS.md D024/D031, cross-checked against docs/BENCHMARK.md's
# R0 table and docs/HANDOFF.md -- NOT the pre-registration's original "~45" EPIC-KITCHENS-100
# estimate, which D024 found was actually the kitchen/environment count, not participants.
CORRECTED_COUNTS = {
    "egocentric-10k": 2153,
    "ego4d": 923,
    "epic-kitchens-100": 37,
}


def test_corrected_counts_round_trip_and_show_near_two_orders_of_magnitude_spread() -> None:
    result = participant_count_disparity(CORRECTED_COUNTS)

    for corpus, count in CORRECTED_COUNTS.items():
        assert result[corpus] == count

    spread = max(CORRECTED_COUNTS.values()) / min(CORRECTED_COUNTS.values())
    assert spread > 50  # 2153 / 37 ~= 58.2 -- close to two orders of magnitude, per D024.


def test_empty_dict_raises() -> None:
    with pytest.raises(ValueError):
        participant_count_disparity({})


@pytest.mark.parametrize("bad_count", [0, -1, -37])
def test_zero_or_negative_count_raises(bad_count: int) -> None:
    with pytest.raises(ValueError):
        participant_count_disparity({"egocentric-10k": 2153, "ego4d": bad_count})


def test_does_not_drop_or_rename_a_corpus_key() -> None:
    result = participant_count_disparity(CORRECTED_COUNTS)

    assert set(result.keys()) == set(CORRECTED_COUNTS.keys())
    assert len(result) == len(CORRECTED_COUNTS)
