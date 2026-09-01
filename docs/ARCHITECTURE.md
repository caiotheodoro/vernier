# Architecture

Module boundaries, fixed before code. Each unit has one purpose, a schema at its edge
(`CONTRACTS.md`), and no knowledge of its callers.

```
sampling ──> judges ─────┬──> agreement ────┐
    │                    │                  │
    ├──────> labels ─────┼──> estimation ───┼──> card
    │                    │                  │
    │                    └──> calibration ──┘
    └──> probe                    │
              distil <────────────┘
```

## `sampling`

Draws `S10k-U`, `S10k-S`, `P2k`, the three `G200-*` sets and `R100` per `PRE-REGISTRATION.md`, and
writes membership to disk **before anything else runs**. Emits `FrameRef` records.

Owns: seed handling, stratification, the ≤1-frame-per-clip constraint, the reserve list for
undecodable frames, and the `worker_id` cluster assignment every downstream interval depends
on. Depends on: the HF dataset metadata only. It never decodes a frame it was not asked for.

**Seam:** corpus-specific identifier mapping. Ego4D and EPIC-KITCHENS-100 name their
participant field differently; the adapter normalises into `worker_id` and records the
original in `corpus`.

## `judges`

One adapter per judge behind a single interface: frame in, `JudgeResponse` out. Written when
the panel was three live judges (closed models Gemini/Claude, plus the open Qwen3-VL) differing
only in the adapter; post-`docs/DECISIONS.md` D042 the live panel is Qwen3-VL alone, and
`gemini-2.5-flash`'s retired adapter is replaced by reading its own stored labels directly from
the evaluation parquets (`scripts/published_labels.py`) rather than an adapter at all -- there
is no live call left to adapt.

Owns: prompt-variant substitution, response parsing, `status` classification, cost and latency
accounting, retry policy, and recording `judge_rev` per response. Depends on: `sampling` for
frames, nothing else.

**Never** decides ground truth. A judge is the object of measurement.

**Seam:** confidence extraction. `logprob` from open weights, `verbalized` from the closed
APIs, `none` where neither is available. Calibration is per judge and never pooled across
kinds — the interface must carry the kind, not flatten it to a float.

## `labels`

The human annotation store and the tool that fills it. Presents frames in random order,
records both tasks, edge-case tags, difficulty and seconds spent.

**Hard constraint, enforced here rather than by discipline: the tool has no read path to
`judges` output.** Displaying a judge's answer to the rater would destroy the only ground
truth in the project. The `retest` pass additionally has no read path to the `primary` pass.

## `agreement`

Consumes `JudgeResponse` and `HumanLabel`, emits `AgreementResult`. Raw agreement, Cohen's κ,
Fleiss' κ across the panel, intra-rater κ on `R100`.

Owns Gwet's AC1 as the primary statistic, with Cohen's κ beside it, and the
judge-error-dependence estimate. Every exclusion is counted with its reason and subtracted from
the denominator explicitly; a silent drop here would inflate every number downstream.

It does **not** own intervals. Those belong to `estimation`, because the headline number is a
bias-corrected estimate rather than an agreement statistic, and conflating the two is precisely
the error the survey caught.

## `estimation`

The module the project's credibility now rests on. Consumes `HumanLabel` plus `JudgeResponse`
and emits `PrevalenceEstimate`: the naive judge proportion, the PPI-rectified estimate, and its
interval — clustered over the participant identifier wherever one exists, and explicitly
labelled a width lower bound wherever one does not.

Also owns the design-effect computation on the corpus draws, the only place a grouping variable
is available (`UPSTREAM-FINDINGS.md` F9), and the effective-N comparison behind H8 — the one
output that needs no experiment at all.

**Seam:** `clustered` is a property of the *arm*, not a global setting. A module that silently
defaulted to iid would reproduce the flaw being audited, so the flag is required and the reason
string is required with it.

## `calibration`

ECE with fixed bins, reliability diagrams, per judge and per confidence kind. Empty bins are
reported empty, never merged into neighbours to make a curve look smooth.

## `distil`

Three rungs, in order: a linear probe on frozen features (cheap, laptop-runnable, the baseline
that must be beaten to justify anything more), then a Qwen3-VL LoRA on Modal, then the
**abstention cascade** — confidence estimation, a threshold, and escalation — which is what turns
the model into an instrument with a stated floor (D026).

**Seam:** the cascade's threshold is calibrated against held-out human gold and must never be
tuned on the frames it will later score. The module exposes coverage and floor as a pair; a
caller cannot obtain one without the other, because a floor at unstated coverage is meaningless.
Mechanism pinned in advance (`docs/DECISIONS.md` D049): Learn-then-Test / conformal risk
control, not a bare point-estimate threshold search — the current `distil/cascade.py`
implementation is the pre-D049 version, not yet rewritten to match.

Training targets are `gemini-2.5-flash` P0 labels — the judge, deliberately, not the human
gold. Human gold is the **held-out** evaluation for both the judge and its distillate, which
is the only way to say whether the instrument inherits the judge's errors.

## `probe`

Result 2 — **dropped, `docs/DECISIONS.md` D048; this module is not built.** Would have been
matched frozen-feature probes across corpora, matching on frame count, cluster count and
training budget enforced in code rather than left to the caller, because an unmatched
comparison silently measures the sampling. The gate is never reached: the raw corpus this
project would need is inaccessible, EPIC-KITCHENS-100 needs an institutional email this
project lacks, and the evaluation release ships no downstream-task labels regardless.

## `card`

Emits the `MeasurementCard`: verdict, every claim tied to the record that produced it, "what
could not be checked" with a reason per item, and a content digest. Exits nonzero when the
verdict is not `VERIFIED` — an audit that always exits zero is decoration.

## Known seams

- **Corpus adapters** are the widest seam: three corpora and three identifier schemes.
  Narrower than first assumed -- the evaluation release redistributes the Ego4D and
  EPIC-KITCHENS frames directly, so those two arms need no separate access path
  (`UPSTREAM-FINDINGS.md` F5).
- **Judge version drift** under a stable API name. Mitigated by recording `judge_rev`,
  not prevented.
- **The rubric-to-code gap.** `RUBRIC.md` is prose applied by a person; nothing in the
  architecture can enforce that the rater followed it. `R100` measures whether they did.
