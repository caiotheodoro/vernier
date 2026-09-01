"""H5 / R100 power and precision simulation, run once before Wave 3 commits any labelling time.

Two independent questions, both Monte Carlo because neither pre-registered quantity (H5's
domain-bias interaction, R100's intra-rater AC1) has a closed-form power formula anyone would
trust without checking it against simulation first:

1. **H5** (`PRE-REGISTRATION.md` line 197): does n=200/arm (the balanced gold sets, D023) have
   adequate power to detect the pre-registered >=5pp domain-bias effect on the manipulation
   task, across a grid of plausible baseline judge-error rates (the true rate is unknown until
   Wave 3 produces labels)?
2. **R100** (line 226): does n=100 give the pre-registered 0.70 intra-rater AC1 stopping rule
   enough precision that a rater near the boundary isn't essentially coin-flipping into
   "proceed" or "defer" by sampling noise alone?

This is a planning tool, not `agreement.core.gwet_ac1` (Wave 1 unit 10, still
`NotImplementedError`) -- it implements Gwet's AC1 for the binary two-rater case independently,
here only, so this simulation doesn't depend on unwritten Wave-1 code. Wave 1's own
implementation is checked against a textbook golden case, per `docs/WAVES.md`'s eval criteria,
not against this script.

Findings recorded in `docs/DECISIONS.md` regardless of outcome, per `AGENTS.md` rule 1: this
script does not itself change `PRE-REGISTRATION.md`'s frozen sample sizes even if it finds them
underpowered -- that would need its own dated amendment decision.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass

import numpy as np
from scipy import stats


def _gwet_ac1_binary(po: float, p_bar: float) -> float:
    """Gwet's AC1 for two raters, one binary category, given observed agreement `po` and the
    pooled marginal "positive" rate `p_bar` (average of both raters' positive-rate).

    `pe = 2 * p_bar * (1 - p_bar)` is the AC1 chance-agreement term -- built from the *pooled*
    marginal rather than each rater's own marginal, which is exactly what keeps it stable at
    high prevalence where Cohen's kappa is not (`SURVEY.md` Track 3, `PRE-REGISTRATION.md`
    line 122).
    """
    pe = 2.0 * p_bar * (1.0 - p_bar)
    if pe >= 1.0:
        return 1.0 if po >= 1.0 else 0.0
    return (po - pe) / (1.0 - pe)


@dataclass(frozen=True)
class H5PowerResult:
    baseline_error_rate: float
    power: float


def simulate_h5_power(
    baseline_error_rates: list[float],
    *,
    effect_pp: float = 0.05,
    n_per_arm: int = 200,
    alpha: float = 0.05,
    n_sims: int = 5000,
    seed: int = 777,
) -> list[H5PowerResult]:
    """Empirical power of a two-proportion z-test to detect `effect_pp` at each baseline rate.

    Models H5's estimand directly: two independent n=`n_per_arm` binary (judge-correct /
    judge-error) samples on the manipulation task, one per domain, with a true difference of
    `effect_pp`. `judge_error ~ domain x task`'s cluster-robust logistic form
    (`PRE-REGISTRATION.md` line 119) reduces to this two-proportion comparison when, as here,
    clustering is unavailable on the evaluation arms (F9) -- the gold sets are iid draws.
    """
    rng = np.random.default_rng(seed)
    z_crit = float(stats.norm.ppf(1.0 - alpha / 2.0))
    results = []
    for p0 in baseline_error_rates:
        p1 = min(p0 + effect_pp, 1.0)
        successes = 0
        for _ in range(n_sims):
            a = rng.binomial(n_per_arm, p0)
            b = rng.binomial(n_per_arm, p1)
            pa, pb = a / n_per_arm, b / n_per_arm
            pooled = (a + b) / (2 * n_per_arm)
            se = np.sqrt(pooled * (1 - pooled) * (2 / n_per_arm))
            if se == 0:
                continue
            z = abs(pa - pb) / se
            if z > z_crit:
                successes += 1
        results.append(H5PowerResult(p0, successes / n_sims))
    return results


@dataclass(frozen=True)
class R100PrecisionResult:
    true_ac1: float
    prevalence: float
    p_measured_ge_070: float
    mean_measured_ac1: float


def _expected_ac1_for_match_rate(po: float, prevalence: float) -> float:
    """Closed-form expected AC1 under the flip generative model, as a function of the match
    probability `po` (see `simulate_r100_precision`). Flipping asymmetrically shifts the
    retest marginal away from `prevalence` (toward 0.5 as `po` falls), which in turn moves the
    pooled `p_bar` and hence `pe` -- this dependency is exactly what an earlier version of this
    function got wrong by assuming `p_bar` stays fixed at `prevalence`. Monotonic increasing in
    `po` over [0, 1] (AC1(0) = -1, AC1(1) = 1), so `_solve_match_rate_for_ac1` can bisect it.
    """
    retest_mean = po * prevalence + (1.0 - po) * (1.0 - prevalence)
    p_bar = (prevalence + retest_mean) / 2.0
    pe = 2.0 * p_bar * (1.0 - p_bar)
    if pe >= 1.0:
        return 1.0
    return (po - pe) / (1.0 - pe)


def _solve_match_rate_for_ac1(target_ac1: float, prevalence: float) -> float:
    """Bisect for the `po` (match probability) whose expected AC1 equals `target_ac1`."""
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        if _expected_ac1_for_match_rate(mid, prevalence) < target_ac1:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2.0


def simulate_r100_precision(
    true_ac1_targets: list[float],
    *,
    prevalence: float = 0.90,
    n: int = 100,
    n_sims: int = 5000,
    seed: int = 777,
    threshold: float = 0.70,
) -> list[R100PrecisionResult]:
    """For each target "true" intra-rater AC1, simulate n=`n` paired primary/retest labels and
    report how often the *measured* AC1 clears the pre-registered 0.70 gate.

    Generative model: primary label ~ Bernoulli(`prevalence`); the retest label matches the
    primary with probability `po`, else flips. `po` is solved (`_solve_match_rate_for_ac1`) so
    the *expected* AC1 under this exact generative process equals the target -- verified against
    a large-`n` sanity run (the empirical mean measured AC1 converges to the target as `n` grows;
    see `tests/test_power_simulation.py`). `prevalence` = 0.90 is an assumption, stated here
    rather than measured -- Build AI's own published proportions run 76-96% positive
    (`docs/HANDOFF.md`), so a high-prevalence label distribution is the realistic planning case,
    not the only possible one; this is exactly the H8/H5-style "state the assumption" this
    project's own instruments demand of everything else.
    """
    rng = np.random.default_rng(seed)
    results = []
    for target_ac1 in true_ac1_targets:
        po = _solve_match_rate_for_ac1(target_ac1, prevalence)
        measured = np.empty(n_sims)
        for i in range(n_sims):
            primary = rng.binomial(1, prevalence, size=n)
            matches = rng.binomial(1, po, size=n).astype(bool)
            retest = np.where(matches, primary, 1 - primary)
            observed_po = float(np.mean(primary == retest))
            p_bar = float((primary.mean() + retest.mean()) / 2.0)
            measured[i] = _gwet_ac1_binary(observed_po, p_bar)
        results.append(
            R100PrecisionResult(
                true_ac1=target_ac1,
                prevalence=prevalence,
                p_measured_ge_070=float(np.mean(measured >= threshold)),
                mean_measured_ac1=float(np.mean(measured)),
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-sims", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON instead of a table")
    args = parser.parse_args()

    h5 = simulate_h5_power(
        baseline_error_rates=[0.05, 0.10, 0.15, 0.20, 0.25, 0.30],
        n_sims=args.n_sims,
        seed=args.seed,
    )
    r100 = simulate_r100_precision(
        true_ac1_targets=[0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90],
        n_sims=args.n_sims,
        seed=args.seed,
    )

    if args.json:
        print(
            json.dumps(
                {
                    "h5_power": [r.__dict__ for r in h5],
                    "r100_precision": [r.__dict__ for r in r100],
                },
                indent=2,
            )
        )
        return

    print("H5 power: two-proportion test, n=200/arm, effect=5pp, alpha=0.05")
    print(f"{'baseline error rate':>22} | {'power':>8}")
    for h5_row in h5:
        print(f"{h5_row.baseline_error_rate:>22.2f} | {h5_row.power:>8.3f}")

    print()
    print("R100 precision: n=100, threshold=AC1>=0.70, prevalence=0.90 (assumption)")
    print(f"{'true AC1':>10} | {'P(measured>=0.70)':>18} | {'mean measured AC1':>18}")
    for r100_row in r100:
        print(
            f"{r100_row.true_ac1:>10.2f} | {r100_row.p_measured_ge_070:>18.3f} | "
            f"{r100_row.mean_measured_ac1:>18.3f}"
        )


if __name__ == "__main__":
    main()
