# Waves

How work gets produced, reviewed, and integrated — the fan-out → independent-review paradigm,
and what "done" means per wave. This is the missing piece between `docs/ARCHITECTURE.md` (the
module graph), `docs/METHOD.md` (the experiments), and `docs/HANDOFF.md` (the resume point):
none of those three is "how a unit of work gets accepted."

The wave sequence — S (side-track) → 0 (interface freeze) → 1 (18-unit fan-out) → 2
(integration) → 3 (the serial spine) → 4 (training and close-out) — previously lived only in a
planning document outside this repo. It is authoritative here from now on.

## The fan-out → independent-review paradigm

Applies to any wave that fans work out across agents: Wave 1, Wave 2, and a future Wave 4 once
it is unitized. Wave 3 is explicitly exempt — see its section below.

**The loop, per unit:**

1. **Dispatch.** `agentgraph dispatch --node <unit> --tool <claude|codex|opencode> --prompt
   "..."` — one unit, one directory, one test file, per the file-ownership boundaries fixed in
   `docs/DECISIONS.md` D033.
2. **Produce.** The worker writes tests first (this project's standing TDD convention),
   implements against the unit's contract, and runs its own local acceptance gate
   (`pytest`/`mypy` scoped to its own files) before declaring done. This is a cheap gate before
   any review cost is spent at all.
3. **Review.** The worker (or the orchestrating session) dispatches a review pass —
   `agentgraph dispatch --tool opencode` (resolves to `mimo-2.5-free`, confirmed live: free,
   which matters at 18-way scale) — with a **narrow, unit-scoped prompt**: only the diff/new
   files for this unit, its relevant-categories checklist, the review criteria, and the rubric
   template to fill in. Never the whole repo. Never another unit's work. This is where
   context-bloat gets controlled, not cleaned up after the fact.
4. **Verdict.** The reviewer returns a fixed-shape rubric: a score per dimension, an overall
   accept/reject, and up to a handful of severity-tagged findings. Structured, not prose — the
   orchestrator should never need to read a full review transcript to get the verdict.
5. **Gate.** The orchestrator reads *only* the rubric verdict (`agentgraph node log` on the
   review node — the short structured output, not the reviewer's reasoning trace):
   - **ACCEPT** → commit the unit's directory + test file only (one scoped commit per unit),
     `agentgraph checkpoint pass <task> <unit>-reviewed --evidence "<rubric summary>"`.
   - **REJECT** → feed the findings back to the *same* worker — it needs the critique to fix,
     not a fresh context re-deriving everything — for one fix-and-resubmit cycle.
6. **Loop cap: two reject cycles per unit.** A third reject escalates rather than retries again
   — re-review with a stronger model (`--tool claude` instead of `opencode`) for a second
   opinion, or flag the unit to a human. A bounded loop with a defined escalation path is the
   actual engineering here; an unbounded retry is not a loop, it's a hang.
7. **Standing context-bloat rule.** The orchestrator's own context holds only per-unit node
   status (a few bytes) and each unit's final rubric verdict (a small fixed shape) — never a
   full worker diff or a full reviewer transcript, except when escalating a twice-rejected unit.
   Dedupe status polling: don't re-report a unit already known terminal.

**Why a separate tool and model for review, specifically:** a reviewer sharing the producer's
own context is the self-grading failure mode this project hit twice already — `DECISIONS.md`
D031 needed a D032 follow-up specifically because its own fix was checked in the same context
that wrote it, and the first pass missed real gaps a fresh, skeptical check found immediately. A
different tool, running a free model, means every unit gets genuinely independent review at
~zero marginal cost — `claude`/`codex` stay reserved for producing and for escalation, not for
routine first-pass review. This is D032's lesson applied prospectively instead of manually
re-discovered after the fact.

## Wave S — side-track (done)

Acceptance was: every citation opened at its primary source, the specific claim quoted or
refuted, tagged `[V]`/`[S]`/`[REFUTED]`. No review loop — this was research output, folded in
by direct verification rather than a code review. See `docs/SURVEY.md`'s verification pass and
`docs/DECISIONS.md` D030.

## Wave 0 — interface freeze (done)

Acceptance was: `pytest` + `mypy --strict` + fixture generation + `make validate` all green. It
did **not** have an independent-review loop — and needed two manual corrective passes
(`docs/DECISIONS.md` D031, D032) plus a third structural one (D033) to reach the state one
properly-reviewed pass should have reached directly. This is the concrete argument for why
Wave 1 gets the loop from the start rather than as a retrofit.

## Wave 1 — 18-unit fan-out, offline, TDD

| # | Unit | File | # | Unit | File |
|---|---|---|---|---|---|
| 1 | `sampling` — stratified draw | `sampling/draw.py` | 10 | `agreement` — AC1, κ, Fleiss | `agreement/core.py` |
| 2 | `sampling` — reserves, membership persistence | `sampling/membership.py` | 11 | `agreement` — error-dependence estimator | `agreement/dependence.py` |
| 3 | `judges` — base interface, parsing, status | `judges/base.py` | 12 | `estimation` — PPI / PPI++ | `estimation/ppi.py` |
| 4 | `judges` — Gemini adapter | `judges/gemini.py` | 13 | `estimation` — cluster bootstrap, design effect | `estimation/bootstrap.py` |
| 5 | `judges` — Claude adapter | `judges/claude.py` | 14 | `estimation` — participant-count disparity (H8) | `estimation/disparity.py` |
| 6 | `judges` — Qwen3-VL adapter (open) | `judges/qwen3vl.py` | 15 | `calibration` — ECE, reliability, J/ΔJ | `calibration/__init__.py` |
| 7 | `judges` — prompt registry P0a/P0b/P1–P7 | `judges/prompts.py` | 16 | `distil` — linear probe on frozen features | `distil/linear_probe.py` |
| 8 | `labels` — annotation store | `labels/store.py` | 17 | `distil` — abstention cascade + agreement floor | `distil/cascade.py` |
| 9 | `labels` — labelling tool, blind by construction | `labels/tool.py` | 18 | `card` — emitter, "what could not be checked", exit codes | `card/__init__.py` |

Every unit now maps to exactly one file (`docs/DECISIONS.md` D033) — the ownership rule below
is enforceable, not just stated. `distil` rung 2 (`distil/lora.py`, Qwen3-VL LoRA on Modal) has
no Wave 1 unit by design — it needs network/GPU, so it belongs to Wave 4, not an offline wave.
`probe` (Result 2) is deliberately absent from this table — it is kill-gated and belongs to
Wave 4 as well.

**Acceptance (mechanical):** the unit's test file passes offline, no network; `mypy --strict`
clean on the unit's files; no `NotImplementedError` left in its public functions; `git diff
--name-only` touches only its own file(s) plus its test file; every test runs against Wave 0's
committed fixtures, no live data.

**Relevant categories, scoped per unit family** (so review effort — and context — stays narrow
rather than running one giant checklist against everything):
- `judges` (3–7): contract fidelity, never-throws, `cost_usd`/`latency_ms` populated, no read
  path to `labels`.
- `labels` (8–9): the hard isolation invariant (`labels` must never import `vernier.judges`) and
  blind-by-construction ordering.
- `agreement`/`estimation` (10–14): statistical correctness dominates over style — see Eval,
  below.
- `calibration` (15): empty-bin handling (never merged), P7-only scoping.
- `distil` (16–17): rung-1-must-beat-baseline framing; the cascade's `calibrate_threshold` must
  never tune on frames it will later score — **the same train/eval-leak shape D031 fixed for
  the rung-1 sample split, watch for it recurring here.**
- `card` (18): nonzero exit iff verdict is not `VERIFIED`; every claim tied to a `record_ref`.

**Review criteria:** matches the unit's `ARCHITECTURE.md` docstring seam; doesn't reach into
another module's file; docstrings and type hints match `CONTRACTS.md`'s literal invariants — no
looser, and no invented stricter constraint without a validator to actually enforce it (the
project's own stated minimal-validator philosophy).

**Eval criteria** — the gap review 3 named directly ("tests are schema tests, not scientific
tests"): every statistical unit ships at least one synthetic golden-case test with a
hand-computable expected answer — `gwet_ac1` against a known confusion matrix with a textbook
AC1 value, `cluster_bootstrap_ci` against synthetic clustered data with a known design effect,
`ppi_estimate` against synthetic gold+judge data where the unbiased answer is known by
construction. `pytest` passing is not sufficient acceptance for these units on its own.

**Rubric** (1–5 or pass/fail per row, filled in by the review pass):

| Dimension | What it checks |
|---|---|
| Contract fidelity | Matches `CONTRACTS.md`/`ARCHITECTURE.md`, no drift |
| Test quality | Behavioral/golden-case, not schema-only, for statistical units |
| Isolation | No cross-module file reach, no shared-file edits |
| Docstring/type accuracy | Types and docstrings match the stated invariant, not looser or invented-stricter |
| **Overall** | Accept / reject + severity-tagged findings |

## Wave 2 — integration, ~6 agents, network allowed

- Evaluation-parquet adapter, and D016's first check made real: the parquets actually contain
  the frames the published labels refer to.
- Egocentric-10K streaming draw for the sampling-design arm.
- Live judge harness with cost and latency accounting.
- E2 replication runner (`P0a`, `P0b`, both corpus arms).
- E5 prompt-sweep runner with IPR/PAR reporting.
- CI gates and `make validate` end to end.

**Acceptance:** end-to-end run against real evaluation parquets succeeds; D016's check is a real
assertion, not a manual step; `make validate` stays green; no live API key ever appears in a log
or a commit.

**Relevant categories:** live-cost accounting (does the harness actually populate
`JudgeResponse.cost_usd`/`latency_ms` per call — the spend-ledger gap review 2/3 both flagged);
real network-failure handling under an actually-flaky connection, not a stub signature; revision
pinning enforced at draw/call time (`corpus_rev == PINNED_REVISION`), not left in prose only.

**Review criteria:** the opencode/mimo pass here includes *re-running* the reproduction check
against real data, not just reading the diff — Wave 2's gate is empirical, not textual.

**Eval criteria:** the reproduction number itself, actual vs. published, within the ±2pp H1
tolerance already pre-registered.

**Rubric:** Real-data reproduction accuracy | Cost/latency ledger completeness | Revision-pinning
enforcement | Failure-handling realism | Overall accept/reject.

## Wave 3 — the serial spine (no fan-out; the review loop above does not apply)

600 primary labels, one rater, against `RUBRIC.md` v1.2.0 — then a ≥7-day gap — then the blind
`R100` retest. Intra-rater agreement is computed first and gates everything.

**Acceptance:** intra-rater AC1 on `R100` ≥ 0.70 — the existing binding stopping rule; below
it, the rubric becomes the deliverable and the audit defers, exactly as pre-registered.

**Eval:** the retest is genuinely blind — no read path from `labels`'s retest pass to the
primary pass, already an enforced Wave 1 invariant, not just a convention here.

There is no opencode review of the rater's *judgment* — there is no fan-out to review, and the
human's own consistency is the eval. What still applies: a lightweight opencode/mimo
**structural** sanity pass over the aggregated label data before it feeds `agreement` — no
duplicate `frame_id`, no impossible timestamp ordering, pass distribution matches the
pre-registered sample sizes. A data-quality check, not a judgment-quality one.

## Wave 4 — training and close-out (not yet unitized)

Distillation rungs 1 and 2, the cascade's guarantee calibration, the Result-2 kill-gate spike,
the probe if it opens, the card, and the self-audit that turns every instrument on vernier's own
claims.

**Acceptance per deliverable:** rung 1 must beat its stated baseline before rung 2 is attempted
(already the project's rule); the cascade's coverage-at-floor guarantee is calibrated on
held-out data disjoint from whatever tuned its threshold — **the same train/eval-leak shape
D031 fixed for rung 1's sample split, checked explicitly here since this is the next place it
could recur**; the kill-gate spike's outcome (open or killed) is recorded either way, never
silently dropped; the final card exits nonzero on any non-`VERIFIED` claim.

**Relevant categories:** the train/eval-leak category, specifically, given the precedent.

**Review criteria + rubric:** the same shape as Wave 1's, once Wave 4 is actually broken into
units — that unitization is future work, out of scope here.
