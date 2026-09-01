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

## E-1 — Effective N (H8)

No experiment. Participant counts for the three corpora, confirmed against each corpus's own
documentation, and the resulting effective-N comparison. "10,000 frames each" conceals a
near-order-of-magnitude difference in precision.

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

## E2 — Replication

`gemini-2.5-flash` under `P0a` and `P0b`, on **Build AI's own frames** (`E10k-ego`).
Because the frames are identical to the ones behind the published numbers, this is a far
tighter test than a re-draw: any gap is the judge or the prompt, never the sample.

H1: all three figures reproduce within **±2 pp** under `P0a`. H1b: `P0a` and `P0b` differ on
the manipulation figure by ≥ 1 pp, which would mean the published number is under-determined
by the published artifacts.

Then the sampling-design arm: `P0a` on `S10k-U` and `S10k-S`. That gap is reported whatever
its size, and it is a different question from replication.

A failure to replicate is reported as a failure to replicate. It is not investigated until it
goes away.

*Cost: ~40,000 judge calls across four arms. ~$15–40.*

## E3 — Human gold

600 primary labels against `RUBRIC.md` v1.1.0: `G200-ego`, `G200-ego4d` and `G200-epic`, all
drawn from Build AI's own judged frames.
Random order, blind to judge output, both tasks per frame, tags and difficulty recorded at
label time.

Then, **at least seven days later**, the blind `R100` re-label. Intra-rater κ is computed
first, before any judge–human comparison. If it is below 0.70 the rubric is not decidable,
the audit is deferred, and the rubric becomes the deliverable — that stopping rule is in the
pre-registration and is not negotiable after the fact.

*Cost: ~700 labelling events at ~20 s each ≈ 4 h of the rater's time, split across two
sessions a week apart. $0.*

## E4 — Judge panel and agreement

All three judges over `P2k`, plus all three over `G200-ego4d` and `G200-epic`.

Reported: raw agreement and **Gwet's AC1** for judge-vs-human per task per domain, with
Cohen's κ beside it; pairwise and Fleiss' agreement across the panel plus a judge-error-
dependence estimate; every exclusion counted by reason and removed from the denominator
explicitly.

Headline prevalence is the **PPI** estimate — human gold debiasing the judge-labelled sample —
with clustered resampling where a grouping variable exists. Build AI's evaluation frames ship
none (`UPSTREAM-FINDINGS.md` F9), so those arms report iid intervals labelled as a lower bound
on width, and the design effect (H2) is measured on `S10k-U` and `S10k-S` instead.

*Cost: ~2,300 frames × 2 frontier judges = ~4,600 calls, plus the same volume locally on
Qwen3-VL. ~$10–30 plus GPU time.*

## E5 — Prompt sensitivity

P1–P7 across `P2k`, all three judges, against the `P0a`/`P0b` reference. Reported as the range
and SD of each headline figure, with Holm–Bonferroni over the 21-test family declared in
advance.

**P3 is the one to watch.** Their prompt never mentions gloves, in a corpus of factory work
where gloves are near-universal. If stating that a glove counts moves the ≥1-hand figure by
more than 2 pp, then a sentence Build AI never wrote is worth percentage points on a number
they publish. The "whose hands" variant was retired — their prompt already says it.

*Cost: 7 variants × 2,000 frames × 2 frontier judges = 28,000 frontier calls, plus 14,000
locally on the open judge. ~$40–90.*

## E6 — Domain bias

The decisive experiment. Same panel, same prompts, human-labelled draws from all three of
Build AI's own evaluation arms — so the domains are exactly the ones their comparative claim
ranks, with no access negotiation and no re-draw.

Model: `judge_correct ~ domain + task`, cluster-robust by participant. The question is not
whether the judge scores the corpora differently — Build AI's claim is that it should. The
question is whether the judge is **equally accurate** across them. If it is not, part of the
published gap measures the judge.

This is the one experiment whose result changes what the published comparative claim means,
in either direction. It is aimed at the EPIC-KITCHENS margins specifically — 6.05 pp and
6.62 pp — which a 5 pp judge-accuracy gap would largely explain. **The Ego4D margins are far
too large for any judge effect to account for**, and the writeup says so rather than letting
the reader over-generalise.

*Cost: included in E4 and E5 volumes; analysis only, ~1 day.*

## E7 — Distillation

Rung 1: linear probe on frozen features, trained on `gemini-2.5-flash` `P0a` labels over
`E10k-ego`, evaluated against human gold on `G200-ego`. Laptop-runnable. This is the baseline that
must be beaten before anything more expensive is justified.

Rung 2: Qwen3-VL LoRA, 4-bit, on Modal L4 24 GB, same targets, same held-out evaluation.

Rung 3, and the one that makes this an instrument rather than a cheaper model: a
**Trust-or-Escalate cascade** (2407.18370). The distillate estimates its own confidence,
abstains below threshold, and escalates. What ships is an agreement **floor** against human gold
plus the **coverage** at which it holds — H6's ≥ 0.80 at ≥ 0.70 — rather than an average anyone
would have to take on trust. Their result is the precedent: on Chatbot Arena, where GPT-4 alone
rarely reached 80% human agreement, a cascade guaranteed >80% at ~80% coverage using much
cheaper models.

Teacher fidelity is still measured and still reported, because the diagnostic question stands:
does the distillate reproduce the judge's *errors* against human gold, or different ones? An
instrument that accidentally got better has stopped measuring the thing. But fidelity is the
diagnostic; the floor is the deliverable.

*Cost: rung 1 ≈ $0 and an afternoon. Rung 2 ≈ a few hours of L4 on free credits.*

## E8 — Calibration

ECE, 10 equal-width bins, reliability diagrams, per judge and per confidence kind, plus the
distillate.

**Restricted to P7.** Both published prompts constrain output to a bare integer or a
`yes`/`no` enum, so no confidence or logprob is exposed and calibration cannot be measured on
the published protocol at all. What is reported is a property of P7, not of Build AI's
measurement, and calibration-under-P0 goes in "what could not be checked". H7,
`DECISIONS.md` D018. Empty bins stay empty.

*Cost: analysis only.*

## E9 — Transfer probe (kill-gated)

Entry is a timeboxed spike: can a matched three-corpus frozen-feature probe run inside the
compute budget? If no, Result 2 is dropped and Result 1 ships alone, with the drop recorded
in `DECISIONS.md`.

If yes: matched on frame count, cluster count and training budget simultaneously, backbone
and downstream task as fixed by E0, seed 777, cluster-bootstrap intervals.

*Cost: the largest single item and the reason the gate exists. Bounded by the free-credit
budget; if it exceeds that, it does not run.*

## E10 — Card, and the self-audit

Emit the `MeasurementCard`. Then turn every instrument in this repository on this
repository's own claims and publish what breaks, unedited, in `RED-TEAM.md`. Sibling
precedent says to expect breakage: `assay` broke twelve of its own published claims this way.

*Cost: ~2 days, and it is the least skippable item on the list.*
