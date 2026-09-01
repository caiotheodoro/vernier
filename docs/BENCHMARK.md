# Benchmark

The results table. **Empty by design** — this repository is documentation-only, and a
benchmark file carrying numbers before any experiment ran would be the exact failure mode
vernier exists to document.

Its structure is fixed now so that results land in a shape decided before anyone saw them.

## R0 — Effective N (H8, no experiment required)

| Corpus | Frames sampled | Participants | Effective N |
|---|---|---|---|
| Egocentric-10K | 10,000 | 2,153 | — |
| Ego4D | 10,000 | ~931 | — |
| EPIC-KITCHENS-100 | 10,000 | ~45 | — |

Published as three estimates of equal precision. They are not. Participant counts confirmed
against each corpus's own documentation before publication (D024).

## R1 — Replication (E2)

On Build AI's own published frames, so any gap is the judge or the prompt, never the sample.
Headline prevalence is the **PPI** estimate; the raw judge proportion is shown beside it.

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

`judge_correct ~ domain + task`, cluster-robust by participant. H5: judge error rate on
manipulation differs by ≥ 5 pp across domains, higher on EPIC-KITCHENS-100.

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

## R6 — Transfer probe (E9, if the gate opens)

Matched frozen-feature probes across Egocentric-*, Ego4D and EPIC-KITCHENS-100 on the
downstream task fixed by `SURVEY.md`. Matched on frame count, cluster count and training
budget simultaneously.

If the gate closes, this section says so and names the compute that would have been required.

## What could not be checked

Every published card carries this section with a named reason per item. It is not an
appendix: an empty finding list must never read as a clean bill of health.
