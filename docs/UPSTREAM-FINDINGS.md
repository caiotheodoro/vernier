# Upstream findings

Facts established by reading Build AI's published artifacts directly, before any experiment.
Recorded here because several of them **corrected this repository's own earlier
characterisation** of the thing it audits — which is the correction discipline this project
exists to apply, applied first to itself.

Source, pinned: `builddotai/Egocentric-10K-Evaluation` at revision
`d74b7883c998dd360e3f051830fcc792a83985e6`, Apache-2.0, **ungated**. Snapshots and provenance
in `docs/upstream/`.

## F1 — The prompts are not one-liners, and this repository said they were

vernier's first drafts described the quality metric as coming from "a one-line prompt". That
was taken from press coverage and it is **wrong**. The shipped prompts are structured: a role
line, an explicit task, an explicit definition, five bulleted rules, and a constrained answer
format.

**Correction (`docs/DECISIONS.md` D043):** that constrained format is not JSON. The claim above
originally said "a constrained JSON response schema (`hand_count` as INTEGER; `answer` as an
enum of `yes`/`no`)" — conflating the *evaluation parquet's stored column* schema
(`hand_count: int32`, `active_labor: "yes"/"no"` — a real schema, just not a *prompted* one)
with what the prompt actually instructs the model to emit. Read directly, both shipped prompt
files (`docs/upstream/P0a-*`/`P0b-*`) end in a bare-value instruction — "Return only one of: 0,
1, 2. No extra words." and 'Respond only with: "yes" or "no."' — never JSON, in any of P0-P7
(`docs/PRE-REGISTRATION.md`'s P7 confidence extension asks for the bare value plus a
comma-separated confidence number, still not JSON). `judges/base.py`'s two response parsers
were built against the wrong claim above and, until D043, would have misclassified every
correct real answer as `"unparseable"` — caught by an actual live call to the deployed
Qwen3-VL judge, not by inspection.

They are more careful than the secondary sources suggested. The audit's premise survives —
there is still no human gold, no agreement statistic, no interval, no prompt-sensitivity
analysis, and no cross-domain accuracy test — but the characterisation has been corrected
everywhere it appeared. `DECISIONS.md` D014.

## F2 — The card prompt and the shipped prompt file are different prompts

This is a reproducibility defect, found without running anything.

`prompts/active_manipulation.txt` and the prompt printed on the dataset card differ in four
places, verified by word-level diff (`docs/upstream/P0a-*` vs `P0b-*`):

| | Card (`P0a`) | Shipped file (`P0b`) |
|---|---|---|
| Task sentence | "actively **manipulating an object**" | "actively **doing active manipulation**" |
| Definition term | `"Active Manpulation"` *(sic)* | `"Active Manipulation"` |
| Object list | "...materials, components" | "...materials, components, **or workpieces**" |
| Third-party rule | "Ignore **objects held by** other people." | "Ignore **actions performed by** other people." |

The third-party rule is the substantive one: *objects held by* others and *actions performed
by* others are different exclusions, and they disagree on frames where the wearer handles
something another person is also holding — a common occurrence on an assembly line.

**Which prompt produced 91.66% is not recoverable from the published artifacts.** So P0 is
not one prompt. vernier runs both arms, `P0a` and `P0b`, and the gap between them is a
result.

The hand-count prompt is identical across both sources apart from one apostrophe glyph
(`'` vs `’`), which is recorded for completeness and is not expected to matter.

## F3 — Their prompt already resolves four of the rubric's nine ambiguities

The hand prompt states explicitly: count only directly visible hands; do not infer hands
behind objects or out of frame; ignore other people's hands; **any amount of visibility
counts, even fingertips**.

That settles what `RUBRIC.md` v1.0.0 had treated as open, and it retires the planned P3
variant ("adds the instruction to exclude other people's hands") — that instruction is
already in P0. The rubric is revised to v1.1.0 to follow the published rules rather than
restate them as vernier's own resolutions.

**Still undefined in their prompt, and therefore still live:** gloves (never mentioned, in a
corpus of factory work where gloves are near-universal), reflections and screens, motion
blur, and how "in pursuit of a specific goal" interacts with idle grip. The glove variant
survives as the strongest single prompt-sensitivity test.

## F4 — The full comparison table is public, and the gaps are small

The card publishes all three datasets, not just the headline:

| Dataset | Frames | 0 hands | ≥1 hand | 2 hands | Active manipulation |
|---|---|---|---|---|---|
| **Egocentric-10K** | 10,000 | 3.58% | **96.42%** | **76.34%** | **91.66%** |
| Ego4D | 10,000 | 32.67% | 67.33% | 36.95% | 50.07% |
| EPIC-KITCHENS-100 | 10,000 | 9.63% | 90.37% | 61.05% | 85.04% |

**The margin over EPIC-KITCHENS-100 is 6.05 pp on hand visibility and 6.62 pp on active
manipulation.** Against Ego4D the gaps are large and nothing plausible closes them.

This sizes H5 precisely. vernier pre-registered a ≥5 pp cross-domain judge-accuracy
difference as the effect that would matter, before this table was read. A judge-accuracy gap
of that size between factory and kitchen imagery would account for most of the EPIC margin
— so the hypothesis is not a fishing expedition, it is aimed at the exact quantity the
comparative claim depends on. The Ego4D comparison is not similarly threatened, and the
writeup must say so rather than implying the whole table is in question.

## F5 — The evaluation set ships the frames, for all three datasets

`egocentric_10k.parquet` (1.79 GB), `ego4d.parquet` (2.03 GB), `epic_kitchens.parquet`
(1.65 GB) — roughly 180 KB per frame, i.e. the images themselves, Apache-2.0 and ungated.

Three consequences:

1. **Ego4D and EPIC-KITCHENS-100 access is no longer a blocker.** vernier does not need to
   obtain either corpus for the domain-bias experiment; Build AI has already extracted and
   redistributed the exact frames their own numbers were computed on. The pre-registered
   fallback for "if either cannot be obtained" is retired.
2. **Human labelling can run on their frames**, so agreement is measured against the very
   frames that produced the published figures rather than against a re-draw. The domain-bias
   arms lose their sampling ambiguity entirely.
3. **Total download is ~5.5 GB, not 16.4 TB.** The whole audit of the published claim is
   affordable. The 10K corpus itself is still only touched for the sampling-design arm.

## F6 — There is no `builddotai/Egocentric-1M` on Hugging Face

Queried directly: **404, not 401.** The org hosts exactly four datasets — `Egocentric-10K`,
`Egocentric-100K`, and the two evaluation sets. A third-party repo `easpeeder/Egocentric-1M`
exists and is unaffiliated as far as can be determined.

The April 2026 "Egocentric-1M" announcement therefore has no public Hugging Face release
under the vendor's org at the time of writing. vernier makes no claim about why; it records
that the artifact could not be found, and every figure names the release it was measured on.

This also settles a `COVERAGE.md` open question: there is no public release through which any
part of the advertised 3D-pose MPJPE guarantee could be independently checked.

## F7 — Download figures, corrected

Earlier drafts cited "1.95M downloads" for Egocentric-100K, taken from a rendered web page.
The Hub API reports **`downloads` = 164,868 for Egocentric-100K and 34,519 for
Egocentric-10K**, which is the last-30-days figure. The evaluation sets, which contain the
actual quality claim, have **256 and 203**.

That last pair is the interesting number: **the quality claim is downloaded roughly a
thousand times less often than the corpus it justifies.** Whatever the all-time totals are,
the corpus is being consumed far more than the evidence for it is being examined.

Every download figure in this repository now names its definition and its source.

## F8 — The response schema forecloses calibration as originally planned

Both prompts constrain the model to structured output — an integer, or a `yes`/`no` enum.
There is no confidence field and no logprob exposure through that schema.

So calibration cannot be measured on the published protocol without changing the prompt,
which would no longer be the published protocol. vernier reports calibration only for the
variant that requests a confidence value (the planned P7), states clearly that it is a
property of that variant and not of Build AI's measurement, and lists calibration-under-P0 in
"what could not be checked".

## F9 — The evaluation frames cannot be traced back to the corpus

`frame_id` in all three evaluation parquets is a **bare UUID4** — e.g.
`cc94d1f8-749a-400f-82e1-de35158cfc18` — carrying no factory, worker, clip or timestamp
component. Schema, read from the parquet footers:

```
frame_id        string        # UUID4
image           struct<bytes: binary, path: string>
source_dataset  string
hand_count      int32
active_labor    string        # "yes" / "no"
```

Two consequences, both load-bearing:

1. **The published sample is not auditable against the corpus.** Nobody outside Build AI can
   determine which clips, workers or factories the 10,000 frames came from, so nobody can
   check whether the sample was uniform, stratified, or concentrated in a handful of sites. A
   quality figure whose sampling frame cannot be inspected has to be taken on trust.
2. **Clustering is impossible on the evaluation arms.** vernier's strongest statistical
   argument — that 10,000 frames from 2,153 workers are not 10,000 independent observations —
   cannot be *demonstrated on their frames*, because the grouping variable was not shipped.

The design-effect result therefore moves to vernier's own corpus draws (`S10k-U`, `S10k-S`),
where `factory_id` and `worker_id` are recoverable from the corpus layout. The finding is then
stated in the only form the evidence supports: **the design effect is measured in the corpus
the published sample was drawn from, and any interval on the published figure inherits it.**
H2 is amended accordingly. This is weaker than measuring it directly on their sample, and the
writeup says so.

Everything the parquets *do* carry is a gift: the images, and Build AI's own per-frame
`hand_count` and `active_labor` labels. Human gold can be compared against the exact published
labels without re-calling any judge at all.

## F10 — The 100K evaluation set removed `frame_id`, deliberately

The Hub commit history for `builddotai/Egocentric-100K-Evaluation` contains, on 2025-12-09:

```
19:35  Upload egocentric_100k.parquet
19:48  Delete egocentric_100k.parquet
19:51  Add egocentric_100k.parquet without frame_id
```

The file was uploaded, deleted, and re-uploaded with the identifier column removed. Its schema
confirms it: `image`, `source_dataset`, `hand_count`, `active_labor`, and no `frame_id`.

The same history shows the repository was created by `Duplicate from
builddotai/Egocentric-10K-Evaluation`, and that `ego4d.parquet` and `epic_kitchens.parquet`
were deleted and replaced.

Also worth stating plainly: **the 100K evaluation parquet has 10,000 rows.** The quality claim
attached to a 100,000-hour release rests on a 10,000-frame sample, exactly as the 10K release
did. That is a defensible sampling decision and not a criticism on its own — but it is not
what a reader skimming "Egocentric-100K Evaluation" would assume, and no interval accompanies
it.

vernier makes no claim about *why* the identifier was removed. It records that reproducibility
of the quality claim **regressed between releases**, that the regression is visible in the
vendor's own commit log, and that it is trivially fixable — which is the most useful form this
finding can take.

## F11 — The prompt files were versioned, then the version was dropped

Same repository, 2025-11-10:

```
14:17:29  Rename prompts/active_labor_v1.txt to prompts/active_manipulation.txt
14:17:51  Rename prompts/hand_count_v1.txt   to prompts/hand_count.txt
```

The prompts carried a `_v1` suffix and lost it. The dataset card was edited **57 times** that
day, the last README edit landing at 14:02 — twenty-five minutes *before* the prompt rename —
and the three parquets were uploaded afterwards, between 15:26 and 15:37.

This does not establish which prompt produced the published numbers, and vernier does not
assert that it does. It does mean the card text and the shipped file were last touched at
different points in a rapid editing session, which is the ordinary way F2's divergence
happens, and is worth stating so the finding reads as a packaging defect rather than something
worse. Both remain primary arms.
