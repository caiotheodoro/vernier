# Provenance, and what it limits

This project measures a dataset of recorded human beings at work. That fact constrains what
can be concluded and how the material is handled. This document records what is knowable from
the public release, what is not, and the limits both place on every finding.

It is scoped to the research. It takes no position on Build AI's collection practices, and it
draws no conclusion the public artifacts do not support.

## What the public release states

From the dataset cards and the vendor's own description:

- 10,000 hours of egocentric video from 2,153 workers across 85 factories (Egocentric-10K);
  100,000 hours from 14,228 workers, mean ~7 hours each (Egocentric-100K).
- Captured on the vendor's own head-mounted devices in production environments — assembly,
  sorting, packaging, machining.
- Released under Apache-2.0, gated on the downloader providing contact information.
- Per-clip metadata: factory identifier, worker identifier, video index, duration, resolution,
  frame rate, file size, codec. Per-worker camera intrinsics.

## What the public release does not state

Recorded because absent information bounds the conclusions, not to imply anything about what
is absent:

- The consent instrument used, its language, or whether it was written or verbal.
- Whether recorded workers were compensated for downstream commercial use.
- Whether workers could decline without consequence.
- Whether faces, voices or identifying context of non-consenting third parties appear.
- The population the 85 factories were sampled from, or how sites were selected.
- Retention, deletion, and withdrawal policy.

## The limits this places on vernier's findings

1. **No claim about representativeness.** With no published population definition or site
   selection method, nothing here can say the corpus represents factory work generally. This
   is recorded in `COVERAGE.md` as untested.
2. **No claim about consent, compensation, or labour practice.** vernier has no evidence
   either way and will not infer from absence. Reporting on egocentric collection elsewhere
   in the industry exists and is not evidence about this vendor.
3. **Worker identifiers are used only as statistical clusters.** `worker_id` is load-bearing
   for every interval in this project because frames from one person are not independent
   observations. It is never used to characterise an individual, and no per-worker result is
   published.
4. **No frames are republished.** Human labelling happens locally. The released artifacts
   contain frame *identifiers* and labels, never image content, so no worker's likeness is
   redistributed by this project. Anyone reproducing the work obtains the frames from the
   vendor under the vendor's own terms. For Ego4D specifically this is not just policy but a
   licence requirement: its terms restrict redistribution to "a research publication(s), an
   academic publication(s), or any website through which such publication(s) is made
   available" (`SURVEY.md`, Wave S) — a standalone repository redistributing raw frames would
   violate it. EPIC-KITCHENS-100's CC BY-NC 4.0 is more permissive but is held to the same
   no-republish policy here regardless.
5. **No attempt to identify anyone.** No face recognition, no re-identification across clips,
   no linkage to any external source. The rubric's `other-person` tag exists to *exclude*
   third parties from the hand count, not to study them.

## The one thing this project does say

A quality statistic computed over recordings of identifiable people should carry an interval
and a validated oracle, for the same reason any measurement used to make a claim should. That
is a methodological position, not an ethical accusation, and it is the whole of vernier's
argument.

## Conflict of interest

The author of this repository has an interest in the vendor whose work is measured being
aware of it. That interest is disclosed here, and structurally contained: the protocol,
hypotheses and stopping rules are frozen in `PRE-REGISTRATION.md` before any result is seen,
so no finding can be shaped by how it would be received. `RED-TEAM.md` A12 states the
containment and its limits.
