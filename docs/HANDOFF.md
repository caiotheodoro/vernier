# Handoff

The resume point. A fresh session should be able to continue from this file without
re-deriving anything.

**Last updated: 2026-09-01, after Wave S, Wave 0, a two-pass refinement audit (D031, D032), and
a file-ownership fix that makes Wave 1 actually dispatchable (D033, `WAVES.md`).**

## Where this stands

**Documentation and interface freeze complete and committed. Survey gate passed. Wave S and
Wave 0 done, Wave 1 dispatch-ready. No experiments, no judge called, no code beyond typed stubs
and contract models.**

`SURVEY.md` returned **PROCEED, narrowed**: the contribution is H5 (cross-corpus judge
confound) plus judge-as-instrument, not judge validation, which is prior-arted. The survey also
caught four methodological errors in `PRE-REGISTRATION.md` v1.1.0, all fixed in v1.2.0 —
PPI over cluster-bootstrap-alone, Gwet's AC1 over Cohen's κ, balanced gold for H5's
interaction, and H8. Catching those is what the gate was for.

**Wave S (8 dispatched audit workers, `agentgraph dispatch`) closed all six remaining "must be
closed before publication" items and caught three further mis-citations**: D021's PPI citation
was wrong (2408.15204 is Confidence-Driven Inference, not PPI — the real PPI paper is 2301.09633),
D024's EPIC-KITCHENS-100 participant count was wrong (37, not ~45 — that was the kitchen count),
and a working-table citation (2503.05965) claimed to support H3 but does not. See `DECISIONS.md`
D030 for the full record. **Wave 0 landed, its gate passed, and it is committed** (`ea75148`):
pydantic models for every `CONTRACTS.md` record, typed stubs for the nine `ARCHITECTURE.md`
units, pytest (43 passed), mypy --strict (clean), and a fixture generator (14 valid + 19
malformed/refused cases) — `make validate` green end to end.

**Three independent AI audit reviews (`docs/private/reviews.txt`) were then cross-checked
against the actual repo in two passes, not trusted from their prose** — a distillation
train/eval leak, a `FrameRef`/evaluation-frame contract contradiction, a clustering
self-contradiction, a mislabelled "effective N," and several validator gaps were all confirmed
live and fixed (`DECISIONS.md` D031). A second, independent re-audit of that fix then caught
what D031 missed — an incomplete `AgreementCI` validator, an untouched sibling gap in
`PPIBlock.cluster_by`, the H8 relabel not reaching the `estimation` module's own identifiers,
and this file's own stale test/fixture counts and "uncommitted" claim (`DECISIONS.md` D032).
The lesson, consistent with this project's own methodology: a self-audit's first pass is not
the last word — verify the fix the same way you verified the original claim.

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
| Protocol | `PRE-REGISTRATION.md` (rev 1.3.0, **frozen by commit**), `RUBRIC.md` (rev 1.2.0), `METHOD.md` |
| Framing | `README.md`, `methodology.md`, `LINEAGE.md`, `COVERAGE.md`, `ETHICS.md` |
| Self-criticism | `RED-TEAM.md`, fourteen attacks, opened before any result |
| Design | `ARCHITECTURE.md`, `CONTRACTS.md` |
| Output shape | `DATASET_CARD.md`, `MODEL_CARD.md`, `EVALS_CARD.md`, `BENCHMARK.md`, all deliberately unfilled |
| Reproducibility contract | `REPRODUCTION.md` |
| Survey | `SURVEY.md`, **complete**, verdict PROCEED-narrowed |
| Upstream facts | `UPSTREAM-FINDINGS.md`, F1–F11, with pinned snapshots in `docs/upstream/` |
| Decisions | `DECISIONS.md`, D001–D033 |
| Private | `docs/private/`, gitignored: outreach, country brief, email draft, self-audit log |
| Interface | `src/vernier/` — pydantic models (`models.py`) + eighteen Wave-1-ready unit files, `tests/fixtures/` — **committed**, `496e514` |
| Waves | `WAVES.md` — the fan-out → independent-review paradigm and every wave's acceptance/review/eval/rubric criteria |

## The next action

**Wave 1 is dispatch-ready but not yet dispatched** — a separate decision from this resume.
`WAVES.md` has the corrected 18-unit table (every unit now maps to exactly one file,
`DECISIONS.md` D033) and the full fan-out → independent-review loop each unit runs through
before its work is trusted or committed. Read `WAVES.md` before dispatching, not just this file.

The P1 tier from `DECISIONS.md` D031/D032 (CI, pre-commit privacy-gate hook,
`scripts/check_eval_parquets.py`, HF-revision assertion in `sampling`, H5/R100 power
simulation, rubric pilot, backbone pin, honest — not no-op — `Makefile` experiment targets) is
also still open and arguably belongs before Wave 1, not after.

## Open questions

- **Item 5 of `SURVEY.md`'s "must be closed" list is the one still open**: the "16.8 pp
  prevalence spread" and "19%→54% neutral" figures remain unsourced after an extensive Wave S
  search. Drop them entirely if nothing surfaces by publication. All five other items closed —
  see `SURVEY.md`'s verification pass and `DECISIONS.md` D030.
- **EPIC-KITCHENS-100 registration requires an institutional email**, which an unaffiliated
  researcher does not have. A Result-2 risk, not a Result-1 blocker.
- **Ego4D frame redistribution is licence-restricted** to research/academic-publication
  contexts (Wave S, `SURVEY.md`); consistent with `ETHICS.md`'s existing no-republish policy,
  now with a concrete legal basis.
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
