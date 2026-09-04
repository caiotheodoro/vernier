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
(`docs/DECISIONS.md`, D001–D069), and the result is a machine-checked card that exits nonzero
unless every claim is backed by a record.

## What was done

- **One open judge**, `Qwen/Qwen3-VL-8B-Instruct-FP8`, self-hosted on Modal, temperature 0,
  seed pinned, prompts verbatim from Build AI's own dataset card. Their original judge is
  retired for new API keys; their per-frame labels ship in the evaluation parquet, so the
  comparison runs against those.
- **Human gold**: 93 frames labelled by one rater against a written rubric, balanced across
  the three corpora, plus a blind re-label of 34 of them at least a week later.
- **Live judge calls**: 10,000 frames × 2 prompt arms on `Egocentric-10K-Evaluation`; the same
  on `Egocentric-100K-Evaluation`, their current release; 2,000 frames × 8 prompt variants;
  600 gold frames. Judge cost for the four 10k passes: $17.63 (`data/e2_full_n10000.json`,
  `data/e2_100k_eval.json`).
- **Statistics**: Gwet's AC1 with bootstrap intervals for agreement; PPI++ for prevalence, so
  the interval is valid however biased the judge is; ECE for calibration.

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

PPI++-corrected active-manipulation prevalence on Egocentric-10K: **80.8%, 95% CI
[70.1, 91.6]**, against a published 91.7%. Judge alone says 90.0%; the human labels pull it
down because every judge error in the gold set is a false positive (the judge says
"manipulating" when the rater says "holding"). The interval is wide because n = 33 gold frames
on this arm, and it is a lower bound on the true width because the evaluation release ships
no worker id to cluster over.

**The rubric is decidable.** Intra-rater AC1 0.876 (hand count) and 0.904 (manipulation) on
34 blind re-labels, against a pre-registered gate of 0.70. The audit is not deferred.

**Judge–human agreement is high, and higher on the harder task.** AC1 0.795 [0.687, 0.894]
on hand count, 0.899 [0.807, 0.969] on manipulation. The pre-registered prediction was the
reverse; the data says otherwise.

**What did not hold, said plainly.** Domain bias (H5): judge error on manipulation is 9.1%
on Egocentric frames and 0.0% on EPIC-KITCHENS frames at n = 30–33 per arm — reversed from
the prediction and underpowered by the project's own power analysis; not a finding either
way. Prompt sensitivity (H3): 1.25 pp spread across manipulation prompts vs 0.25 pp across
hand-count prompts — direction right, magnitude under the 5 pp bar
(`data/e5_full_n2000.json#H3`). Calibration (H7): ECE 0.15 / 0.06, but 99% of frames land in
one confidence bin under greedy decoding, so the curve is degenerate by construction.
Distillation (H6): a DINOv2-small linear probe reaches 0.69 fidelity to the teacher against a
0.90 target, and the abstention cascade cannot reach a 0.80 floor at 95% confidence on 46
calibration frames (`data/rung1_distillation.json`). The probe is published anyway, labelled
as a negative result.

## What this means for someone buying the corpus

The published number is not wrong in any way this work can show. It is a point without an
interval, produced by a judge that over-calls manipulation on the frames a human looked at,
and the honest range for the figure on the batch you would buy is roughly 70–92%. The
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

No frame is redistributed anywhere above. One rater. n = 93. Every limitation is in
`docs/RED-TEAM.md`, written before the results existed.
