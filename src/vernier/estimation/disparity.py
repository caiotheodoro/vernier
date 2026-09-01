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

    Output shape: an unchanged copy of `participant_counts` -- same keys, same values, same
    corpus labels. No derived ratio, rank, or ICC-adjusted figure is added; H8's finding is the
    raw counts themselves (`docs/DECISIONS.md` D024), and adding a computed column here would
    reintroduce the "effective N" framing D031 explicitly removed. Callers that want the spread
    compute it themselves from this pass-through.

    Raises `ValueError` if `participant_counts` is empty or any count is not positive --
    `CONTRACTS.md` rule 2: absence (or a nonsensical zero/negative count) must be explicit,
    never silently reported as a real value.
    """
    if not participant_counts:
        raise ValueError("participant_counts must not be empty")
    for corpus, count in participant_counts.items():
        if count <= 0:
            raise ValueError(
                f"participant count for {corpus!r} must be positive, got {count}"
            )
    return dict(participant_counts)
