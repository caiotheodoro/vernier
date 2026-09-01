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
annotation-density improvements with no agreement figure found — **[V] confirmed-absence**,
full text read (arXiv 2006.13256). **EgoVerse (2604.07607), EgoLive (2604.23570), HumanNet
(2605.06747)**: no interval or agreement statistic found for any dataset-level quality claim
— **[V] confirmed-absence**, full text and appendices read. **Ego4D, HOI4D,
Assembly101/AssemblyHands, EgoDex, H-Tac**: still *unverified-absence*, out of Wave S's scope,
pending a full-text read.

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
and is now a Result-2 risk.

**Frame-redistribution terms, read in full (closes "must be closed" item 4).**
EPIC-KITCHENS-100 is permissive: CC BY-NC 4.0 permits sharing and adapting with attribution,
non-commercial only. Ego4D is restrictive: its click-through licence limits redistribution to
"distributing or reproducing any images or videos contained in the Database in a research
publication(s), an academic publication(s), or any website through which such publication(s)
is made available" and separately bars any portion of the data from appearing in "any program,
dataset, or product, whatsoever, commercial or otherwise" outside that exception. A standalone
repository redistributing raw Ego4D frames would violate the licence; this is consistent with
— and gives a concrete legal basis for — `ETHICS.md`'s existing no-republish policy.

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
| PPI / PPI++ **2301.09633 [V]** | Bias-corrected estimation from a small gold sample plus many model labels. The correct primary citation — `2408.15204` was mis-cited as this paper; see the verification pass below |
| Confidence-Driven Inference **2408.15204 [V]** | A refinement of PPI (power-tuning parameter λ interpolating human-only and LLM-augmented estimates), cited separately from PPI itself, not as its replacement |
| IPR / PAR **2604.16413 [V]** | Prompt-sweep reporting |
| Trust-or-Escalate **2407.18370 [V]** | The real ancestor of the distilled instrument: a cheap judge with a *provable* human-agreement guarantee |
| **2607.08535 [V]** | Judge-error dependence — a panel buys less than assumed when errors correlate |
| **2503.05965 [REFUTED]** | Was cited for rating-indeterminate rubrics including "active manipulation" — the paper's actual examples are toxic language, factuality, helpfulness, and relevance; no active-manipulation discussion exists. Not adopted; H3's prior-art support rests on IPR/PAR (2604.16413) alone |

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
   corpora by close to two orders of magnitude — EPIC-KITCHENS-100 has **37 participants**
   (confirmed against the primary source, arXiv 2006.13256: "increasing the total number of
   subjects and kitchen environments to 37 and 45 respectively" — the "45" figure previously
   used here was the kitchen/environment count, not the participant count) against Ego4D's
   **923** (confirmed against Ego4D's own site, correcting the prior ~931) and Egocentric-10K's
   **2,153** (already primary-sourced, unchanged). "10,000 frames each" conceals that, and it
   is **reportable before any labelling happens**.

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
| 2411.00640 | Miller. Full text: Table 4 reports `SE_clustered = 1.34` vs `SE_naive = 0.44` on DROP, a 3.05× ratio; "clustered standard errors can be over 3X larger than naive standard errors" | **[V]** — promoted from partial, full text read |
| 2607.00218 | EgoSafetyBench, Appendix A Table 8/9. Chunk-level observed agreement 91.2%, κ=0.744; video-level 90.5%, κ=0.804 (human-vs-human); human-vs-benchmark κ=0.660 (chunk) / 0.799 (video) | **[V]** — promoted from soft, appendix value found. Closes "must be closed" item 2. |
| 2206.01670 | EgoClip/EgoNCE cited as the basis for the full Result-2 fixture suite (EPIC verb/noun/action top-1, multi-instance retrieval, Ego4D EgoMCQ/EgoNLQ/EgoMQ/LTA, EGTEA, Charades-Ego) | **[S]** — the paper supports EgoClip, EgoNCE, EgoMCQ, EPIC-100 multi-instance retrieval, Ego4D NLQ/MQ/OSCC and Charades-Ego, but not the bundled EPIC verb/noun/action top-1, EGTEA, or Long-Term Anticipation claims; it explicitly leaves long-term dependencies to future work |
| 2309.02423 | EgoPCA cited as hand/hand-object interaction scored against ground truth, "never" used as a descriptive corpus-ranking number | **[S]** — the paper does report top-1 accuracy against ground truth, but also quantitatively compares hand-location/pose distributions across datasets for dataset similarity and selection; "never" is too broad |
| 2402.04788 | MLLM-as-a-Judge — "moderate human agreement (≈53–71% pairwise) even on easier tasks" | **[S]** — the paper's actual pairwise agreement is 72–79% (GPT-4V 79.3%, Gemini 72.4%); the 53–71% bracket fits the non-pairwise Score/Batch tasks instead. Qualitative point (moderate, unreliable agreement) holds; the pairwise number is understated |
| **2408.15204** | Cited as "prediction-powered inference (2408.15204)" — vernier's primary statistical estimator (D021) | **[REFUTED as a PPI citation]** — this is *"Can Unconfident LLM Annotations Be Used for Confident Conclusions?"* (Gligorić, Zrnic, Lee, Candès, Jurafsky), which introduces **Confidence-Driven Inference**, a refinement built on top of PPI — it is not the PPI paper. The actual Prediction-Powered Inference paper is **arXiv 2301.09633** (Angelopoulos, Bates, Fannjiang, Jordan, Zrnic). The valid-interval property still holds under either paper; the citation and the "debiases via the human-gold sample" mechanism description need correcting — CDI's mechanism is a power-tuning parameter λ interpolating human-only and LLM-augmented estimates, not the description in `DECISIONS.md` D021 |
| 2502.04144 | HD-EPIC's inter-annotator-agreement pipeline: ≥3 annotators, temporal-IoU, hard 0.3 threshold, best-2 merge | **[S]** — core pipeline confirmed verbatim in the appendix, but best-two merging only applies when pairwise IoU > 0.5; below that, only the single best annotator's label is retained, not a merge |
| **2503.05965** | Cited for "rating-indeterminate rubrics; 'active manipulation' is one," used as prior support for H3 | **[REFUTED]** — the paper's actual rating-indeterminacy examples are toxic language, factuality, helpfulness, and relevance rating tasks. No discussion of active manipulation, hand-counting, or any egocentric-video labelling task exists anywhere in the paper. This citation does not support H3; H3's prior-art support should rest on 2604.16413 (IPR/PAR) alone, not this paper |
| 2508.10729 | EgoCross — "MLLM task performance shifts sharply across egocentric domains," circumstantial support for H5's confound | **[S]** — confirmed as indirect/circumstantial support only, consistent with how it's already framed; not a direct test of the confound |
| 2604.07607 | EgoVerse — listed among corpora with "no interval or agreement statistic found for any dataset-level quality claim" | **[V]** — confirmed absent in full text and appendices; "interval" appears only as an unrelated integration hyperparameter |
| 2604.23570 | EgoLive — same absence claim | **[V]** — confirmed absent; paper reports depth-error and LLM-as-judge caption metrics, no confidence intervals or inter-annotator agreement anywhere |
| 2605.06747 | HumanNet — same absence claim | **[V]** — confirmed absent; paper's only empirical claim is a downstream training-transfer comparison (validation-loss curves), no interval or agreement statistic |
| 2606.20521 | HumanScale — "matched-protocol transfer comparison of human video versus robot teleop data, adjacent to Result 2, different corpora" | **[V]** — confirmed as described: HumanNet-derived egocentric subset vs. aggregated robot corpora, same architecture/post-training/eval splits, methodologically adjacent to Result 2 but different corpora and target |

**EPIC-KITCHENS-100's "Rescaling Egocentric Vision"** (arXiv 2006.13256, Damen et al., IJCV
2022) — the paper the "unverified-absence" claim at lines 88–89 refers to — reports
annotation-density improvements ("+128% more action segments") but **no inter-annotator
agreement statistic of any kind**. **[V] confirmed-absence**, promoted from unverified-absence.
Closes "must be closed" item 3.

Wave S — the full audit above — also closed item 6: neither "Chau 2026" nor "EgoScale (Niu et
al. 2026)" could be reconstructed as supporting any claim in this document. EgoScale (arXiv
2602.16710, Niu et al.) is a human-to-robot manipulation-transfer paper, unrelated to dataset
quality or judge validation; several 2026 papers by an author named Chau exist in egocentric
vision, none about quality auditing or annotation agreement. Both references are dropped rather
than guessed at.

## Must be closed before publication

1. ~~Open LIME (2607.02417) in full.~~ **Done — refuted, see the verification pass above.**
2. ~~Open EgoSafetyBench's appendix for its actual agreement value.~~ **Done — 91.2%/κ=0.744
   chunk-level, 90.5%/κ=0.804 video-level, see the verification pass above.**
3. ~~Full-text check of EPIC-KITCHENS-100's "Rescaling Egocentric Vision".~~ **Done —
   confirmed-absence, no agreement statistic found (arXiv 2006.13256).**
4. ~~Read the Ego4D and EPIC-KITCHENS-100 licence texts on frame redistribution.~~ **Done —
   EPIC-KITCHENS-100 permissive (CC BY-NC 4.0), Ego4D restrictive (publication-context-only
   redistribution), see above.**
5. **Open.** Source or drop the two refused figures — extensive search found no source for
   either the "16.8 pp prevalence spread" or "19%→54% neutral" figures. They remain uncited;
   drop entirely if no source surfaces by publication.
6. ~~Confirm author attributions for "Chau 2026" and "EgoScale (Niu et al. 2026)".~~ **Done —
   neither could be reconstructed as supporting any claim here; both dropped rather than
   guessed at, see above.**

Wave S (this pass) also caught two further mis-citations neither on this list nor previously
flagged: `2408.15204` was cited as the Prediction-Powered Inference paper but is actually
Confidence-Driven Inference, a later refinement (the real PPI paper is arXiv 2301.09633); and
`2503.05965` was cited as supporting H3's "active manipulation is rating-indeterminate" claim
but does not discuss active manipulation at all. Both are corrected above and in `DECISIONS.md`
/ `LINEAGE.md`.
