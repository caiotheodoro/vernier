---
title: vernier
emoji: 📏
colorFrom: gray
colorTo: blue
sdk: static
app_file: index.html
pinned: false
license: apache-2.0
short_description: Their quality number, with error bars, frame by frame
datasets:
  - builddotai/Egocentric-10K-Evaluation
  - caiotheodoro/vernier
tags:
  - evaluation
  - dataset-audit
  - egocentric
---

# vernier

Build AI publishes a quality figure for its egocentric factory video: 96.42% of frames show a
hand, 91.66% show active manipulation, judged once by `gemini-2.5-flash`. No human label, no
interval, no test that the judge scores a factory floor and a home kitchen the same way.

This page is the measurement of that judge, frame by frame. Pick a task and a corpus and the
scale shows three things at once: what was published, what an independent open judge says on
the same frames, and what the figure becomes once 93 human labels correct it — with its 95%
interval. Every count on the page opens the frames behind it, because a number you cannot look
through is the problem this project exists to fix.

Frames are fetched live from Hugging Face's dataset server. **No frame is copied into this
Space or into the dataset release** — vernier redistributes identifiers, labels and statistics
only.

## Not here, and why

- **Pose and a video timeline.** The evaluation release ships no pose annotations and no clip
  or worker ids, so there is nothing to lay on a timeline and no way to cluster an interval by
  worker.
- **"Measure your batch" — upload frames and judge them live.** That needs the Qwen3-VL
  endpoint warm and open to this page; it is the next thing, not this thing.
- **The full 10,000-frame slice.** Per-frame judge records exist for the 600 gold frames; the
  10k runs are committed as aggregates.

## Where the rest is

- Labels, membership, judge output, every result: [`caiotheodoro/vernier`](https://huggingface.co/datasets/caiotheodoro/vernier)
- The distilled probe, published as the negative result it is: [`caiotheodoro/vernier-rung1-probe`](https://huggingface.co/caiotheodoro/vernier-rung1-probe)
- Code, pre-registration, decision log, measurement card: [github.com/caiotheodoro/vernier](https://github.com/caiotheodoro/vernier)

One rater, n = 93. Every limitation is written down in the repository's `docs/RED-TEAM.md`,
which was opened before any result existed.

Apache-2.0.
