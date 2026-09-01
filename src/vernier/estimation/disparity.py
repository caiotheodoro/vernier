"""H8's participant-count precision-disparity lookup.

Not an ICC-adjusted effective sample size -- no such computation exists here or anywhere in
this repo (`docs/DECISIONS.md` D031). A true effective N, once R100/primary labelling produces
real cluster-size and outcome-variance data, belongs in `estimation.bootstrap.design_effect`,
not in this pre-labelling lookup.
"""

from __future__ import annotations


def participant_count_disparity(participant_counts: dict[str, int]) -> dict[str, int]:
    """H8: the participant-count precision disparity per corpus. No experiment required.

    A pass-through report of public participant counts, not an ICC-adjusted effective sample
    size -- see this module's docstring and `docs/DECISIONS.md` D031.
    """
    raise NotImplementedError
