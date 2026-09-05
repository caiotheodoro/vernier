# Coverage

What vernier measures, and — the half that matters — what it does not. An audit that
enumerates only its findings misleads by omission.

Written in the vocabulary of Build AI's own advertised guarantee rather than vernier's, so
that a reader can see exactly how much of the claim is touched.

## The advertised SLA, axis by axis

Build AI's site sells "SLA guarantees on **3D pose MPJPE**, **diversity**, and **quality**".

| Axis | Covered | Why |
|---|---|---|
| **Quality** | **Yes, on the published operationalisation.** | Their quality claim *is* the hand-visibility and manipulation-density figures. vernier validates the judge that produces them, puts intervals on them, tests their prompt sensitivity, and tests whether the cross-domain comparison is sound. |
| **Diversity** | **Partially.** | The public metadata supports measuring distribution over factories, workers, clip durations and worker-hour skew — real diversity structure. It does **not** support measuring task, object, or action diversity, which are unlabelled. vernier reports the former and is silent on the latter. |
| **3D pose MPJPE** | **No, and no public release could change that.** | The public releases ship metadata and per-worker fisheye intrinsics, not pose annotations. There is no ground truth against which MPJPE could be independently computed. `builddotai/Egocentric-1M` does not exist on the Hub (404; the org hosts four datasets), so the open question from scoping is closed — `UPSTREAM-FINDINGS.md` F6. |

**So: one axis of three, plus part of a second.** Any summary of this project that implies it
audited "the SLA" is wrong, and this table exists to make that hard to do by accident.

## Within the quality axis, what is and is not tested

| | Status |
|---|---|
| Do the published figures reproduce under their own protocol | Tested — E2 |
| How wide are they, honestly, given clustered frames | Tested — E4. `S10k-U`/`S10k-S` cluster bootstrap over `worker_id`; Build AI's evaluation frames (`P2k`, `G200-*`) carry no `worker_id` and report an iid interval labelled as a lower bound instead (`UPSTREAM-FINDINGS.md` F9, D031) |
| Does the judge agree with a human applying a written rubric | Tested — E4, against `RUBRIC.md` |
| Does the figure move when the prompt is reworded | Tested — E5, P0–P7 |
| Is the judge equally accurate across the compared domains | **Partly.** H5's error-rate comparison on the gold sets, n=33/30. E6's model was never fitted — see below |
| Can a cheap open model carry a stated agreement floor | Tested — E7 rung 3, H6. Coverage is reported with every floor; a floor at unstated coverage is meaningless. |
| Is the judge calibrated | **Not testable for Build AI's judge; measured for the open one.** Their response schema returns a bare integer or a `yes`/`no` enum, exposing no confidence, so nothing can be said about the judge behind the published figure. The self-hosted judge exposes an answer-token logprob on every call, so H7 is read under `P0b` itself (`DECISIONS.md` D060): ECE 0.15 / 0.06, with 99% of frames in one confidence bin under greedy decoding, a weak curve by construction. |
| Do the card and the shipped prompt file agree | Tested — E2, hypothesis H1b. They already do not (`UPSTREAM-FINDINGS.md` F2); the experiment measures how much it matters. |
| Can the measurement be re-run by a third party | Tested by construction — an open-weights judge is in the panel |
| **Is the human rater correct** | **Not tested.** One rater. `R100` measures self-consistency, not correctness. |
| **Is the judge equally accurate across domains, as E6 specified** | **Not tested.** `docs/METHOD.md` E6 calls this the decisive experiment and specifies a model, `judge_correct ~ domain + task`, with cluster-robust intervals. That model was never fitted and `make domain-bias` is unwired. What exists is H5: two raw error rates (Egocentric 9.1%, EPIC-KITCHENS-100 3.3%) and the gap between them, at n=33 and n=30, with no interval on the difference and no interaction term. The row above read "Tested — E6" for longer than it should have (`docs/DECISIONS.md` D082). |
| **Was the published sample drawn fairly** | **Not testable.** `frame_id` is a bare UUID4 with no corpus linkage, so the sampling frame behind the published figures cannot be inspected by anyone outside the vendor. `UPSTREAM-FINDINGS.md` F9. |
| **The design effect on *their* sample** | **Not measurable.** No grouping variable shipped (`UPSTREAM-FINDINGS.md` F9). Measured on vernier's own corpus draws instead (D072: 1.25-1.66 across two arms and three tasks, below H2's pre-registered 2), and the published figure is argued to inherit it, never asserted to have been measured. |
| **Are the judge arms independent** | **Not tested, and assumed false.** Written when the panel was three live judges; post-`docs/DECISIONS.md` D042 it is Qwen3-VL live plus Build AI's own frozen `gemini-2.5-flash` labels as a second arm (`docs/REVIEW.md` point 2) -- shared pretraining lineage between the two model families is unverified either way, so agreement between them is still treated as an upper bound on reliability, not a measure of it. |
| **Has the live judge been pretrained on the compared domains** | **Not tested.** EPIC-KITCHENS-100 and Ego4D are public and plausibly in Qwen3-VL's pretraining mix; Egocentric-10K is gated and released after most public pretraining cutoffs. A real confound on H5, disclosed but not probed (`RED-TEAM.md` A15). |
| **Does hand visibility predict training value** | **Not tested, and now will not be.** It is the premise of the whole metric; Result 2 was the only part of this project that touched it and is dropped (`docs/DECISIONS.md` D048) -- the raw-corpus adapter now exists (D071), but EPIC-KITCHENS-100 needs an institutional email this project lacks, and the evaluation release ships no downstream-task labels regardless; either alone is sufficient. Stays untested, in those words. |
| **Is the corpus representative of factory work generally** | **Not tested.** 85 factories, sampling frame unknown, and no population definition is published to compare against. |
| **Video-level or temporal quality** | **Not tested.** Every figure here is per-frame, because the published metric is per-frame. Stability, coverage of a full task, and clip-level redundancy are untouched. |
| **Near-duplicate and redundancy rate** | **Not tested in v1.** Cheap and plausible as a follow-up; out of scope now so the pre-registration stays honest about what was planned in advance. |

## What a clean result would and would not license

If every hypothesis fails to find a problem, the licensed conclusion is narrow: *under one
sampling design, on one release, at one point in time, the published per-frame quality
figures reproduce, and the judge behind them agrees with one rater applying one rubric.*

It would not license "the dataset is high quality", "the SLA is verified", or "the corpus
trains better models than Ego4D". Those are three different claims and vernier tests none of
them.
