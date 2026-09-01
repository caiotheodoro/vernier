# Review — where the project stands, and what to add

**Dated 2026-09-01.** A read of every document in `docs/`, `MEASUREMENT_CARD.json`,
`DECISIONS.md` D035–D046 and the untracked `scripts/generate_rung1_labels.py`, through the
post-training lens the project itself uses: eval ladder → reward type → data → train →
checkpoint → production. Nothing here is implemented. Every proposal names the document it
would change and what would reverse it, in the repository's own convention.

This file is a review, not a finding. It carries no experimental number.

## Verdict

**The protocol is strong. The object of study changed under it (D042) and the documents did
not follow.** The single most valuable action is not a new experiment; it is absorbing D042's
consequences — which, read carefully, make the project *stronger* than the current framing
admits, because the original judge's labels are already in hand.

## What is strong, and why it matters

Most solo research repositories have none of these. This one has all of them, before any
result exists:

- **Pre-registration frozen by commit before `src/`** (`PRE-REGISTRATION.md` 1.3.0), with three
  pre-freeze revisions each driven by a primary source, and a binding rule that any later change
  is a `DECISIONS.md` entry with the prior number recorded.
- **A survey that refuted its own citations.** LIME, the PPI mis-cite, and 2503.05965 were all
  caught by opening the source (`SURVEY.md`, verification pass). The `[V]`/`[S]` tagging did its
  job on the project's own claims.
- **Statistics chosen for the actual regime.** PPI over cluster-bootstrap-alone (D021), Gwet's
  AC1 over κ at 96% prevalence (D022), balanced gold because H5 is an interaction (D023),
  Holm–Bonferroni declared over a named family. These are the choices a careful referee would
  demand, made before data.
- **Power computed and published as bad news** (D035). H5 is underpowered and the R100 gate is a
  coin flip at the boundary; the sizes stayed frozen and the limitation is on the record.
- **A card that exits nonzero** with a named blocker per unmet hypothesis
  (`MEASUREMENT_CARD.json`, `verdict=NOT_VERIFIED`). This is the rarest artefact in the list.
- **Train/eval leak caught twice** before any training ran (D031; `WAVES.md` rung-3 warning).
- **Real bugs found only by real calls**, and recorded as a pattern (D043, D044, D045, D046).
  The lesson in D046 — tests shaped like existing tests share their gaps — is the correct one.
- **Self-audit as a first-class step** (`RED-TEAM.md` opened pre-result; E10 the "least
  skippable item"; A14's fairness test for reporting a vendor's commit log).

Against the post-training iron laws: evals before training (yes — human gold is the frozen
held-out set, and nothing trains before it exists); verifiable reward over judged reward (not
applicable — the domain forces a human oracle, and `methodology.md` prices that cost
honestly); report a profile not a number (yes — per class, per task, per domain, with the
constant-answer baseline demanded by A8); production failures become evals (the instrument
framing in `MODEL_CARD.md` is exactly this).

## The structural hole: D042 changed the study and the documents did not follow

D042 records that `gemini-2.5-flash` is unreachable for a new key and that the panel is now one
self-hosted judge, `Qwen/Qwen3-VL-8B-Instruct-FP8`. That decision is sound. Four of its
consequences are not yet absorbed.

### 1. The distillation teacher is now the wrong one

`MODEL_CARD.md`, `METHOD.md` E7 and `ARCHITECTURE.md` `distil` all say: train on the judge's
labels so the instrument reproduces *the judge* including its errors, because an instrument that
improved on the thing it measures would stop measuring it (D007).

The untracked `scripts/generate_rung1_labels.py` instead calls Qwen3-VL over `E10k-ego \
G200-ego` to *produce* training labels. But the judge that produced the published number
already labelled every one of those frames, and the labels ship in the parquets:
`hand_count` and `active_labor`, per frame, for all three corpora (`UPSTREAM-FINDINGS.md` F9;
verified live to match the card's figures to two decimals, D040/D042). **Those columns are the
published measurement.** Training on Qwen labels distils a substitute judge that nobody's
claim rests on. Rung 2 as written — a Qwen3-VL LoRA fitted to Qwen3-VL-8B's own labels — is
self-distillation and adds nothing.

### 2. The panel is two judges, not one — and one of them is the real target

F9 already states it: human gold can be compared to the exact published labels without
re-calling any judge. So for E4 (agreement), E6 (domain bias) and the error-inheritance
diagnostic, the frozen gemini labels are a full judge arm — the *only* arm that speaks to the
published claim — and Qwen3-VL is the live comparison judge. The card's blockers for H4 and H5
are correct (they need human labels) but the prose everywhere frames the study as
single-judge. Judge–judge agreement on all 10,000 `E10k-ego` frames, and D025's
error-dependence estimate on the 600 gold frames, come at no extra cost.

### 3. Calibration under the published protocol is measurable for the open judge

H7 and F8 say calibration cannot be measured under P0 because the response schema exposes no
confidence. That was true of the closed APIs. The open judge exposes the answer-token logprob
under the bare-value format, and `HANDOFF.md` records this working live. Calibration of *a*
judge under the *published* prompt is a real result; "P7 only" is a leftover of the
closed-API design. The pre-registered claim about Build AI's measurement stays as written —
their judge exposed nothing — but the "what could not be checked" entry should narrow.

### 4. Stale prose

`AGENTS.md` rule 2 says prose carrying a number the pipeline no longer produces is a bug. The
same applies to prose carrying a *design* the project no longer has. As of this review:

| File | Says | True since |
|---|---|---|
| `README.md` status block | "No judge has been called, no label written" | Live judge calls exist at n=100 (`HANDOFF.md`) |
| `AGENTS.md` | "Current state: documentation only" | Wave 1 and most of Wave 2 are committed |
| `PRE-REGISTRATION.md` judge panel table | Three judges, gemini as replication target | D042 |
| `METHOD.md` E2, E4, E5, E7, E8 | Gemini and Claude arms, frontier-call costs | D042 |
| `EVALS_CARD.md` | "`gemini-2.5-flash` P0 over S10k", "all three judges" | D042, D044 |
| `REPRODUCTION.md` | "Two of the three judges are closed APIs", `JUDGES=gemini-2.5-flash,claude,qwen3-vl` | D042 |
| `RED-TEAM.md` A3, A11 | Three-judge panel | D042 |
| `RED-TEAM.md` A7 | Judge version drift as a risk | It happened; the entry should say so |
| `ARCHITECTURE.md` `judges` | "Closed models (Gemini, Claude) and the open model" | D042 |
| `BENCHMARK.md` R1 | Replication headers assume the original judge | D042 redefined H1 |
| `RUBRIC.md` Task 1 rule 3 | "which is why P4 exists" for gloves | P3 is gloves; P4 is reflections (`PRE-REGISTRATION.md`) |
| `RED-TEAM.md` A4 | "Eight variants × three figures is 21" | Seven variants |

`PRE-REGISTRATION.md` is frozen and should not be rewritten. It should carry an *Amendments*
section that points at D042 and at whatever entry absorbs this review, so a reader of the
frozen document is not misled about the panel.

## The second weakness: the decisive experiment is thin, and the oracle is one person

Both are already on the record (`RED-TEAM.md` A1, A9; D035). What is missing is action
proportional to how cheap the remedies are. H5 is the headline contribution per D020 and
`SURVEY.md`; by the project's own simulation it cannot reliably detect the effect it is
designed to find. A1 is "unmitigated" when the mitigation costs someone else about half an
hour.

## Research additions

Ranked by value per hour. Each names the documents it touches. None is a change to a frozen
number without a `DECISIONS.md` entry, and every one is pre-data — no human label exists, so
these are amendments of the kind the pre-registration explicitly allows, not post-hoc changes.

### R1 — Retarget the distillation teacher to the stored gemini labels

**What.** Rung 1 trains on Build AI's own per-frame `hand_count`/`active_labor` over all three
evaluation arms minus the three `G200-*` sets — roughly 29,400 frames, three domains, zero
judge spend. Qwen3-VL becomes the comparison judge in E4/E6, not the teacher. Rung 2 either
targets the same labels or is dropped; a LoRA of Qwen on Qwen's own labels is not a rung.

**Why.** Restores the design's stated purpose — reproduce *the* judge behind the published
number — which D042 accidentally severed. Also makes the instrument cross-domain by
construction, so "does it inherit the judge's *domain-specific* errors" becomes testable.

**Touches.** `MODEL_CARD.md` (targets row), `METHOD.md` E7, `ARCHITECTURE.md` `distil`,
`WAVES.md` Wave 4, `scripts/generate_rung1_labels.py` (read the parquet columns instead of
calling the judge; keep the live path as an explicit comparison-arm option).

**Reverses if.** The stored labels turn out not to be gemini's output — D040/D042's live
cross-check says they match the published figures exactly, so this is unlikely, but it is the
assumption.

### R2 — A pseudo-cluster design effect on Build AI's own frames

**What.** Embed every `E10k-*` frame with the pinned DINOv3 backbone (D034), cluster by
embedding similarity (near-duplicate threshold plus agglomerative clustering), and run the
cluster bootstrap over the pseudo-clusters. Report beside the iid interval, labelled
**exploratory** and **a proxy**, with the clustering threshold swept so the design effect is a
curve, not a number. The same embeddings yield the near-duplicate rate `COVERAGE.md` lists as
untested.

**Why.** A13 is the sharpest attack in `RED-TEAM.md`: H2 is measured somewhere other than where
it is claimed, and H2 is now *blocked* entirely (D044, gated corpus). A pseudo-cluster estimate
on their actual sample is the only route to any statement about the published figure's true
width, and it is laptop-runnable.

**Touches.** `COVERAGE.md` (two rows), `RED-TEAM.md` A13 (partial answer), `BENCHMARK.md` R1
(a labelled exploratory column), `METHOD.md` (new E4b). Not `PRE-REGISTRATION.md`: this is
exploratory by construction and must be labelled so in those words.

**Reverses if.** Access to the raw corpus is granted and `S10k-U`/`S10k-S` become drawable —
then the real design effect supersedes the proxy, and the proxy is reported as a validation of
the method rather than as the result.

### R3 — A second rater on `R100`

**What.** One other person labels the 100 `R100` frames once, blind, against `RUBRIC.md`
1.2.0, using the existing tool (`make human-labels RATER=<name>`). Inter-rater AC1 and κ are
reported beside the intra-rater figures.

**Why.** A1 is the first weakness on the front page and it is "unmitigated". At the rubric's
own timing estimate this is about 35 minutes of someone else's time. `REPRODUCTION.md` already
says a re-labeller should be treated as a collaborator; this makes it happen before
publication rather than hoping for it after.

**Touches.** `RED-TEAM.md` A1 (status), `METHOD.md` E3, `PRE-REGISTRATION.md` amendments
pointer, `DECISIONS.md`. The 0.70 intra-rater gate stays as written.

**Reverses if.** No second rater is available. Then A1 stays unmitigated and says so.

### R4 — Judge test–retest

**What.** For a fixed set of frames (the 600 gold frames is the natural choice), call the live
judge N times per frame under P0 with the deployment's real settings, and report judge
self-agreement per task, plus the vLLM version, seed, temperature, `max_model_len`, batch
size and image preprocessing recorded as part of `judge_rev`.

**Why.** The project measures a human's self-consistency (`R100`) and has no analogue for the
machine. Post-training iron law 8: a served model at temperature 0 is not deterministic across
batch compositions without batch-invariant inference. A judge whose own test–retest is below
the human's cannot be the instrument. This is a few dollars at the observed per-call cost
(`HANDOFF.md`).

**Touches.** `METHOD.md` (E4 sub-item), `ARCHITECTURE.md` `judges` (what `judge_rev` must
carry), `COVERAGE.md`, `RED-TEAM.md` (new entry: sampler non-determinism).

**Reverses if.** Nothing. It is a diagnostic every judge arm should carry.

### R5 — Contamination as a confound on H5

**What.** EPIC-KITCHENS-100 and Ego4D are public, widely used in vision-language pretraining
and instruction mixes; Egocentric-10K was released in November 2025 and is contact-gated. The
open judge has plausibly *seen* two of the three compared domains and not the third. Record
this as `RED-TEAM.md` A15 and a `COVERAGE.md` row. Cheap probe: ask the judge, per frame, to
name the source dataset, and report accuracy per corpus as a memorisation signal. Also note
that the same question is unanswerable for the stored gemini labels, and say so.

**Why.** H5 predicts higher judge error on EPIC-KITCHENS. Pretraining exposure would push the
other way. Without naming the confound, a null H5 has three readings (no effect, underpowered,
contamination masking) and the writeup can only distinguish two of them.

**Touches.** `RED-TEAM.md`, `COVERAGE.md`, `SURVEY.md` (a Track-3 note on VLM pretraining
corpora), `DECISIONS.md`.

**Reverses if.** Nothing; it is a disclosure.

### R6 — Pre-data amendment to gold size or gold allocation for H5

**What.** Two options, either recorded as a `DECISIONS.md` entry *before the first label is
written*:

- Raise the manipulation-task gold to ≥400 per arm (the task H5 is stated on), keeping 200 per
  arm for hand count. Roughly four extra hours of labelling at the rubric's timing estimate.
- Or keep 200 per arm but draw gold **stratified on judge disagreement** (frames where the
  stored gemini label and the live Qwen label differ, oversampled with known inclusion
  probabilities) and use the weighted / stratified form of PPI. The disagreement stratum is
  where judge error concentrates, so the same label budget buys more information about
  P(error | domain).

**Why.** D035: power for the pre-registered effect is between roughly one-in-five and
one-in-two at n=200. A pre-registered headline that the project's own simulation says it
cannot reliably detect is the one place where a pre-data amendment is clearly the right
call, and the pre-registration's own rules allow it if recorded.

**Touches.** `PRE-REGISTRATION.md` (amendments pointer only), `DECISIONS.md` (the entry, with
the prior sizes stated), `METHOD.md` E3, `scripts/power_simulation.py` re-run for the new
design.

**Reverses if.** Labelling has already begun. Then the sizes are frozen and D035's
"underpowered, not null" language governs.

### R7 — Pin the rung-3 guarantee mechanism

**What.** H6 promises "an agreement floor at a stated coverage". Name the mechanism now:
conformal risk control / Learn-then-Test (the machinery Trust-or-Escalate builds on), with the
calibration set disjoint from the scoring set. With 200 gold frames on the ego arm, pre-declare
the split — or use the stored gemini labels for threshold search and reserve gold solely for
verifying the floor.

**Why.** "Reports a floor" is a promise, not a procedure. `WAVES.md` already flags the leak
shape (tuning the threshold on frames it later scores). A finite-sample guarantee at n≈100 is
achievable only with the mechanism chosen in advance.

**Touches.** `PRE-REGISTRATION.md` amendments pointer, `MODEL_CARD.md` rung 3,
`ARCHITECTURE.md` `distil` seam, `distil/cascade.py`'s docstring.

**Reverses if.** Nothing; H6 as written needs this to be checkable.

### R8 — Run E2 and E5 at the pre-registered N

**What.** The n=100 run cost cents (`HANDOFF.md`); the pre-registered 10,000 per arm is tens
of dollars total including the seven-variant sweep on `P2k`. `HANDOFF.md` correctly says this
needs an explicit decision. This review's recommendation is: make it.

**Why.** H1, H1b and H3 are blocked only by that decision. The infrastructure is live and
smoke-tested. Nothing in the post-training pipeline is cheaper per unit of information.

**Touches.** `DECISIONS.md` (the authorisation), `HANDOFF.md`, `BENCHMARK.md` R1/R3.

### R9 — Kill Result 2 explicitly

**What.** Record in `DECISIONS.md` that the transfer probe is dropped: the raw corpus is
inaccessible to this account (D044), EPIC-KITCHENS-100 registration requires an institutional
email (`SURVEY.md`), and the evaluation release ships no downstream-task labels. Keep "does hand
visibility predict training value" in `COVERAGE.md` as untested, in those words.

**Why.** The pre-registration's own kill-gate logic: a half-finished second result damages the
first. Every document still carries Result 2 as pending; a reader cannot tell it is
effectively dead.

**Touches.** `README.md`, `PRE-REGISTRATION.md` amendments pointer, `METHOD.md` E9,
`BENCHMARK.md` R6, `COVERAGE.md`, `DECISIONS.md`.

**Reverses if.** Corpus access and an institutional affiliation both materialise. Then the
gate re-opens as pre-registered.

### R10 — A drift lint in `make validate`

**What.** A script that fails if `gemini-2.5-flash`, "three judges", "documentation only",
"no judge has been called" or `JUDGES=gemini` appear in any public document outside
`DECISIONS.md`, `UPSTREAM-FINDINGS.md`, `LINEAGE.md`, `WAVES.md`'s historical table and this
file.

**Why.** `AGENTS.md` rule 2 says `make validate` should catch stale prose. Today it catches
stale *numbers* only in spirit and stale *designs* not at all. Section 4 above is the evidence.

**Touches.** `Makefile`, a new script under `scripts/`, `AGENTS.md` rule 2 (one sentence).

## Suggested order

1. R9, R1, R5 and the stale-prose sweep, as one `DECISIONS.md` entry — all documentation, all
   pre-data, all cheap. This is the "absorb D042" step and should precede anything else.
2. R6 and R7 decided and recorded, because both must land before the first label is written.
3. R3 arranged (a person, a date) so the second rater's pass can follow the primary pass.
4. R8 authorised and run; R4 in the same session, on the same deployment.
5. Wave 3 labelling. It is the critical path: the seven-day retest gap dominates everything
   downstream and nothing else blocks it (`HANDOFF.md`).
6. R2 while waiting out the retest gap.
7. R10 last, so it lints the corrected documents rather than the current ones.

## What this review does not do

- It does not question the survey verdict or the H5 framing. Both hold.
- It does not propose new hypotheses. Every addition above either strengthens an existing one
  or discloses a confound on it.
- It does not recommend re-adding a paid frontier judge. D042's reasoning stands; the point of
  section 2 is that the original judge is *already in the panel* through its stored labels.
- It carries no experimental number, and cites the file for every figure it mentions.
