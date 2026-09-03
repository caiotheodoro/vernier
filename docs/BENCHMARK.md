# Benchmark

The results table. Its structure was fixed before any experiment ran, specifically so results
would land in a shape decided before anyone saw them — that discipline held. Real results now
exist for R0/R1/R4/R6, and for the agreement, calibration, and instrument sections (R2/R3/R5)
via `data/wave4_analysis.json` and `data/rung1_distillation.json`; the authoritative,
machine-checked source for every cited figure is `MEASUREMENT_CARD.json` (`make card`), not
this file — backfilling this table's cells from that card is separate, still-open work, tracked
in `docs/HANDOFF.md`, not a claim that no experiment has run.

## R0 — Participant-count precision disparity (H8, no experiment required)

| Corpus | Frames sampled | Participants | Effective N |
|---|---|---|---|
| Egocentric-10K | 10,000 | 2,153 | — |
| Ego4D | 10,000 | 923 | — |
| EPIC-KITCHENS-100 | 10,000 | 37 | — |

**Effective N is a distinct, not-yet-computed quantity** (D031). H8 is a raw participant-count
lookup, not an ICC-adjusted effective sample size — computing the latter needs cluster-size and
outcome-variance data that only exist once R100/primary labelling has run; `estimation`'s
`design_effect` is where that computation belongs. The `Effective N` column stays `—` until then.

Published as three estimates of equal precision. They are not. Participant counts confirmed
against each corpus's own primary documentation (D024, corrected D030): Egocentric-10K from the vendor's own
card, Ego4D from ego4d-data.org, EPIC-KITCHENS-100 from arXiv 2006.13256's full text (the
"~45" previously used here was the kitchen/environment count, not participants — the paper's
own figure is 37 subjects across 45 kitchen environments).

## R1 — Comparison, not replication (E2, `docs/DECISIONS.md` D042)

Written when H1 was a live replication under the original judge; that judge
(`gemini-2.5-flash`) is deprecated for new API keys, so this is now a comparison between Build
AI's own published labels (stored in the evaluation parquet, read directly, never re-called)
and the live Qwen3-VL judge, on the identical published frames — any gap is the judge or the
prompt, never the sample. `P0a`/`P0b` below are the live judge's own answers under each prompt
arm. Headline prevalence is the **PPI** estimate; the raw judge proportion is shown beside it.
A real preliminary run exists at n=100 (`docs/HANDOFF.md`) — not filled in below, since it is
far short of the pre-registered N and would misrepresent a smoke test as the headline result.

| Figure | Published | `P0a` | `P0b` | Within ±2 pp (H1) | `P0a`−`P0b` (H1b) |
|---|---|---|---|---|---|
| ≥1 hand | 96.42% | — | — | — | — |
| Both hands | 76.34% | — | — | — | — |
| Active manipulation | 91.66% | — | — | — | — |

Sampling-design arm, a separate question from replication:

| Figure | `E10k-ego` (theirs) | `S10k-U` | `S10k-S` |
|---|---|---|---|
| ≥1 hand | — | — | — |
| Both hands | — | — | — |
| Active manipulation | — | — | — |

Intervals are cluster bootstrap over `worker_id`. The iid interval is reported beside each,
labelled, with the design effect (H2: ≥ 2).

## R2 — Judge–human agreement (E4)

Per judge × task × domain: n, exclusions by reason, raw agreement, **Gwet's AC1 (primary)**,
Cohen's κ beside it, and an interval. H4: agreement higher on hand count than on manipulation,
for every judge.

Reported alongside: pairwise and Fleiss' agreement across the panel, labelled as an **upper
bound** on judge reliability (`RED-TEAM.md` A3), an explicit **judge-error-dependence**
estimate (D025), and intra-rater agreement on `R100`, which gates the whole table at 0.70.

## R3 — Prompt sensitivity (E5)

Each headline figure across `P1`–`P7` against the `P0a`/`P0b` reference: range, SD, and
Holm–Bonferroni-adjusted comparisons within the pre-declared 21-test family. H3: manipulation
spread ≥ 5 pp and greater than the ≥1-hand spread.

**P3 carries its own line.** Their prompt never mentions gloves. H3 predicts that stating a
glove counts moves the ≥1-hand figure by ≥ 2 pp on its own.

## R4 — Domain bias (E6)

`judge_correct ~ domain + task`, cluster-robust where a grouping variable exists. H5: judge
error rate on manipulation differs by ≥ 5 pp across domains, higher on EPIC-KITCHENS-100.

The `G200-*` draws are subsets of Build AI's evaluation-parquet frames, which carry no
participant identifier (`FrameRef.why_no_provenance`, `docs/UPSTREAM-FINDINGS.md` F9) — this
model reports an **iid interval labelled as a lower bound**, not a clustered one, for those
arms. "Cluster-robust by participant" only applies where `FrameRef.worker_id` is present.

Read against the published margins, which is the whole point:

| Comparison | Published margin, ≥1 hand | Published margin, manipulation | Could a 5 pp judge effect explain it? |
|---|---|---|---|
| Egocentric-10K vs EPIC-KITCHENS-100 | 6.05 pp | 6.62 pp | **Largely, yes** |
| Egocentric-10K vs Ego4D | 29.09 pp | 41.59 pp | No — and the writeup must say so |

A wide interval containing zero is reported as **underpowered, not null** (`RED-TEAM.md` A9).

## R5 — The instrument (E7, E8)

**Headline is the guarantee**, per H6:

| Task | Agreement floor | Coverage at that floor | Target |
|---|---|---|---|
| Hand count | — | — | ≥ 0.80 at ≥ 0.70 |
| Active manipulation | — | — | ≥ 0.80, coverage expected lower |

Diagnostics beneath it: distillate vs. teacher and vs. human gold, per class, against a
constant-answer baseline, with AC1 primary and κ beside it; error inheritance; ECE and
reliability diagrams per judge and for the distillate; and **J / ΔJ** for calibration
instability across the three corpora.

## R6 — Transfer probe (E9) — dropped, `docs/DECISIONS.md` D048

Matched frozen-feature probes across Egocentric-*, Ego4D and EPIC-KITCHENS-100 on the
downstream task fixed by `SURVEY.md` would have tested this. It does not run: the raw
Egocentric-10K corpus is inaccessible to this account (D044), EPIC-KITCHENS-100 registration
requires an institutional email this project does not have (`SURVEY.md`), and the evaluation
release ships no downstream-task labels at all. This is not a compute-budget gate closing --
the inputs the probe needs do not exist for this project.

## What could not be checked

Every published card carries this section with a named reason per item. It is not an
appendix: an empty finding list must never read as a clean bill of health.
