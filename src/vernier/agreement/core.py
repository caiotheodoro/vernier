"""Agreement statistics and the `AgreementResult` assembler.

Owns Gwet's AC1 as the primary statistic, Cohen's kappa beside it, Fleiss' kappa across the
panel, and intra-rater kappa on `R100`. Every exclusion is counted with its reason and
subtracted from the denominator explicitly.

Does not own intervals -- `ci` on `AgreementResult` is computed by `vernier.estimation`
(cluster bootstrap over `worker_id`) and passed in, never recomputed here.

**Deviation from the frozen stub, flagged for review:** `raw_agreement`, `gwet_ac1`,
`cohens_kappa`, `fleiss_kappa`, and `intra_rater_kappa` each gained a required `task` parameter
appended after their existing arguments. The un-parameterised stubs could not express which of
`HumanLabel`/`JudgeResponse`'s two comparable fields (`hands_visible` for `hand_count`,
`manipulation` for `manipulation`) to compare -- both fields are always populated on an `ok`
response, so nothing in the data itself disambiguates. `build_agreement_result` already carries
`task: str` for exactly this reason; the same parameter had to reach the statistic functions it
calls. All existing positional arguments keep their position, order and type.

**Gwet's AC1, multi-category generalisation:** for two raters and `q` categories,
`pe = 1/(q-1) * sum_j(pi_j * (1 - pi_j))`, where `pi_j` is the *pooled* marginal probability of
category `j` -- the average of both raters' own marginal proportions, not each rater's marginal
used separately (that product is Cohen's kappa's `pe`, and reproducing it is exactly the paradox
this project exists to avoid; PRE-REGISTRATION.md "Why AC1 and not kappa"). `AC1 = (pa - pe) /
(1 - pe)`. This is Gwet's (2008) own generalisation to more than two categories (see also the
`irrCAC` reference implementation's `gwet.ac1.raw`, which uses the identical pooled-marginal
formula): setting `q=2` collapses it to the textbook binary formula `pe = 2*p_bar*(1-p_bar)`
given in this unit's brief, since for two categories `pi_1*(1-pi_1) + pi_2*(1-pi_2) =
2*pi_1*pi_2 = 2*p_bar*(1-p_bar)`. `hand_count` uses `q=3` (categories `{0, 1, 2}`); `manipulation`
uses `q=2` (categories `{False, True}`).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from vernier.models import AgreementCI, AgreementResult, Comparison, HumanLabel, JudgeResponse

# The two tasks CONTRACTS.md's `HumanLabel`/`JudgeResponse` support, and their fixed category
# spaces. Fixed by task, not inferred from the data, so a category absent from a particular
# sample still contributes correctly (as a zero-probability category) to AC1's pooled marginals.
_TASK_CATEGORIES: dict[str, tuple[object, ...]] = {
    "hand_count": (0, 1, 2),
    "manipulation": (False, True),
}

_LABEL_FIELD: dict[str, Callable[[HumanLabel], object]] = {
    "hand_count": lambda label: label.hands_visible,
    "manipulation": lambda label: label.manipulation,
}

_RESPONSE_FIELD: dict[str, Callable[[JudgeResponse], object]] = {
    "hand_count": lambda response: response.hands_visible,
    "manipulation": lambda response: response.manipulation,
}


def _categories(task: str) -> tuple[object, ...]:
    try:
        return _TASK_CATEGORIES[task]
    except KeyError:
        raise ValueError(
            f"unknown task {task!r}; expected one of {sorted(_TASK_CATEGORIES)}"
        ) from None


def _comparable_pairs_with_exclusions(
    labels: list[HumanLabel], responses: list[JudgeResponse], task: str
) -> tuple[list[tuple[object, object]], dict[str, int]]:
    """Match `labels` to `responses` by `frame_id`, and split into comparable pairs vs. exclusions.

    A label whose `frame_id` has no matching response is neither a pair nor an exclusion -- it is
    not a comparison at all, since there is nothing on the other side to compare against. A
    matched response with `status != "ok"` is counted in `excluded_why` by its status and dropped
    from the comparable pairs, per CONTRACTS.md rule 2 ("absence is explicit"): it must be
    excluded, never coerced to a value.
    """
    _categories(task)  # validates task, raising for anything not in the closed set
    label_value = _LABEL_FIELD[task]
    response_value = _RESPONSE_FIELD[task]
    responses_by_frame = {response.frame_id: response for response in responses}

    pairs: list[tuple[object, object]] = []
    excluded_why: dict[str, int] = {}
    for label in labels:
        response = responses_by_frame.get(label.frame_id)
        if response is None:
            continue
        if response.status != "ok":
            excluded_why[response.status] = excluded_why.get(response.status, 0) + 1
            continue
        pairs.append((label_value(label), response_value(response)))
    return pairs, excluded_why


def _comparable_pairs(
    labels: list[HumanLabel], responses: list[JudgeResponse], task: str
) -> list[tuple[object, object]]:
    pairs, _ = _comparable_pairs_with_exclusions(labels, responses, task)
    return pairs


def _marginal_proportions(
    values: Sequence[object], categories: Sequence[object]
) -> dict[object, float]:
    n = len(values)
    return {category: sum(1 for value in values if value == category) / n for category in categories}


def _raw_agreement_from_pairs(pairs: list[tuple[object, object]]) -> float:
    if not pairs:
        raise ValueError("no comparable pairs to compute agreement over")
    agreeing = sum(1 for a, b in pairs if a == b)
    return agreeing / len(pairs)


def _cohens_kappa_from_pairs(
    pairs: list[tuple[object, object]], categories: Sequence[object]
) -> float:
    if not pairs:
        raise ValueError("no comparable pairs to compute kappa over")
    p_a = _raw_agreement_from_pairs(pairs)
    a_marginal = _marginal_proportions([a for a, _ in pairs], categories)
    b_marginal = _marginal_proportions([b for _, b in pairs], categories)
    p_e = sum(a_marginal[c] * b_marginal[c] for c in categories)
    if p_e >= 1.0:
        return 1.0
    return (p_a - p_e) / (1 - p_e)


def _gwet_ac1_from_pairs(
    pairs: list[tuple[object, object]], categories: Sequence[object]
) -> float:
    if not pairs:
        raise ValueError("no comparable pairs to compute AC1 over")
    q = len(categories)
    p_a = _raw_agreement_from_pairs(pairs)
    a_marginal = _marginal_proportions([a for a, _ in pairs], categories)
    b_marginal = _marginal_proportions([b for _, b in pairs], categories)
    pooled = {c: (a_marginal[c] + b_marginal[c]) / 2 for c in categories}
    p_e = sum(pooled[c] * (1 - pooled[c]) for c in categories) / (q - 1)
    if p_e >= 1.0:
        return 1.0
    return (p_a - p_e) / (1 - p_e)


def raw_agreement(labels: list[HumanLabel], responses: list[JudgeResponse], task: str) -> float:
    """Fraction of matched, comparable pairs where judge and human agree, over `task`."""
    return _raw_agreement_from_pairs(_comparable_pairs(labels, responses, task))


def gwet_ac1(labels: list[HumanLabel], responses: list[JudgeResponse], task: str) -> float:
    """Primary agreement statistic (pre-registered; stable at the corpus's 96% prevalence
    where Cohen's kappa is not). See the module docstring for the multi-category formula."""
    pairs = _comparable_pairs(labels, responses, task)
    return _gwet_ac1_from_pairs(pairs, _categories(task))


def cohens_kappa(labels: list[HumanLabel], responses: list[JudgeResponse], task: str) -> float:
    """Reported beside AC1. Never the headline."""
    pairs = _comparable_pairs(labels, responses, task)
    return _cohens_kappa_from_pairs(pairs, _categories(task))


def fleiss_kappa(responses_by_judge: dict[str, list[JudgeResponse]], task: str) -> float:
    """Agreement across the full judge panel.

    Only frames where every judge in `responses_by_judge` produced a `status == "ok"` response
    are included -- classic Fleiss' kappa assumes a fixed number of raters per subject, and a
    non-`ok` response is an exclusion (CONTRACTS.md rule 2), not a vote to drop for that judge
    alone while keeping the subject at a lower rater count.
    """
    categories = _categories(task)
    response_value = _RESPONSE_FIELD[task]
    judges = list(responses_by_judge)
    if len(judges) < 2:
        raise ValueError("fleiss_kappa requires at least two judges")

    ok_values_by_frame: dict[str, dict[str, object]] = {}
    for judge in judges:
        for response in responses_by_judge[judge]:
            if response.status != "ok":
                continue
            ok_values_by_frame.setdefault(response.frame_id, {})[judge] = response_value(response)

    k = len(judges)
    category_index = {category: i for i, category in enumerate(categories)}
    counts: list[list[int]] = []
    for per_judge in ok_values_by_frame.values():
        if len(per_judge) != k:
            continue  # not every judge answered "ok" for this frame -- excluded, not padded
        row = [0] * len(categories)
        for value in per_judge.values():
            row[category_index[value]] += 1
        counts.append(row)

    n = len(counts)
    if n == 0:
        raise ValueError("no frames with an ok response from every judge")

    p_j = [sum(row[j] for row in counts) / (n * k) for j in range(len(categories))]
    p_e_bar = sum(p * p for p in p_j)
    p_i = [(sum(count * count for count in row) - k) / (k * (k - 1)) for row in counts]
    p_bar = sum(p_i) / n
    if p_e_bar >= 1.0:
        return 1.0
    return (p_bar - p_e_bar) / (1 - p_e_bar)


def intra_rater_kappa(primary: list[HumanLabel], retest: list[HumanLabel], task: str) -> float:
    """Primary pass vs. the blind re-label, matched by `frame_id`.

    The pre-registration specifies that re-label as `R100`, at least seven days later. Neither
    held in the data this ships against: D058 redrew the retest from the primary pool, and the
    separation came in at a median of 2.4 hours (`docs/DECISIONS.md` D076). The statistic is the
    same either way; what it licenses is not, and `scripts/wave4_analysis.py` reports the
    measured separation beside it so a reader is not left with the protocol's version.

    Implements Cohen's kappa (the standard two-rater formula), treating the primary pass as one
    rater and the retest pass as the other, matched by `frame_id`. AC1 is also pre-registered for
    intra-rater agreement (PRE-REGISTRATION.md); it is obtained by calling `gwet_ac1`'s
    pair/category machinery the same way this function calls `cohens_kappa`'s -- there is no
    separate `intra_rater_ac1` entry point because this unit's frozen signature list names only
    `intra_rater_kappa`.
    """
    categories = _categories(task)
    label_value = _LABEL_FIELD[task]
    retest_by_frame = {label.frame_id: label for label in retest}
    pairs: list[tuple[object, object]] = []
    for label in primary:
        match = retest_by_frame.get(label.frame_id)
        if match is None:
            continue
        pairs.append((label_value(label), label_value(match)))
    return _cohens_kappa_from_pairs(pairs, categories)


def build_agreement_result(
    comparison_a: str,
    comparison_b: str,
    task: str,
    subset: str,
    labels: list[HumanLabel],
    responses: list[JudgeResponse],
    ci: AgreementCI,
    design_effect: float,
) -> AgreementResult:
    """Assemble one `AgreementResult`. `ci` and `design_effect` are supplied by the caller
    (from `vernier.estimation`), not computed here."""
    pairs, excluded_why = _comparable_pairs_with_exclusions(labels, responses, task)
    return AgreementResult(
        comparison=Comparison(a=comparison_a, b=comparison_b),
        task=task,
        subset=subset,
        n=len(pairs),
        n_excluded=sum(excluded_why.values()),
        excluded_why=excluded_why,
        raw_agreement=raw_agreement(labels, responses, task),
        ac1=gwet_ac1(labels, responses, task),
        kappa=cohens_kappa(labels, responses, task),
        ci=ci,
        design_effect=design_effect,
    )
