# Handoff

The resume point. A fresh session should be able to continue from this file without
re-deriving anything.

**Last updated: 2026-08-31, after the survey gate and the paper verification pass.**

## Where this stands

**Documentation complete. Survey gate passed. No code, no experiments, no judge called.**

`SURVEY.md` returned **PROCEED, narrowed**: the contribution is H5 (cross-corpus judge
confound) plus judge-as-instrument, not judge validation, which is prior-arted. The survey also
caught four methodological errors in `PRE-REGISTRATION.md` v1.1.0, all fixed in v1.2.0 —
PPI over cluster-bootstrap-alone, Gwet's AC1 over Cohen's κ, balanced gold for H5's
interaction, and H8. Catching those is what the gate was for.

A direct read of Build AI's published artifacts produced eleven findings, several of which
corrected this repository's own earlier claims. See `UPSTREAM-FINDINGS.md`.

The repository was created in one session from a scoping investigation of Build AI
(build.ai) and a decision to open a research collaboration by publishing an independent
measurement rather than by making an approach. The full context, including the outreach
sequencing, is in `docs/private/OUTREACH.md`, which is gitignored and never influences a
finding.

## What exists

| | |
|---|---|
| Root | `README.md`, `CONTRACTS.md`, `AGENTS.md`, `Makefile`, `llms.txt`, `pyproject.toml` skeleton, `.env.example`, `.gitignore`, `LICENSE` |
| Protocol | `PRE-REGISTRATION.md` (rev 1.3.0, **frozen by commit**), `RUBRIC.md` (rev 1.1.0), `METHOD.md` |
| Framing | `README.md`, `methodology.md`, `LINEAGE.md`, `COVERAGE.md`, `ETHICS.md` |
| Self-criticism | `RED-TEAM.md`, fourteen attacks, opened before any result |
| Design | `ARCHITECTURE.md`, `CONTRACTS.md` |
| Output shape | `DATASET_CARD.md`, `MODEL_CARD.md`, `EVALS_CARD.md`, `BENCHMARK.md`, all deliberately unfilled |
| Reproducibility contract | `REPRODUCTION.md` |
| Survey | `SURVEY.md`, **complete**, verdict PROCEED-narrowed |
| Upstream facts | `UPSTREAM-FINDINGS.md`, F1–F11, with pinned snapshots in `docs/upstream/` |
| Decisions | `DECISIONS.md`, D001–D029 |
| Private | `docs/private/`, gitignored: outreach, country brief, email draft |

## The next three actions, in order

1. ~~Open LIME.~~ **Done — refuted (D029).** ~~Freeze the pre-registration.~~ **Done.**
2. **Wave S**, which blocks nothing and starts immediately: full audit of every remaining
   citation, the two unresolved figures (EgoSafetyBench's agreement value, Miller's clustered-SE
   figure — full text or dropped), H8's participant counts confirmed against primary
   documentation, and the Ego4D / EPIC licence terms on frame redistribution.
3. **Wave 0**, the interface freeze, which gates everything else: pydantic models from
   `CONTRACTS.md`, typed stubs for the nine `ARCHITECTURE.md` modules, and a fixture generator
   so Wave 1 runs entirely offline.

Then Wave 1: eighteen units, one directory and one test file each, TDD against fixtures.

## Open questions

- **LIME (2607.02417), unopened.** Action 1 above.
- **The five other items in `SURVEY.md` "must be closed before publication"** — EgoSafetyBench's
  agreement value, EPIC-KITCHENS-100's unverified-absence of an IAA figure, the Ego4D and
  EPIC licence terms on frame redistribution, two refused figures, and two unconfirmed author
  attributions.
- **Participant counts for H8** are secondary-sourced and must be confirmed.
- **EPIC-KITCHENS-100 registration requires an institutional email**, which an unaffiliated
  researcher does not have. A Result-2 risk, not a Result-1 blocker.
- **Whether the evaluation parquets contain the frames the published labels refer to.** The
  first thing `make sample` verifies (D016).

Settled since the last update: there is no public `builddotai/Egocentric-1M` (404), so no
public release could make the MPJPE guarantee checkable; and Ego4D/EPIC access is off Result
1's critical path because their frames ship inside the evaluation release.

## What must not drift

- The rater never sees judge output. Enforced in `labels`, not by discipline.
- No agreement statistic is computed before all 600 primary labels exist.
- Intra-rater agreement on `R100` below 0.70 defers the audit and makes the rubric the
  deliverable.
- AC1 is primary, κ is secondary, PPI is the headline estimator — all decided before data.
- Intervals cluster over `worker_id` wherever a grouping variable exists, and say so plainly
  where it does not.
- `make privacy-gate` passes before any commit.
