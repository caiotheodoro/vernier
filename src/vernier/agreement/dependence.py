"""Judge-error-dependence: whether the panel's errors correlate.

A panel with correlated errors buys less than N independent opinions -- this is what makes the
three-judge panel's agreement an upper bound rather than a guarantee (`docs/RED-TEAM.md` A3).
"""

from __future__ import annotations

import itertools
import math

from vernier.models import HumanLabel, JudgeResponse


def judge_error_dependence(
    responses_by_judge: dict[str, list[JudgeResponse]], gold: list[HumanLabel]
) -> float:
    """Whether the panel's errors correlate -- a panel with correlated errors buys less than
    N independent opinions.

    **Design choice, not a pre-registered formula.** `PRE-REGISTRATION.md` names the concept
    ("an explicit judge-error-dependence estimate") but pins no statistic; the operationalization
    below is this function's own and should be read and cited as such.

    Per judge, per frame: build a binary "was this judge wrong on the `manipulation` task"
    indicator, comparing `JudgeResponse.manipulation` against `HumanLabel.manipulation` on the
    primary human pass, matched by `frame_id`. `JudgeResponse`s with `status != "ok"` are
    dropped before the comparison (CONTRACTS.md rule 2, "absence is explicit") -- a refusal or
    timeout is neither a correct nor an incorrect answer, so counting it as either would bias
    the indicator, not just shrink its denominator.

    For each pair of judges, the two indicator series (restricted to frames both judges have an
    "ok" response for) form a 2x2 contingency table, and the phi coefficient -- equivalently the
    Matthews correlation coefficient, and equivalently Pearson's r computed on the two binary
    series -- is computed from it:

        phi = (n11*n00 - n10*n01) / sqrt((n11+n10)(n01+n00)(n11+n01)(n10+n00))

    where n11/n00 count frames both judges got wrong/right and n10/n01 count frames exactly one
    did. phi = 1 means the two judges are wrong on exactly the same frames (their errors carry
    no information beyond one judge's); phi = 0 means their errors are as correlated as chance;
    phi = -1 means their errors are perfectly anti-correlated (one is wrong exactly where the
    other is right). This is a reasonable operationalization of "do panel errors correlate"
    because it is the standard correlation coefficient for two binary variables, and correlated
    binary error indicators are exactly what A3 (`docs/RED-TEAM.md`) warns inflates panel
    agreement statistics like Fleiss' kappa.

    The single returned float is the mean phi coefficient across all judge pairs -- a simple
    aggregate that reads as "how much, on average, does one judge's error tell you about
    another's" across the whole panel. When a pair has no frames in common, or one judge has
    zero variance in its error indicator across the common frames (always right or always wrong,
    making phi's denominator zero), that pair contributes phi = 0 -- treated as no evidence of
    dependence rather than an undefined value distorting the mean. A panel with fewer than two
    judges, or with no comparable pairs at all, returns 0.0 for the same reason.
    """
    gold_by_frame = {label.frame_id: label for label in gold if label.pass_ == "primary"}

    error_by_judge: dict[str, dict[str, bool]] = {}
    for judge, responses in responses_by_judge.items():
        errors: dict[str, bool] = {}
        for response in responses:
            if response.status != "ok":
                continue
            matched_gold = gold_by_frame.get(response.frame_id)
            if matched_gold is None:
                continue
            errors[response.frame_id] = response.manipulation != matched_gold.manipulation
        error_by_judge[judge] = errors

    phi_coefficients: list[float] = []
    for judge_a, judge_b in itertools.combinations(sorted(error_by_judge), 2):
        errors_a = error_by_judge[judge_a]
        errors_b = error_by_judge[judge_b]
        common_frames = errors_a.keys() & errors_b.keys()
        if not common_frames:
            continue

        n11 = n10 = n01 = n00 = 0
        for frame_id in common_frames:
            wrong_a = errors_a[frame_id]
            wrong_b = errors_b[frame_id]
            if wrong_a and wrong_b:
                n11 += 1
            elif wrong_a and not wrong_b:
                n10 += 1
            elif not wrong_a and wrong_b:
                n01 += 1
            else:
                n00 += 1

        denominator = math.sqrt((n11 + n10) * (n01 + n00) * (n11 + n01) * (n10 + n00))
        phi = 0.0 if denominator == 0 else (n11 * n00 - n10 * n01) / denominator
        phi_coefficients.append(phi)

    if not phi_coefficients:
        return 0.0
    return sum(phi_coefficients) / len(phi_coefficients)
