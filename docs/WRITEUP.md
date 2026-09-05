# Their quality number, with error bars

*Draft for the Hugging Face community blog. Every number below is copied from
`MEASUREMENT_CARD.json` or a `data/*.json` result file; the file is named beside each. If a
number here and the card disagree, the card wins and this file has a bug.*

Build AI sells egocentric factory video with a published guarantee on quality: 96.42% of
frames show at least one hand, 91.66% show active manipulation, and both figures beat Ego4D
and EPIC-KITCHENS-100. The number comes from 10,000 frames labelled once by `gemini-2.5-flash`.
There is no human label behind it, no interval, no prompt-sensitivity check, and no test that
the judge scores a factory floor and a home kitchen on the same scale — which is the
assumption the comparison rests on. The margin over EPIC-KITCHENS-100 is about six points.

vernier measured the judge. The protocol was frozen before any frame was drawn
(`docs/PRE-REGISTRATION.md`), every deviation is a dated entry in a decision log
(`docs/DECISIONS.md`, D001–D081), and the result is a machine-checked card that exits nonzero
unless every claim is backed by a record.

## What was done

- **One open judge**, `Qwen/Qwen3-VL-8B-Instruct-FP8`, self-hosted on Modal, temperature 0,
  seed pinned, prompts verbatim from Build AI's own dataset card. Their original judge is
  retired for new API keys; their per-frame labels ship in the evaluation parquet, so the
  comparison runs against those.
- **Human gold**: 93 frames labelled by one rater against a written rubric, balanced across
  the three corpora, plus a blind re-label of 34 of them. The protocol asked for seven days
  between the two passes; the re-label actually ran a median of 2.4 hours after the first, so it
  measures whether the rubric is applied consistently within a session and does not rule out the
  rater remembering the frame (`docs/DECISIONS.md` D076).
- **The raw corpus, drawn twice**: 10,000 frames uniform over frames (`S10k-U`) and 10,000
  stratified by factory worker-hours, at most one per clip (`S10k-S`), from 19,495 video shards
  (~16 TB) without downloading them: a tar index built from 512-byte headers, then one frame per
  clip via ffmpeg over HTTP range requests. These are the only frames in the project that carry
  a worker id, so the only ones on which an interval can be clustered.
- **Live judge calls**: 10,000 frames × 2 prompt arms on `Egocentric-10K-Evaluation`; the same
  on `Egocentric-100K-Evaluation`, their current release; 2,000 frames × 8 prompt variants;
  600 gold frames; 20,000 raw-corpus frames on a spot GPU. Judge cost for the four
  evaluation-release 10k passes: $17.63 (`data/e2_full_n10000.json`,
  `data/e2_100k_eval.json`); for the two corpus arms, about $7.50 (`docs/DECISIONS.md` D072).
- **Statistics**: Gwet's AC1 with bootstrap intervals for agreement; PPI++ for prevalence, so
  the interval is valid however biased the judge is; ECE for calibration; a cluster bootstrap
  over worker id, against its iid counterpart, wherever a worker id exists.

## What was found

**Their headline mostly replicates. One figure doesn't, on both releases.**
(`data/e2_full_n10000.json#H1`, `data/e2_100k_eval.json#published_comparison`)

| figure | measured | published | diff |
|---|---:|---:|---:|
| 10K, ≥1 hand | 95.4 | 96.4 | 0.97 pp |
| 10K, 2 hands | **82.7** | **76.3** | **6.32 pp** |
| 10K, active manipulation | 91.3 | 91.7 | 0.38 pp |
| 100K, ≥1 hand | 96.1 | 97.0 | 0.86 pp |
| 100K, 2 hands | **85.2** | **79.0** | **6.14 pp** |
| 100K, active manipulation | 92.1 | 92.8 | 0.62 pp |

An independent judge lands within a point on two of three figures, on two releases a year
apart. The two-hands figure is six points off both times, in the same direction. Also
observed while doing this: the Ego4D and EPIC-KITCHENS baselines on the 100K card are
byte-identical to the 10K card's (`data/eval_baseline_comparison.json`) — the comparison
corpora were judged once, in November 2025, and reused.

**With human gold, the manipulation rate has an interval, and the published number sits at
its upper edge.** (`data/wave4_analysis.json#ppi`)

PPI++-corrected active-manipulation prevalence on Egocentric-10K: **85.1%, 95% CI
[77.9, 92.2]**, against a published 91.7%. Judge alone says 90.0%; the human labels pull it
down because every judge error in the gold set is a false positive (the judge says
"manipulating" when the rater says "holding"). The interval is wide because n = 33 gold frames
on this arm, and it is a lower bound on the true width because the evaluation release ships
no worker id to cluster over.

**Does that make their comparison wrong? On this data the honest answer is that we cannot
say.** (`data/margin_exploratory.json`)

What Build AI sells is not a rate but a lead: 6.62 pp over EPIC-KITCHENS-100 on active
manipulation. Correct both sides for judge error against human gold and that lead becomes
-1.02 pp, 95% CI [-11.68, +9.65]. The point estimate changes sign, and the interval still
covers the published figure, so the published margin is not refuted here. It is unresolved.
The hand-visibility lead keeps its sign and loses about half its size: +6.05 pp published,
+3.02 pp corrected, interval [-5.23, +11.26], which also covers the published value. Neither
comparative claim is refuted and neither is confirmed.

This estimand is exploratory. The pre-registration asked a narrower question, whether the
judge's error rate differs by domain, and that one is reported unchanged below. An earlier
revision of this file priced the gap at roughly 42 gold frames per arm. Sixty more labels were
then collected, and the corrected margins moved toward the published figures rather than away.
The price was then found to be wrong: it scaled the whole standard error as one over root n,
when only the gold term shrinks with more labels and the unlabelled pool sets a floor.
Corrected, the manipulation margin needs about 226 gold frames per arm, and the hand-visibility
margin cannot be separated by labelling at any budget, because the floor already exceeds what
separation would take (`docs/DECISIONS.md` D088). More labels made the vendor's number look
better and the price of settling it went up, and both are reported here rather than set aside.

**Their 10,000 frames are not 10,000 independent observations, and the gap is smaller than
pre-registered.** (`data/h2_design_effect.S10k-U.json`, `data/h2_design_effect.S10k-S.json`)

Frames from one worker share scene, lighting, task, gloves and camera. The pre-registration
predicted a design effect of at least 2, and in the next sentence a clustered interval at
least twice as wide as the iid one, which under its own definition is a design effect of 4;
the result clears neither (`docs/DECISIONS.md` D074). Measured at N = 10,000 per arm,
B = 10,000, on both draws (read to two decimals; the bootstrap's own resolution is about ±0.05):

| figure | `S10k-U` | `S10k-S` |
|---|---:|---:|
| ≥1 hand | 1.25 | 1.31 |
| 2 hands | **1.62** | **1.66** |
| active manipulation | 1.27 | 1.29 |

None reaches 2, so H2 fails as stated. All six exceed 1, so the effect is real: an interval
computed as if frames were independent understates its width by 11–22% on this corpus,
equivalently the cluster-aware interval is 12–29% wider. Concretely,
the 2-hands rate on `S10k-U` is 80.8%, iid interval [80.0, 81.6], clustered [79.8, 81.8]. Two
separate draws with different cluster structures land within the bootstrap's own resolution
of each other on every task, and an independent re-run at a different seed reproduced the
structure (`docs/DECISIONS.md` D074). The 2-hands figure carries the largest design effect
on both arms, and it is the same figure the independent judge missed by six points on both
releases; three measurements now single it out, and none explains it.

This is measured on vernier's own draws, not on Build AI's evaluation frames, which ship no
worker id at all. A published interval would inherit this; theirs was never measured, because
there is none.

Building the index also counted the corpus: 2,144 distinct workers against the published 2,153,
with 85 factories, 10,000 hours and 192,903 clips reconciling essentially exactly
(`docs/UPSTREAM-FINDINGS.md` F12). Nine workers, 0.42%, too few to move anything above;
recorded so a reader comparing counts knows why they differ.

**The rubric is decidable within a session.** Intra-rater AC1 0.876 (hand count) and 0.899
(manipulation) on 34 blind re-labels, against a pre-registered gate of 0.70. The audit is not
deferred. The re-label came a median of 2.4 hours after the first pass rather than the
pre-registered seven days, which makes this a weaker check than intended: it shows the rubric
is applied consistently, and it cannot separate that from the rater recalling the frame
(`docs/DECISIONS.md` D076).

**Judge–human agreement is high, and higher on the harder task.** AC1 0.860 [0.791, 0.921]
on hand count, 0.887 [0.815, 0.945] on manipulation. The pre-registered prediction was the
reverse; the data says otherwise.

**What did not hold, said plainly.** Domain bias (H5): judge error on manipulation is 4.8%
on Egocentric frames and 8.3% on EPIC-KITCHENS frames at n = 30–63 per arm — the predicted
direction, 3.57pp against a 5pp bar and underpowered by the project's own power analysis; not a finding either
way. Prompt sensitivity (H3): 1.25 pp spread across manipulation prompts vs 0.25 pp across
hand-count prompts — direction right, magnitude under the 5 pp bar
(`data/e5_full_n2000.json#H3`). Calibration (H7): ECE 0.10 / 0.08, but 99% of frames land in
one confidence bin under greedy decoding, so the curve is degenerate by construction.
Distillation (H6): a DINOv2-small linear probe reaches 0.69 fidelity to the teacher against a
0.90 target, and the abstention cascade cannot reach a 0.80 floor at 95% confidence on 46
calibration frames (`data/rung1_distillation.json`). The probe is published anyway, labelled
as a negative result. Design effect (H2): 1.25–1.66 against a pre-registered 2; real, smaller
than predicted, reported above.

## What this means for someone buying the corpus

The published number is not wrong in any way this work can show. It is a point without an
interval, produced by a judge that over-calls manipulation on the frames a human looked at,
and the honest range for the figure on the batch you would buy is roughly 70–92%. Any interval
on this corpus that treats frames as independent understates its width by 11–22%, and the published figure
has no interval at all. The
instrument that produces that range costs about $9 per 10,000 frames to re-run on any batch,
needs no API vendor, and is public.

For Build AI specifically: the cheapest upgrade to the SLA is an interval. The second
cheapest is a second rater on the 200 frames in `G200-ego` — the one number this project
cannot produce alone, and the dataset release is set up to receive it.

## Where everything is

- Frame-by-frame view: https://huggingface.co/spaces/caiotheodoro/vernier
- Labels, membership, judge output, results: https://huggingface.co/datasets/caiotheodoro/vernier
- The probe: https://huggingface.co/caiotheodoro/vernier-rung1-probe
- Code, pre-registration, decision log, measurement card: https://github.com/caiotheodoro/vernier

The dataset and model releases above redistribute no frame; the 20,000 corpus frames are
identified by clip and frame index only. The Space ships 24 downscaled Egocentric-10K stills,
and `docs/ETHICS.md` §4 says which and why (D073). One rater. n = 93. Every limitation is in
`docs/RED-TEAM.md`, written before the results existed.
