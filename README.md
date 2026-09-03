# vernier

**Putting error bars on a dataset vendor's quality claim — and distilling the judge that
produced it into an instrument anyone can re-run.**

Build AI sells egocentric factory video with published guarantees on quality. The number
behind the headline claim comes from `builddotai/Egocentric-10K-Evaluation`: **10,000
randomly sampled frames, labelled once, by `gemini-2.5-flash`.**

| Dataset | 0 hands | ≥1 hand | 2 hands | Active manipulation |
|---|---|---|---|---|
| **Egocentric-10K** | 3.58% | **96.42%** | **76.34%** | **91.66%** |
| Ego4D | 32.67% | 67.33% | 36.95% | 50.07% |
| EPIC-KITCHENS-100 | 9.63% | 90.37% | 61.05% | 85.04% |

Those numbers carry the comparative claim that Egocentric-10K is "state-of-the-art in hand
visibility and active manipulation density compared to previous in-the-wild egocentric
datasets".

The prompts behind them are more careful than press coverage suggested — structured, with
explicit rules and a constrained bare-value answer format (`0`/`1`/`2`, `yes`/`no` — not JSON,
corrected in `docs/DECISIONS.md` D043 after the earlier "constrained JSON schema" claim, D014,
was found to not match the shipped prompt files it was supposedly read from). What is missing
is everything downstream of
that: no human gold, no agreement statistic, no confidence interval, no prompt-sensitivity
analysis, and no test that the judge applies the same scale to a factory floor and a home
kitchen. **The margin over EPIC-KITCHENS-100 is 6.05 pp and 6.62 pp** — small enough that a
judge which is merely *less accurate* on kitchen imagery could account for most of it. The
comparison rests on that assumption and nobody checked it.

The measurement is also **closed and single-shot**: a buyer cannot re-run it on the batch they
are actually buying.

vernier measures the judge, then replaces it with something re-runnable.

> **Status: results in, two items blocked on external access.** The protocol is specified in
> `docs/PRE-REGISTRATION.md` and froze before `src/` existed -- that ordering is the whole
> point: a project auditing someone's unvalidated measurement does not get to improvise its
> own. Since then: the live judge (Qwen3-VL, self-hosted, `docs/DECISIONS.md` D042) has made
> thousands of real calls across the full-N replication, the prompt sweep, and gold-set
> judging. Human labels are real and collected (93 primary + retest, reduced from the
> pre-registered 600/100 per D057/D058) and committed as data. A rung-1 instrument (DINOv2
> features + linear probe + abstention cascade) has been trained and evaluated for real
> (D061) -- it does not clear its pre-registered target, and that negative result is reported,
> not hidden. `MEASUREMENT_CARD.json` is real and regenerable via `make card`; see
> `docs/HANDOFF.md` for exactly what remains (H2 and Result 2, both blocked on gated corpus
> access).
>
> What *has* happened is a close read of the published artifacts, which corrected several of
> this repository's own earlier claims. Those corrections are in `docs/UPSTREAM-FINDINGS.md`,
> including the one that matters most: **the dataset card and the shipped prompt file contain
> two different versions of the manipulation prompt**, and which one produced 91.66% cannot be
> recovered from what was published.

## The claim, in one line

A measurement is not a result until you know its uncertainty and what a wrong answer costs.
vernier does **not** claim Build AI's numbers are wrong. It claims nobody — including Build
AI — currently knows how wrong they could be.

## What this is not

- **Not an audit of the whole SLA.** Build AI advertises guarantees on "3D pose MPJPE,
  diversity, and quality". MPJPE is not checkable from the public release, which ships
  metadata and per-worker fisheye intrinsics but no pose annotations. vernier covers the
  quality axis and part of the diversity axis, and `docs/COVERAGE.md` says so in plain terms
  rather than implying more.
- **Not a claim about data collection practices.** `docs/ETHICS.md` records what is and is
  not knowable about provenance from the public release, and the limits that places on every
  conclusion here. It does not speculate beyond that.
- **Not a better hand detector.** The distilled model reproduces *the judge*, deliberately,
  including where the judge is wrong. An instrument that silently improved on the thing it
  measures would be useless for measuring it.

## The two results

**Result 1 — validate the judge.** Compare Build AI's own published labels against a live,
self-hosted open-weights judge on their own published frames (`docs/DECISIONS.md` D042 —
their original judge is deprecated for new API keys, so this is a comparison, not a live
replication); collect human gold against a written rubric; sweep the prompt; and test whether
the judge scores the three compared domains on the same scale.

**Result 2 — the transfer probe — dropped (`docs/DECISIONS.md` D048).** Their thesis is that
egocentric factory data is a general learning framework. The corpus draws 164,868 downloads in
30 days against 203 for the evaluation set that justifies it, and the publishing org has zero
public models. Matched-size frozen-feature probes across Egocentric-*, Ego4D and
EPIC-KITCHENS-100 on a common downstream task would have tested that thesis publicly for the
first time. It does not run: the raw Egocentric-10K corpus is inaccessible to this account
(D044), EPIC-KITCHENS-100 registration requires an institutional email this project does not
have (`SURVEY.md`), and the evaluation release ships no downstream-task labels at all to probe
against. Result 1 ships alone.

## Two things found before any experiment ran

**The published number is under-determined by the published artifacts.** The manipulation
prompt on the dataset card and the one in `prompts/active_manipulation.txt` differ in four
places — including "ignore *objects held by* other people" versus "ignore *actions performed
by* other people", which are different exclusions that disagree on exactly the frames an
assembly line produces. Both are run as primary arms. `docs/UPSTREAM-FINDINGS.md` F2.

**Their 10,000 frames are not 10,000 independent observations.** Egocentric-10K is 192,900
clips from 2,153 workers across 85 factories; frames drawn from one worker share scene,
lighting, task, glove, and camera placement. Any interval computed as though frames were iid
understates the true width by the design effect. vernier's pre-registration therefore fixes
a **cluster bootstrap over worker ID**, not over frames, and publishes the design effect as
a result in its own right — because the correct comparison between two datasets depends on
it and the published claim has no interval at all.

## Who this is for

1. **Someone about to buy or train on the corpus.** They need to know what the quality figure
   means on the batch they are getting, not on one 10k sample from November 2025. They run
   the instrument.
2. **A researcher comparing egocentric datasets.** They need to know whether a cross-dataset
   quality gap measures the data or the judge. That is the domain-bias experiment.
3. **Build AI.** A vendor selling SLAs on quality cannot self-certify them. An independent,
   cheap, repeatable measurement is the thing that turns a marketing number into a
   guarantee — and if the numbers hold, the outcome is their claim, confirmed, with intervals
   they did not have.

## Map

| | |
|---|---|
| What is committed before any result is seen | `docs/PRE-REGISTRATION.md` |
| The annotation rules their prompt still leaves undefined | `docs/RUBRIC.md` |
| What reading their published artifacts established, before any experiment | `docs/UPSTREAM-FINDINGS.md` |
| The protocol, experiment by experiment, with its cost | `docs/METHOD.md` |
| The literature, and the novelty gate | `docs/SURVEY.md` |
| What vernier does not measure | `docs/COVERAGE.md` |
| Attacks on vernier's own findings | `docs/RED-TEAM.md` |
| Provenance and what it limits | `docs/ETHICS.md` |
| Module boundaries | `docs/ARCHITECTURE.md` |
| Data contracts | `CONTRACTS.md` |
| Reproducing all of it | `docs/REPRODUCTION.md` |
| What is inherited, and from where | `docs/LINEAGE.md` |
| Decisions and what would reverse them | `docs/DECISIONS.md` |
| Where the work currently stands | `docs/HANDOFF.md` |

Apache-2.0.
