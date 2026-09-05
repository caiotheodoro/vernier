# Method

The protocol, experiment by experiment, with what each one costs. Cost is published because
a check nobody can afford is not a check — the convention is inherited from `assay/docs/METHOD.md`.

Estimates below are stated before execution and will be replaced with measured figures, each
citing the run record that produced it. An estimate that turns out badly wrong is itself
reportable.

## Order, and why it is fixed

```
SURVEY (gate) → freeze PRE-REGISTRATION → sample → replicate → human-labels
   → agreement → prompt-sweep → domain-bias → distil → calibrate
   → [kill-gate] → probe → card
```

`human-labels` runs **before** any agreement statistic is computed and before the rater has
seen any judge output. `prompt-sweep` runs after replication so that P0 is established as a
reference point rather than one arm among eight.

## E-1 — Participant-count precision disparity (H8)

No experiment. Participant counts for the three corpora, confirmed against each corpus's own
documentation, and the resulting precision-disparity comparison — a raw participant-count
lookup, not an ICC-adjusted effective N (D031; a true effective N needs cluster-size and
outcome-variance data that don't exist pre-labelling). "10,000 frames each" conceals a
near-two-orders-of-magnitude difference in precision.

Published first because it is free, it is checkable by anyone, and it needs no cooperation
from anybody.

*Cost: an afternoon.*

## E0 — Survey gate

`SURVEY.md`, three tracks, background research agents. **The novelty claim must survive it.**
If independent validation of a VLM quality judge on egocentric data already exists, the
project stops and re-scopes rather than duplicating it.

The survey also fixes two things nothing downstream can start without: the **backbone** and
the **downstream benchmark** for Result 2, chosen so numbers are commensurable with the
field rather than with vernier's convenience.

*Cost: ~2 days, agent time only.*

## E1 — Sampling

Pull the three evaluation parquets (~5.5 GB total, Apache-2.0, ungated) and draw `P2k`,
`G200-ego`, `G200-ego4d`, `G200-epic`, `R100` from Build AI's own judged frames at seed 777.
Separately draw `S10k-U` and `S10k-S` from the Egocentric-10K corpus for the sampling-design
arm, streamed — the corpus is 16.4 TB and only the drawn frames are decoded.

**First check, before anything else:** verify the parquets contain the frames the published
per-frame labels refer to, and whether they carry a worker or participant identifier. The
second determines whether clustered intervals are available for these arms or whether that
limitation goes in the card. `DECISIONS.md` D016.

*Cost: ~1 day. 5.5 GB plus ~20k streamed corpus frames.*

## E2 — Comparison, not replication (`docs/DECISIONS.md` D042)

Written when this was a live replication under `gemini-2.5-flash`; that judge is deprecated
for new API keys. Now: the live Qwen3-VL judge under `P0a` and `P0b`, on **Build AI's own
frames** (`E10k-ego`), compared against Build AI's own `gemini-2.5-flash` labels for those same
frames — already stored in the evaluation parquet, read directly, never re-called
(`UPSTREAM-FINDINGS.md` F9). Because the frames are identical to the ones behind the published
numbers, this is a far tighter test than a re-draw: any gap is the judge or the prompt, never
the sample. Real, smoke-scale (`scripts/e2_replication.py`, n=100) runs exist; see
`docs/HANDOFF.md`.

H1: all three figures land within **±2 pp** of published under `P0a`. H1b: `P0a` and `P0b`
differ on the manipulation figure by ≥ 1 pp, which would mean the published number is
under-determined by the published artifacts.

Then the sampling-design arm: `P0a` on `S10k-U` and `S10k-S` — **run, and H2 does not hold**
(`docs/DECISIONS.md` D071 built the raw-corpus adapter, D072 measured it). The design effect is
1.25–1.66 across both arms and all three tasks, against a pre-registered threshold of 2. Real,
so an iid interval here is genuinely too narrow, but by less than H2 asserted. A different
question from the comparison above, and reported whatever its size, as promised.

A comparison landing outside tolerance is reported as such. It is not investigated until it
goes away.

*Cost: real per-call rates observed live are far below the original frontier-API estimate this
line once carried, since one of the two arms (Build AI's own labels) is now free and the other
is a self-hosted open judge, not a paid API — see `docs/HANDOFF.md` for the actual observed
figures rather than a pre-D042 estimate.*

## E3 — Human gold

600 primary labels against `RUBRIC.md` v1.2.0: `G200-ego`, `G200-ego4d` and `G200-epic`, all
drawn from Build AI's own judged frames.
Random order, blind to judge output, both tasks per frame, tags and difficulty recorded at
label time.

Then, **at least seven days later**, the blind `R100` re-label. (As run, neither held: the
retest was redrawn from the primary pool, D058, and came a median of 2.4 hours later rather
than seven days, `docs/DECISIONS.md` D076.) Intra-rater κ is computed
first, before any judge–human comparison. If it is below 0.70 the rubric is not decidable,
the audit is deferred, and the rubric becomes the deliverable — that stopping rule is in the
pre-registration and is not negotiable after the fact.

*Cost: ~700 labelling events at ~20 s each ≈ 4 h of the rater's time, split across two
sessions a week apart. $0.*

## E4 — Judge panel and agreement

Written for three live judges; post-D042 the live judge is Qwen3-VL alone
(`scripts/generate_qwen_comparison_labels.py`), with Build AI's own stored `gemini-2.5-flash`
labels as the second, frozen arm (`docs/REVIEW.md` point 2) — over `P2k`, plus both over
`G200-ego4d` and `G200-epic`.

Reported: raw agreement and **Gwet's AC1** for judge-vs-human per task per domain, with
Cohen's κ beside it; pairwise and Fleiss' agreement across the panel plus a judge-error-
dependence estimate; every exclusion counted by reason and removed from the denominator
explicitly.

Headline prevalence is the **PPI** estimate — human gold debiasing the judge-labelled sample —
with clustered resampling where a grouping variable exists. Build AI's evaluation frames ship
none (`UPSTREAM-FINDINGS.md` F9), so those arms report iid intervals labelled as a lower bound
on width, and the design effect (H2) is measured on `S10k-U` and `S10k-S` instead.

*Cost: the stored-label arm is free (already-published data, `scripts/published_labels.py`);
~2,300 frames on Qwen3-VL, self-hosted, not a paid frontier API — see `docs/HANDOFF.md` for
real observed per-call rates.*

## E5 — Prompt sensitivity

Written when the live panel held three live judges; post-D042, P1–P7 across `P2k`, the live Qwen3-VL judge only (Build
AI's own stored labels exist for `P0` alone — they never published a multi-variant sweep to
compare against), against the `P0a`/`P0b` reference. Reported as the range and SD of each
headline figure, with Holm–Bonferroni over the 21-test family declared in advance. Real,
smoke-scale (`scripts/e5_prompt_sweep.py`, n=5) runs exist; see `docs/HANDOFF.md`.

**P3 is the one to watch.** Their prompt never mentions gloves, in a corpus of factory work
where gloves are near-universal. If stating that a glove counts moves the ≥1-hand figure by
more than 2 pp, then a sentence Build AI never wrote is worth percentage points on a number
they publish. The "whose hands" variant was retired — their prompt already says it.

*Cost: 7 variants × 2,000 frames on the self-hosted open judge alone, not a paid frontier API —
see `docs/HANDOFF.md` for real observed per-call rates.*

## E6 — Domain bias

The decisive experiment. Same panel, same prompts, human-labelled draws from all three of
Build AI's own evaluation arms — so the domains are exactly the ones their comparative claim
ranks, with no access negotiation and no re-draw.

Model: `judge_correct ~ domain + task`, cluster-robust where a grouping variable exists. The
`G200-*` draws come from Build AI's evaluation-parquet frames, which carry no participant
identifier (`docs/UPSTREAM-FINDINGS.md` F9) — this model reports an iid interval labelled as a
lower bound for those arms, not a clustered one; see `PRE-REGISTRATION.md`'s cluster-problem
section. The question is not whether the judge scores the corpora differently — Build AI's
claim is that it should. The question is whether the judge is **equally accurate** across them.
If it is not, part of the published gap measures the judge.

This is the one experiment whose result changes what the published comparative claim means,
in either direction. It is aimed at the EPIC-KITCHENS margins specifically — 6.05 pp and
6.62 pp — which a 5 pp judge-accuracy gap would largely explain. **The Ego4D margins are far
too large for any judge effect to account for**, and the writeup says so rather than letting
the reader over-generalise.

*Cost: included in E4 and E5 volumes; analysis only, ~1 day.*

## E7 — Distillation

Rung 1: linear probe on frozen features, trained on `gemini-2.5-flash` `P0` labels — read
directly from the evaluation parquets, never a live call (`scripts/published_labels.py`,
`docs/DECISIONS.md` D047) — over `E10k-ego \ G200-ego` **and, per `docs/REVIEW.md` R1, extended
to all three evaluation arms** (`E10k-ego4d \ G200-ego4d`, `E10k-epic \ G200-epic` too — ~29,400
real labels total, zero judge spend, cross-domain by construction), evaluated against human
gold on `G200-ego`. The `G200-*` frames are excluded from training by construction, not just
convention, in every arm — each is a real subset of its own root sample, and training on the
unfiltered set would leak the evaluation frames into training. Laptop-runnable, and now
literally free. This is the baseline that must be beaten before anything more expensive is
justified.

This paragraph originally said `P0a` specifically; the real stored label's exact P0 variant is
not recoverable from the published artifacts at all (`UPSTREAM-FINDINGS.md` F2 — the dataset
card and shipped prompt file differ, and which one produced the published figures cannot be
determined). `scripts/generate_rung1_labels.py` records the labels as `P0b`, matching
`RUBRIC.md`'s own convention of treating the shipped, pinned-revision file as the reference
prompt — a flagged judgment call, not a recovered fact.

Rung 2: Qwen3-VL LoRA, 4-bit, on Modal L4 24 GB, same targets, same held-out evaluation.

Rung 3, and the one that makes this an instrument rather than a cheaper model: a
**Trust-or-Escalate cascade** (2407.18370). The distillate estimates its own confidence,
abstains below threshold, and escalates. What ships is an agreement **floor** against human gold
plus the **coverage** at which it holds — H6's ≥ 0.80 at ≥ 0.70 — rather than an average anyone
would have to take on trust. Their result is the precedent: on Chatbot Arena, where GPT-4 alone
rarely reached 80% human agreement, a cascade guaranteed >80% at ~80% coverage using much
cheaper models.

**Threshold-selection mechanism, pinned before any label is written (`docs/DECISIONS.md`
D049, `docs/REVIEW.md` R7): Learn-then-Test / conformal risk control** (2110.01052, the
machinery Trust-or-Escalate itself builds on) — a finite-sample statistical guarantee on the
true error rate, not a point estimate of it. Calibration set (threshold search) and scoring
set (floor verification) are disjoint by pre-declared design: threshold search uses Build AI's
own free, stored labels; `G200-ego`'s 200 human-gold frames are reserved solely for verifying
the floor the mechanism selects, never for searching over candidate thresholds.

Teacher fidelity is still measured and still reported, because the diagnostic question stands:
does the distillate reproduce the judge's *errors* against human gold, or different ones? An
instrument that accidentally got better has stopped measuring the thing. But fidelity is the
diagnostic; the floor is the deliverable.

*Cost: rung 1 ≈ $0 and an afternoon. Rung 2 ≈ a few hours of L4 on free credits.*

## E8 — Calibration

ECE, 10 equal-width bins, reliability diagrams, per judge and per confidence kind, plus the
distillate.

**Restricted to P7 for Build AI's own claim; real for the open judge under P0 as well
(`docs/REVIEW.md` point 3).** Both published prompts constrain output to a bare integer or a
`yes`/`no` enum, so no confidence or logprob is exposed by Build AI's own closed-API
measurement, and calibration cannot be measured on *their* published protocol at all — that
finding stands as written, H7, `DECISIONS.md` D018. But the self-hosted Qwen3-VL judge exposes
the answer-token logprob regardless of prompt variant (`judges/qwen3vl.py`'s
`_mean_output_token_probability`, confirmed working live against real frames, `docs/HANDOFF.md`)
— calibration of *this* judge under the *published* bare-value format is a real, measurable
result, not restricted to P7. "P7 only" was a leftover of the retired closed-API design, where
verbalized confidence was the only signal a prompt schema could expose. `docs/REVIEW.md`
recommends narrowing the "what could not be checked" entry accordingly, once calibration is
actually computed at scale. Empty bins stay empty.

*Cost: analysis only.*

## E9 — Transfer probe — dropped, gate never reached (`docs/DECISIONS.md` D048)

Entry was to be a timeboxed spike: can a matched three-corpus frozen-feature probe run inside
the compute budget? The gate is never reached. Raw Egocentric-10K access has since been granted
(D065), but the other two reasons stand and either alone is sufficient: EPIC-KITCHENS-100
registration requires an institutional email this project does not have (`SURVEY.md`), and the
evaluation release ships no downstream-task labels to probe against regardless of access. Result 2 is dropped and Result 1 ships alone.

*Cost: zero -- the timeboxed spike this entry describes never ran.*

## E10 — Card, and the self-audit

Emit the `MeasurementCard`. Then turn every instrument in this repository on this
repository's own claims and publish what breaks, unedited, in `RED-TEAM.md`. Sibling
precedent says to expect breakage: `assay` broke twelve of its own published claims this way.

*Cost: ~2 days, and it is the least skippable item on the list.*
