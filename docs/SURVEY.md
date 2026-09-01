# Survey

**The novelty gate.** Nothing downstream runs until this file answers one question: *has
independent validation of a VLM quality judge on egocentric video already been published?*

## Verdict: PROCEED, narrowed

Completed 2026-08-31, three tracks, background research agents. Every entry carries a
citation. Claims verified by opening the primary source are marked **[V]**; claims resting on
a search summary only are marked **[S]** and are not load-bearing anywhere in this project
until opened.

**The gate is clear.** No published work takes a corpus-level statistic produced by a VLM
judge, collects independent human gold, reports the judge's error as a property of the
*measurement*, and re-estimates the published statistic — by anyone other than the dataset's
own producers. Three adjacent genres exist and all stop short: first-party validation of a
producer's own judge inside a dataset paper; judge meta-evaluation as a subject in itself,
almost entirely on text; and protocol-fidelity audits of benchmarks.

**The narrowing, and it matters.** vernier's contribution is *not* "validate a VLM judge
against humans". That is routine and heavily prior-arted, and presenting it as the headline
would invite an easy rejection. The contribution is **H5 — the cross-corpus judge confound —
together with treating the judge as an instrument that has a design effect.** Experiments E3
and E4 are infrastructure supporting that claim, not the claim. `DECISIONS.md` D020.

## Track 1 — Egocentric vision SOTA, 2023–2026

**Nobody else reports hand visibility or manipulation density as a corpus-level quality
statistic.** The field treats hand and hand-object interaction as *tasks scored against
ground truth* — EgoPCA (2309.02423), Ego-HOIBench, EPIC-Contact, EgoHOIBench/EgoNCE++,
HanDyVQA — never as a descriptive number used to rank corpora. No paper computed hand
visibility for Ego4D or EPIC-KITCHENS-100 as a dataset-comparison figure before Build AI did.

Closest on-domain precedent for validating a VLM annotator on egocentric video:
**EgoSafetyBench (2607.00218)** pairs VLM chunk-labelling with human review of a sample and
reports agreement in an appendix **[S]** — the appendix value could not be retrieved. It is a
different measurement (safety, not hand state) and a partial precedent, but it is what
"validating the judge" looks like in this literature, and Build AI's card has no equivalent.

**LIME (2607.02417) — [REFUTED], and it was the survey's largest claimed novelty risk.**
Track 3 reported it as achieving 91.3% agreement with humans on egocentric video. Opened
directly: it is *"a vision-language camera-motion generator that combines an auto-regressive
observation-gain output with a continuous flow-matching pose head"* — Sun, Li, Yang, Zhang,
Engelbracht, Hong, Cadena, Pollefeys, Blum. Robotics camera motion. **No 91.3% figure, no judge
validation, no human agreement, no relation to this project.**

The claim was tagged `[S]` and the tag did its job: it was checked before it was relied on, and
it was wrong. That is the entire argument for the tagging discipline, demonstrated on this
project's own survey. It is also why every remaining citation is being audited — one
mis-attribution means the base rate is not zero.

General calibration, cited as context rather than as evidence about this vendor:
**MLLM-as-a-Judge (2402.04788)** finds MLLM judges reach only moderate human agreement
(≈53–71% pairwise) even on easier tasks.

**Result-2 fixtures, now fixed.** The standard comparison suite descends from
EgoClip/EgoNCE (2206.01670): EPIC-KITCHENS-100 action recognition (verb/noun/action top-1)
and multi-instance retrieval; Ego4D's EgoMCQ, EgoNLQ, EgoMQ and Long-Term Anticipation;
EGTEA; Charades-Ego.

- **Downstream task:** EPIC-KITCHENS-100 action recognition, **paired with an Ego4D-native
  task (EgoMCQ or LTA)**. Pairing is not optional — EPIC-KITCHENS-100 is one of the three
  audited corpora, so using it alone is circular.
- **Backbone:** **DINOv3 (2508.10104) [V]**, ViT-S/16 or ViT-B/16, frozen. Newest
  well-attested general SSL backbone, strong dense features, no image-text pairing dependency,
  and the small variants run linear probes on a laptop. SigLIP2 is the second comparator; its
  egocentric-domain validation is unconfirmed **[S]**.

**Redundancy risk: low.** No existing work combines auditing this claim, human-validating the
judge, clustered inference, prompt sensitivity, cross-domain judge accuracy, and distillation
into a reusable instrument. **HumanScale (2606.20521)** runs a matched-protocol transfer
comparison of human video versus robot teleop data — adjacent to Result 2, different corpora,
and evidence that transfer-based corpus comparison is a recognised methodology.

## Track 2 — The egocentric dataset landscape

**No egocentric dataset publishes a confidence interval on any headline quality or diversity
statistic. Zero, across every dataset checked.**

**HD-EPIC (2502.04144) is the field's one rigorous agreement pipeline** and must be cited and
distinguished rather than ignored: ≥3 annotators per narration, per-annotator mean temporal
IoU against the others, a hard 0.3 minimum agreement threshold per HIT with re-annotation if
unmet, ground truth merged from the two highest-agreement annotators above IoU 0.5. But it
governs *action-segment timing*, not a model-produced visual-attribute density statistic, and
it reports no interval on any dataset-level number either.

**Ego-Exo4D** gates annotators at ≥98% approval and a ≥90% qualifier — a precondition on who
may annotate, not a reported agreement statistic **[S]**. **EPIC-KITCHENS-100** reports
annotation-density improvements with no agreement figure found; recorded as
*unverified-absence* pending a full-text read. **Ego4D, HOI4D, Assembly101/AssemblyHands,
EgoDex, EgoVerse (2604.07607), EgoLive (2604.23570), HumanNet (2605.06747), H-Tac**: no
interval or agreement statistic found for any dataset-level quality claim.

**No dataset does the thing Build AI's claim would need to be defensible** — a model-labelled
quality metric with human spot-check and a reported model-versus-human agreement rate.

**Clustering: no counter-example found.** No dataset or paper in this survey treats
frames-within-video or clips-within-participant as clustered when computing a dataset-wide
statistic. Every quality figure encountered is a flat rate over the sampled unit, with no
design effect and no clustered standard errors. Recorded as best-effort absence, not proof.

**Ego4D and EPIC-KITCHENS-100 access** — no longer on Result 1's critical path, since the
evaluation release ships their frames (`UPSTREAM-FINDINGS.md` F5), but relevant to Result 2.
Ego4D: click-through licence, ~48 h approval, AWS credentials expiring after 14 days.
EPIC-KITCHENS-100: CC BY-NC 4.0, ~2 working days, and **requires an institutional email — a
personal address is auto-rejected**. That is a live obstacle for an unaffiliated researcher
and is now a Result-2 risk. Neither licence's frame-redistribution terms were read; they must
be before any frame is republished.

**The domain-bias gap is open.** No prior work both compares egocentric datasets on a common
quality metric with a shared labeller *and* tests whether that labeller behaves consistently
across visual domains. Build AI's own comparison is the only instance of the first, and it
does not do the second. **EgoCross (2508.10729)** shows MLLM task performance shifts sharply
across egocentric domains — circumstantial support for the confound, not a demonstration of
it **[S]**.

No public reproduction or criticism of the 96.42 / 76.34 / 91.66 figures was found; the HF
discussion tabs are essentially empty.

## Track 3 — VLM-as-judge validation. The decisive track

### H5 is real in text, and unmeasured in vision

**arXiv 2606.23915 [V]** — an LLM attribution scorer at AUROC 0.90 on one dataset **collapses
to 0.53, chance, on another**, and per-dataset metric rankings invert (τ = −0.64).

**arXiv 2605.06939 [V]** — sharing judge calibration across compared items "can introduce
severe bias, including cases where the comparison estimate points in the wrong direction with
high apparent confidence", with a documented sign reversal on MMLU-Pro.

That is vernier's hypothesis, established in text and untested in vision. The vision
literature has only *uncertainty-width* variation by domain (**2604.25235 [V]**, 40%→70% of
score range), which is not accuracy bias across compared corpora.

### Methodology to adopt rather than invent

| Adopt | For |
|---|---|
| Rao & Callison-Burch **2606.00093 [V]** | The agreement-reporting standard. Their finding is the reason it is adopted: protocol choices alone moved accuracy 0.551→0.899 **and flipped the sign of κ, with no verdict changes** |
| Miller **2411.00640 [V]** | Clustered standard errors. Full text: *"clustered standard errors can be over 3X larger than naive"* |
| PPI / PPI++ / Confidence-Driven Inference **2408.15204 [V]** | Bias-corrected estimation from a small gold sample plus many model labels |
| IPR / PAR **2604.16413 [V]** | Prompt-sweep reporting |
| Trust-or-Escalate **2407.18370 [V]** | The real ancestor of the distilled instrument: a cheap judge with a *provable* human-agreement guarantee |
| **2607.08535 [V]** | Judge-error dependence — a panel buys less than assumed when errors correlate |
| **2503.05965** | Rating-indeterminate rubrics; "active manipulation" is one |

### Four errors this track caught in vernier's own protocol

All four are fixed in `PRE-REGISTRATION.md` v1.2.0. Recorded here because catching them is
what the gate was for.

1. **The cluster bootstrap was the wrong primary estimator.** It corrects variance and leaves
   bias untouched — vernier would have published a rigorously-intervalled wrong number, a
   more sophisticated version of the error it is auditing. **PPI with clustered resampling**,
   not instead of it.
2. **Cohen's κ is uninformative at 96% prevalence** — the kappa paradox. **Gwet's AC1** is
   now the pre-registered primary agreement statistic; κ is reported beside it.
3. **H5's estimand is an interaction, not a main effect** — P(judge *error* | domain).
   It requires **balanced** human gold across all three domains or it is unidentified. The
   `1.1.0` split of 300/150/150 would not have identified it. Now 200/200/200.
4. **Equal frame counts are not equal precision.** Effective N differs across the three
   corpora by up to an order of magnitude — EPIC-KITCHENS-100 has roughly 45 participants
   against Ego4D's ~931. "10,000 frames each" conceals that, and it is **reportable before any
   labelling happens**.

### Two figures refused

The widely repeated "16.8 pp prevalence spread from prompt choice" and "19%→54% neutral"
could not be attributed to any source. **Do not cite either** until sourced.

## What the survey settled

- **Novelty verdict:** proceed, narrowed to H5 plus judge-as-instrument.
- **Backbone:** DINOv3 ViT-S/16 or ViT-B/16, frozen.
- **Downstream:** EPIC-KITCHENS-100 action recognition paired with an Ego4D-native task.
- **Access:** not blocking for Result 1; EPIC's institutional-email requirement is a Result-2
  risk.
- **Prior art to cite and distinguish:** HD-EPIC, EgoSafetyBench, Trust-or-Escalate,
  HumanScale, EgoCross.

## Verification pass, 2026-08-31

Every load-bearing claim opened at source. Quotes are verbatim from the abstracts.

| Paper | Claim | Status |
|---|---|---|
| 2606.23915 | NLI scorer "best on short-claim AttributedQA (AUROC 0.90) collapses to AUROC 0.53 (chance) on long-form LFQA"; rankings invert, "Kendall tau = -0.64, p = 0.031" | **[V]** exact |
| 2605.06939 | "Sharing calibration across compared models is practically attractive but can introduce severe bias, including cases where the comparison estimate points in the wrong direction with high apparent confidence"; "a real-data MMLU-Pro case study with sign reversal". Supplies **J** and **ΔJ** diagnostics | **[V]** exact |
| 2606.00093 | Rao & Callison-Burch confirmed. "protocol choice alone moves reported accuracy from `0.551` to `0.899` and carries `κ` across zero, without altering a single verdict" | **[V]** exact |
| 2607.08535 | "Repeated-sample juries add little when errors are correlated"; reports should carry slices, bias probes, error-dependence estimates, audit trails | **[V]** |
| 2604.16413 | IPR = stability across "semantically equivalent but linguistically varied prompts"; PAR its pairwise rate. "LLM prompt acts as an instrumental measurement while its wording exhibits methodological uncertainty" | **[V]** |
| 2407.18370 | Trust-or-Escalate. "human agreement can be provably guaranteed -- such that the model evaluation aligns with that of humans to a user-specified agreement level" | **[V]** |
| **2607.02417** | LIME — claimed 91.3% human agreement on egocentric video | **[REFUTED]** — robotics camera-motion generator |
| 2411.00640 | Confirmed as an error-bars-for-LLM-evals paper (Miller). The "clustered SEs over 3× naive" figure is **not** in the abstract | **[V] partial** — full text or drop |
| 2607.00218 | EgoSafetyBench's human-validation agreement value is **not** in the abstract | **[S]** — full text or drop |

A full audit of every remaining citation is Wave S of the implementation plan.

## Must be closed before publication

1. ~~Open LIME (2607.02417) in full.~~ **Done — refuted, see the verification pass above.**
2. Open EgoSafetyBench's appendix for its actual agreement value.
3. Full-text check of EPIC-KITCHENS-100's "Rescaling Egocentric Vision" to convert an
   unverified-absence into a confirmed one, or a correction.
4. Read the Ego4D and EPIC-KITCHENS-100 licence texts on frame redistribution before any
   frame is republished.
5. Source or drop the two refused figures.
6. Confirm author attributions for "Chau 2026" and "EgoScale (Niu et al. 2026)", both matched
   on topic and timing rather than by-line.
