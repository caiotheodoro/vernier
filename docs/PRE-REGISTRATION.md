# Pre-registration

**Committed before any judge is called or any label is written.** That ordering is the only
thing separating a pre-registration from a description. Check the git history: this file
lands before `src/`.

Revision `1.3.0`. Revised three times before freezing and **before any result was seen**:
`1.1.0` on facts established by reading Build AI's published artifacts directly
(`UPSTREAM-FINDINGS.md`, `DECISIONS.md` D014–D019); `1.2.0` on four methodological errors the
literature survey caught (`SURVEY.md` Track 3, `DECISIONS.md` D020–D025); `1.3.0` on the
verification pass over the cited papers, which rewrote H6 as a coverage-at-a-floor guarantee,
grounded H3 in prior work, added J/ΔJ, and refuted the survey's claimed novelty risk
(`DECISIONS.md` D026–D029).

Three revisions before freeze is the process working, not churn: each was driven by reading a
primary source, and every change is dated and attributed. **From the freeze commit onward the
protocol is fixed**, and any further change is an amendment recorded in `DECISIONS.md` naming
what changed, when, why, and what the affected number was beforehand. After freeze, any change is a new
`DECISIONS.md` entry naming what changed, when, why, and what the affected number was before.

## Why this document exists

vernier's finding is that Build AI's published quality figures have no stated uncertainty, no
validated oracle, and no test of the cross-domain assumption their comparative claim depends
on. A project making that finding by improvising its own protocol would be self-refuting.
Everything below is fixed in advance so that no result can be reached by choosing the
analysis after seeing the data.

## What is being audited

`builddotai/Egocentric-10K-Evaluation`, pinned at revision
`d74b7883c998dd360e3f051830fcc792a83985e6`, Apache-2.0, ungated. It publishes, from 10,000
randomly sampled frames of each of three corpora labelled by `gemini-2.5-flash`:

| Dataset | Frames | 0 hands | ≥1 hand | 2 hands | Active manipulation |
|---|---|---|---|---|---|
| **Egocentric-10K** | 10,000 | 3.58% | **96.42%** | **76.34%** | **91.66%** |
| Ego4D | 10,000 | 32.67% | 67.33% | 36.95% | 50.07% |
| EPIC-KITCHENS-100 | 10,000 | 9.63% | 90.37% | 61.05% | 85.04% |

The comparative claim is that Egocentric-10K is state-of-the-art on both measures. **The
margins over EPIC-KITCHENS-100 are 6.05 pp and 6.62 pp.** Against Ego4D they are large.

The release ships the judged frames themselves for all three corpora (~5.5 GB total) and both
prompts. Snapshots: `docs/upstream/`.

## P0 is two prompts, not one

The dataset card and the shipped `prompts/active_manipulation.txt` differ in four places, and
which one produced 91.66% is not recoverable (`UPSTREAM-FINDINGS.md` F2). Both are therefore
run as primary arms:

- **`P0a`** — the prompt printed on the dataset card.
- **`P0b`** — the prompt shipped in `prompts/`.

The hand-count prompt is identical across both sources apart from an apostrophe glyph; it is
run once and labelled `P0`.

## Samples

Two families. The **evaluation family** is Build AI's own judged frames, so agreement is
measured against the exact frames behind the published numbers with no sampling difference at
all. The **corpus family** exists only to test sampling-design sensitivity.

| Sample | Definition | n |
|---|---|---|
| `E10k-ego` | Build AI's published evaluation frames, Egocentric-10K arm | 10,000 |
| `E10k-ego4d` | Their evaluation frames, Ego4D arm | 10,000 |
| `E10k-epic` | Their evaluation frames, EPIC-KITCHENS-100 arm | 10,000 |
| `S10k-U` | Fresh draw from Egocentric-10K, uniform over frames | 10,000 |
| `S10k-S` | Fresh draw from Egocentric-10K, stratified by `factory_id` proportional to worker-hours, ≤1 frame per clip | 10,000 |
| `P2k` | Random subset of `E10k-ego`. The panel core: every judge, every prompt variant. | 2,000 |
| `G200-ego` | Random subset of `P2k`. Human-labelled, primary pass. | 200 |
| `G200-ego4d` | Random subset of `E10k-ego4d`. Human-labelled and panel-judged. | 200 |
| `G200-epic` | Random subset of `E10k-epic`. Human-labelled and panel-judged. | 200 |
| `R100` | Random subset of the three `G200` sets. Blind re-label, ≥7 days later. | 100 |

All draws use **seed 777**. Membership is written to disk before any judge is called and is
never redrawn. Undecodable frames are replaced from a pre-drawn reserve and every replacement
is logged.

Total human labelling: **600 primary + 100 re-label = 700 events**, one rater.

**The three gold sets are balanced at 200 each, deliberately.** H5's estimand is an
interaction — P(judge *error* | domain) — not a main effect, and an unbalanced split does not
identify it. `1.1.0` had 300/150/150 and would have failed on this. `SURVEY.md` Track 3,
error 3.

## The cluster problem, stated in advance

Frames are not independent observations. Frames from one worker share scene, lighting, task,
gloves, camera placement and fisheye calibration. An interval computed as though 10,000
frames were 10,000 independent draws understates its width by the design effect.

**Every interval vernier reports is a cluster bootstrap over `worker_id`** (Ego4D and
EPIC-KITCHENS-100: over that corpus's participant identifier), B = 10,000, seed 777. An iid
interval may be shown *beside* it, labelled, solely to exhibit the design effect. Never alone.

Design effect is reported as `(cluster CI width / iid CI width)²`.

**Resolved, and it constrains the design.** The evaluation parquets carry `frame_id` as a bare
UUID4 with no factory, worker, clip or timestamp component (`UPSTREAM-FINDINGS.md` F9), so
**clustering is unavailable on all three evaluation arms**. Those arms report iid intervals
labelled as a *lower bound on width*, and the limitation is named in the card rather than
absorbed. The design effect is measured instead on `S10k-U` and `S10k-S`, where the corpus
layout exposes factory and worker.

## Statistics, chosen now

| Quantity | Estimator |
|---|---|
| Headline proportions | Point estimate + cluster-bootstrap 95% interval |
| Headline proportions, bias-corrected | **Prediction-powered inference (PPI/PPI++)** over the human gold plus the judge labels, with **clustered resampling** — not instead of it |
| Judge–human agreement | Raw agreement and **Gwet's AC1** (primary), with Cohen's κ reported beside it |
| Judge–judge agreement | Pairwise AC1 and κ; Fleiss' κ across the panel; **plus an explicit judge-error-dependence estimate**, because a panel whose errors correlate buys less than three independent opinions |
| Intra-rater agreement | Gwet's AC1 and Cohen's κ, `R100` primary vs. re-label |
| Calibration | ECE, 10 equal-width bins, plus a reliability diagram; empty bins reported empty, never merged. **P7 only** — see H7. Plus **J and ΔJ** (2605.06939): judge quality and cross-corpus calibration instability, the diagnostics that say when a shared-calibration comparison is unreliable |
| Prompt sensitivity | Range and SD of each headline figure across the variant set |
| Domain bias | Logistic model on the **interaction**: `judge_error ~ domain × task`, cluster-robust where a grouping variable exists |
| Multiplicity | Holm–Bonferroni across the prompt-sweep family (7 variants × 3 figures = 21 tests), α = 0.05 |

**Why AC1 and not κ.** At a 96% prevalence the kappa paradox makes κ near-uninformative and
unstable: Rao & Callison-Burch (2606.00093) show protocol choices alone moving accuracy from
0.551 to 0.899 **and flipping the sign of κ with no verdict changes**. AC1 is pre-registered
as primary for that reason, decided before any label exists. `SURVEY.md` Track 3, error 2.

**Why PPI.** A cluster bootstrap corrects variance and leaves bias untouched. Reporting a
wide interval around an uncorrected judge-derived proportion would be a more sophisticated
version of the error being audited: a rigorously-intervalled wrong number. PPI uses the small
human-gold sample to debias the large judge-labelled sample and returns a valid interval for
the *true* prevalence. `SURVEY.md` Track 3, error 1.

No optional stopping. Sample sizes are fixed above and no agreement statistic is computed
until all 600 primary labels exist. Nothing not listed here is reported as confirmatory;
anything else discovered is labelled exploratory, in those words.

## The judge panel

| Judge | Role | Confidence available |
|---|---|---|
| `gemini-2.5-flash` | The replication target. Build AI's own judge. | none under their schema; verbalized under P7 |
| Claude (Opus/Sonnet 5) | Second frontier judge, different lineage. | none under their schema; verbalized under P7 |
| Qwen3-VL (open weights) | The reproducibility anchor: a third party with no API keys can re-run the audit end to end. | logprob |

Calibration is reported per judge and never pooled across confidence kinds.

## Prompt variants, fixed before any are run

`P0a` and `P0b` are upstream's own, verbatim, from `docs/upstream/`. The variants below each
change one thing. None is added after this file is frozen.

| | Variation | Why |
|---|---|---|
| P1 | Hand rule tightened: "clearly and unambiguously visible", fingertip clause removed | Their rule is maximally permissive; this brackets it from the strict side |
| P2 | Hand rule: the "any amount of visibility counts (even fingertips)" line deleted entirely | Isolates how much of 96.42% that single line is carrying |
| P3 | Adds an explicit instruction that a gloved hand counts as a hand | **Undefined in their prompt**, in a corpus of factory work where gloves are near-universal. The strongest single sensitivity test |
| P4 | Adds an explicit instruction that hands seen only in reflections or on screens do not count | Undefined in their prompt |
| P5 | Manipulation narrowed: visible contact with an object required | Their "in pursuit of a specific goal" clause is untestable per-frame |
| P6 | Manipulation widened: reaching toward an object counts | The other bracket |
| P7 | Response schema extended to request a confidence value | The only route to calibration; see H7 |

The planned "exclude other people's hands" variant was **retired**: their prompt already
states it (`UPSTREAM-FINDINGS.md` F3). Recording the retirement matters more than the variant
would have.

## Hypotheses

Directional, stated now. Any of these being wrong is itself the result.

- **H8 — Equal frame counts are not equal precision.** Effective N differs across the three
  compared corpora by close to an order of magnitude: EPIC-KITCHENS-100 draws on roughly 45
  participants against Ego4D's ~931. "10,000 frames each" therefore does not mean three
  estimates of equal precision, and the published comparison presents them as though it does.
  **This is computable from public participant counts before a single frame is labelled**, and
  it is reported first for that reason.
- **H1 — Replication.** On Build AI's own frames (`E10k-ego`), `gemini-2.5-flash` under `P0a`
  reproduces all three published figures within **±2 pp**. Outside that band is a replication
  failure, reported as one and not investigated until it goes away. This is a far tighter test
  than a re-draw would have been, because the frames are identical.
- **H1b — The two P0s disagree.** `P0a` and `P0b` differ on the manipulation figure by
  **≥ 1 pp**. If they do, the published number is under-determined by the published artifacts.
- **H2 — Design effect ≥ 2**, measured on `S10k-U` and `S10k-S`. Cluster-bootstrap intervals
  over `worker_id` are at least twice the width of the corresponding iid intervals. Because
  Build AI's own frames ship no grouping variable, this is established **in the corpus their
  sample was drawn from**, and the licensed conclusion is that any interval on the published
  figure inherits it — not that their sample's design effect was measured directly. Weaker
  than the `1.0.0` plan intended, and stated as such.
- **H3 — Prompt sensitivity is larger for manipulation than for hand count.** The spread of
  the manipulation figure across the variant set is **≥ 5 pp**, and exceeds the spread of the
  ≥1-hand figure. Reported as IPR/PAR (2604.16413). **This direction is predicted by prior
  work** — that paper finds LLM annotation "exhibits substantial stochastic variation in
  interpretative tasks, while appearing more stable in knowledge-based tasks", and hand-count is
  perceptual where active-manipulation is interpretative. H3 was written before that paper was
  read, which makes it a confirmation rather than a discovery, and the writeup says so. **P3 (gloves) alone moves the ≥1-hand figure by ≥ 2 pp.**
- **H4 — Agreement is higher for hand count than for manipulation.** AC1(judge, human) is
  greater on hand count than on manipulation, for every judge.
- **H5 — Domain bias exists, and it is large enough to matter.** In `judge_error ~ domain ×
  task`, the judge's error rate against human gold on the manipulation task differs between the
  Egocentric and EPIC-KITCHENS arms by **≥ 5 pp**, with the larger error rate on EPIC-KITCHENS-100. The published margin there is
  6.62 pp, so an effect of this size would account for most of it. **No such claim is made
  about the Ego4D comparison**, whose margins are far too large for a judge effect to explain,
  and the writeup must say so explicitly rather than letting the reader over-generalise.
- **H6 — The instrument carries a guarantee, at usable coverage.** Following Trust-or-Escalate
  (2407.18370), the distilled instrument **abstains** rather than always answering, and reports
  a *user-specified agreement floor* against human gold together with the **coverage** at which
  it holds. Pre-registered target: **≥ 0.80 agreement floor at ≥ 0.70 coverage** on the hand
  task, with lower coverage on manipulation at the same floor.
  A point estimate of teacher fidelity is reported too — a linear probe reaching **≥ 0.90**
  agreement with `gemini-2.5-flash` `P0a` on hand presence — but it is the *diagnostic*, not the
  claim. A buyer measuring a batch needs a floor they can rely on, not an average.
- **H7 — Calibration is not measurable on the published protocol.** Both published prompts
  constrain output to a bare integer or a `yes`/`no` enum, exposing no confidence. Calibration
  is therefore reported for `P7` only and is a property of that variant, not of Build AI's
  measurement. Calibration-under-P0 is listed in "what could not be checked".

## What would falsify the project

Written down so it cannot be quietly avoided:

- **H1 holds tightly, H1b is null, H2 is small, H3 is under 2 pp, and H5 is null.** Then Build
  AI's measurement is more robust than its documentation suggests, vernier's contribution is a
  confirmation with intervals, and it is published as a confirmation — not reframed to sound
  like a critique.
- **`SURVEY.md` finds this already published** for egocentric data. The project stops and
  re-scopes.
- **Human gold disagrees with itself.** Intra-rater AC1 on `R100` below **0.70** means the rubric
  is not decidable and no agreement statistic against it is interpretable. The rubric becomes
  the deliverable and the audit is deferred.

## Result 2 — the transfer probe, and its kill-gate

Matched frozen-feature probes over Egocentric-10K, Ego4D and EPIC-KITCHENS-100, on a
downstream task and backbone **fixed by `SURVEY.md` before any training**, so the numbers are
commensurable with the field rather than with vernier's convenience.

Matching is on frame count, cluster count and training budget simultaneously. An unmatched
comparison measures the sampling.

**Kill-gate:** a timeboxed spike at entry. If a matched three-corpus probe is not runnable
within the compute budget, Result 2 is dropped and Result 1 ships alone. A half-finished
second result damages the first.

## Known deviations, already anticipated

- **There is no public `builddotai/Egocentric-1M`** (404; the org hosts four datasets). Every
  figure names the release it was measured on. `UPSTREAM-FINDINGS.md` F6.
- **Ego4D and EPIC-KITCHENS-100 access is no longer required.** Their frames ship inside the
  evaluation release under Apache-2.0. The `1.0.0` fallback for "if either cannot be obtained"
  is retired. `UPSTREAM-FINDINGS.md` F5.
- **The evaluation parquets lack a usable cluster identifier** — confirmed, not anticipated.
  Handled under "the cluster problem" above: it moves where H2 is measured and weakens what H2
  licenses.
- **The published sample cannot be checked against the corpus at all**, for the same reason.
  Whether the 10,000 frames were uniform, stratified, or concentrated in a few sites is not
  determinable from the release. `S10k-U` versus `S10k-S` becomes the only available evidence
  about how much sampling design could matter, and it is evidence about the corpus rather than
  about their draw.
- **Judge availability drifts.** Model versions change under a stable API name. `judge_rev` is
  recorded per response, and a mid-experiment version change is a `DECISIONS.md` entry. This
  is unfixable from outside and is itself a finding about any SLA whose instrument is a
  versionless third-party API.

## Amendments

This file is frozen and not rewritten after the fact — this section exists so a reader of the
frozen text above is not misled about what actually happened, without touching a word of it.
Every entry here is a pointer to the real `DECISIONS.md` record, not a restatement of it.

- **`gemini-2.5-flash` (named throughout the judge-panel text above as the replication target
  and one of three judges) became unreachable for new API keys** before this project's own
  live replication could run. The panel is now the self-hosted Qwen3-VL judge alone; H1 is
  redefined from a live replication into a comparison against Build AI's own already-published
  labels on the same frames. `docs/DECISIONS.md` D042.
- **Result 2 (the transfer probe) is dropped**, its kill-gate never reached: the raw corpus
  this project would need is inaccessible to this account, EPIC-KITCHENS-100 registration
  needs an institutional email this project does not have, and the evaluation release ships no
  downstream-task labels to probe against regardless of access. `docs/DECISIONS.md` D044, D048.
- **A wider absorption of the D042 reframe's consequences** — the rung-1 distillation teacher,
  the judge-arm framing for E4/E6, and calibration's real availability under the open judge —
  is recorded in `docs/DECISIONS.md` D047, D048, following an independent review,
  `docs/REVIEW.md`.
