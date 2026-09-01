# Lineage

What vernier inherits, from where, and what is new. Written so a reader can tell which parts
of this project have been exercised before and which are being attempted for the first time.

## From `assay` — the audit form

- **The card.** `assay` emits an Environment Card: a verdict where every claim is tied to the
  probe that produced it, machine-readable, digest-carrying, exiting nonzero when the verdict
  is not clean. vernier's `MeasurementCard` is the same object aimed at a data product.
- **"What could not be checked" as a first-class section.** An empty finding list must never
  read as a clean bill of health. This is the single most transferable idea in the lineage.
- **The self-audit obligation.** `assay` turned its own instruments on itself and published
  the result: twelve of its own claims broke, three real behavioural bugs fell out, and the
  breakage is published unedited. `RED-TEAM.md` inherits that obligation and opens before any
  result exists.
- **Publishing negative results as results.** `assay`'s GRPO-trained Challenger does not beat
  the scripted floor, and says so in the README. vernier's H1-holds case is the same shape:
  a confirmation published as a confirmation, not reframed.
- **Pre-registration before corpus change.** `assay/docs/PRE-REGISTRATION.md` commits
  arithmetic before the corpus grows. vernier commits its whole protocol before the first
  frame is fetched, which is stricter, because the oracle here is a person.
- **Publishing what each check cost.** `assay/docs/METHOD.md`'s convention, carried into
  `METHOD.md`.

## From `suture`

The distillation recipe: Qwen3-VL, 4-bit LoRA, images in and structured output out, evaluated
on a held-out seed. `suture` clears 0.95 recall and 0.95 precision on a two-page-image
discrepancy task; the training and evaluation shape transfers directly to rung 2 of E7.

Also `CONTRACTS.md` as a document that exists before code.

## From `specula`, `plumb`, `habeas`

The shared `docs/methodology.md` — seeded synthetic generator, deterministic
verifier-as-oracle, RLVR — and the Modal/GCP free-credit workflow that makes a small
fine-tune affordable. `methodology.md` here records precisely where that oracle model breaks
down and what replaces it.

## From `reconforge` and `lossbench`

Severity-weighted rather than raw scoring, calibration reported alongside accuracy, and the
habit of retracting a headline in place when it does not survive scrutiny — `reconforge`'s
README carries its own retraction above the number it retracts.

## From `readapt`

Computer vision and accessibility, from the degree work: a CelebA-trained model estimating a
reader's level of visual impairment, with the reader adapting to it. Not used in Result 1 or
2; it is the background that makes the accessibility direction a genuine continuation rather
than a pivot.

## From the literature, adopted rather than invented

`SURVEY.md` Track 3 replaced four pieces of home-made methodology with published ones. Recorded
here because "we invented our own estimator" is a smell, and because the survey catching these
is the strongest evidence the gate was worth running.

| Adopted | Replaces | Source |
|---|---|---|
| Prediction-powered inference | A cluster bootstrap used as the primary estimator, which fixes variance and leaves bias | 2301.09633 (corrected — Wave S caught 2408.15204 mis-cited as this paper; that id is Confidence-Driven Inference, a related refinement, see `DECISIONS.md` D030) |
| Gwet's AC1 | Cohen's κ as headline, unusable at 96% prevalence | 2606.00093 |
| Clustered standard errors, framed as design effect | An informal argument that frames are not independent | Miller 2411.00640 |
| IPR / PAR | An ad-hoc prompt-sweep summary | 2604.16413 |
| Abstention cascade with an agreement floor | Plain distillation reporting teacher fidelity | 2407.18370 |
| J and ΔJ calibration-instability diagnostics | An unmeasured assertion that the comparison may be confounded | 2605.06939 |

**Trust-or-Escalate (2407.18370) supplies the instrument's mechanism, not just its ancestry.**
Selective abstention with a provable floor: confidence estimation plus a cascade, guaranteeing
agreement "to a user-specified agreement level". vernier applies it to a corpus statistic rather
than to pairwise judging — the estimand differs, the mechanism is theirs, and D026 records the
adoption.

**HD-EPIC (2502.04144)** is the field's one rigorous inter-annotator-agreement pipeline and is
cited and distinguished, not ignored: it validates action-segment *timing* with ≥3 annotators,
which is a different object from a model-produced corpus-level statistic.

## What is new here

- **The audited object is a data product, not a model or an environment.** No sibling
  repository has audited a vendor's published dataset statistic.
- **A human oracle.** Every sibling used a program. This is the first time ground truth is an
  interpretation, and the pre-registration and rubric exist to carry that weight.
- **Clustered inference and bias correction together.** Design effects over `worker_id` have
  not appeared in the sibling line, and no sibling has had to debias an estimate produced by an
  unreliable labeller. PPI plus clustered resampling is new to this line of work.
- **Distillation as instrumentation.** `suture` distils to *do a task*. vernier distils to
  *measure*, deliberately reproducing the teacher's errors — a different objective, and the
  reason human gold is held out rather than trained on.
- **Cross-domain judge bias.** No sibling has had to ask whether the measuring instrument
  reads differently on different subjects. It is the experiment most likely to produce
  something the field has not seen.
