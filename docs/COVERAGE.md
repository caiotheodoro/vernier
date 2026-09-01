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
| How wide are they, honestly, given clustered frames | Tested — E4, cluster bootstrap over `worker_id` |
| Does the judge agree with a human applying a written rubric | Tested — E4, against `RUBRIC.md` |
| Does the figure move when the prompt is reworded | Tested — E5, P0–P7 |
| Is the judge equally accurate across the compared domains | Tested — E6, the decisive experiment |
| Can a cheap open model carry a stated agreement floor | Tested — E7 rung 3, H6. Coverage is reported with every floor; a floor at unstated coverage is meaningless. |
| Is the judge calibrated | **Not testable on the published protocol.** Their response schema returns a bare integer or a `yes`/`no` enum, exposing no confidence. Calibration is measured only under variant P7 and is a property of that variant. H7, `DECISIONS.md` D018. |
| Do the card and the shipped prompt file agree | Tested — E2, hypothesis H1b. They already do not (`UPSTREAM-FINDINGS.md` F2); the experiment measures how much it matters. |
| Can the measurement be re-run by a third party | Tested by construction — an open-weights judge is in the panel |
| **Is the human rater correct** | **Not tested.** One rater. `R100` measures self-consistency, not correctness. |
| **Was the published sample drawn fairly** | **Not testable.** `frame_id` is a bare UUID4 with no corpus linkage, so the sampling frame behind the published figures cannot be inspected by anyone outside the vendor. `UPSTREAM-FINDINGS.md` F9. |
| **The design effect on *their* sample** | **Not measurable.** No grouping variable shipped. Measured on vernier's own corpus draws instead, and the published figure is argued to inherit it. |
| **Are the three judges independent** | **Not tested, and assumed false.** Shared pretraining lineage means panel agreement is an upper bound on reliability. |
| **Does hand visibility predict training value** | **Not tested by Result 1.** It is the premise of the whole metric, and Result 2 is the only part of this project that touches it — kill-gated, and even then only as transfer on one downstream task. |
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
