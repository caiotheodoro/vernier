# Contracts

Every record vernier writes, fixed before any code exists. Schemas are the seam between
modules described in `docs/ARCHITECTURE.md`; changing one is a decision and belongs in
`docs/DECISIONS.md`.

Two rules apply to all of them:

1. **Every record carries its provenance.** Which sample, which revision, which judge,
   which prompt variant, which rubric version. A number whose origin cannot be reconstructed
   is not publishable.
2. **Absence is explicit.** A judge that refused, timed out, or returned unparseable output
   is recorded as such and excluded from the denominator with its reason. Silently dropping
   it inflates agreement, and that is exactly the class of error vernier exists to catch.

## `FrameRef` — the unit of everything

```json
{
  "frame_id":      "ego10k/f0051/w00243/v0007/000418",
  "corpus":        "egocentric-10k",
  "corpus_rev":    "<hf revision sha, recorded at draw time>",
  "factory_id":    "0051",
  "worker_id":     "00243",
  "clip_id":       "0007",
  "frame_index":   418,
  "timestamp_s":   13.933,
  "width":         1920,
  "height":        1080,
  "fps":           30.0,
  "codec":         "hevc",
  "sample":        "S10k-U",
  "stratum":       "<stratum label from the pre-registered frame>",
  "why_no_provenance": null
}
```

An evaluation-arm frame (`E10k-ego`, `P2k`, `G200-ego`, ...) instead carries:

```json
{
  "factory_id":    null,
  "worker_id":     null,
  "clip_id":       null,
  "timestamp_s":   null,
  "fps":           null,
  "codec":         null,
  "why_no_provenance": "bare UUID4 frame_id, no provenance columns in Build AI's evaluation parquet -- docs/UPSTREAM-FINDINGS.md F9"
}
```

`worker_id` is load-bearing: it is the **cluster unit** for every interval vernier reports.
For Ego4D and EPIC-KITCHENS-100 the cluster unit is that corpus's participant identifier,
recorded in the same field with `corpus` disambiguating it.

**`factory_id`, `worker_id`, `clip_id`, `timestamp_s`, `fps`, and `codec` are nullable, and
null together, not individually.** Build AI's evaluation parquets (the `E10k-*`, `P2k`, and
`G200-*` samples) ship `frame_id` as a bare UUID4 with none of the first four fields
recoverable (`docs/UPSTREAM-FINDINGS.md` F9), and ship extracted still frames with no source
video referenced at all, so `fps`/`codec` have nothing to report either (`docs/DECISIONS.md`
D040 — the real parquet schema was verified live and carries no video-level column). A
validator enforces that either all six are present or all six are null, never a partial mix,
and requires `why_no_provenance` to be set whenever they are null. Corpus draws (`S10k-U`,
`S10k-S`) carry full provenance and leave `why_no_provenance` null. `width`/`height` are never
null — they are always recoverable by decoding the frame image itself, independent of source
video metadata. Any analysis over a frame with null provenance fields has no cluster unit and
must report an iid interval labelled as a lower bound, never a clustered one.

## `JudgeResponse` — one judge, one prompt variant, one frame

```json
{
  "frame_id":       "ego10k/f0051/w00243/v0007/000418",
  "judge":          "gemini-2.5-flash",
  "judge_rev":      "<model version string as reported by the API>",
  "prompt_variant": "P0",
  "hands_visible":  2,
  "manipulation":   true,
  "confidence":     { "kind": "none", "value": null },
  "raw":            "<verbatim response text>",
  "status":         "ok",
  "latency_ms":     412,
  "cost_usd":       0.00031
}
```

- `hands_visible` ∈ {0, 1, 2}. Build AI's prompt admits no other answer; a judge returning
  anything else is `status: "unparseable"` with `hands_visible: null`.
- `status` ∈ {`ok`, `refused`, `unparseable`, `timeout`, `error`}. Anything but `ok` keeps
  `raw` and is counted in the "could not be checked" tally.
- `confidence.kind` ∈ {`logprob`, `verbalized`, `none`}. Judges differ in what they expose;
  calibration is reported per judge and never pooled across kinds. Under `P0a`/`P0b` the
  published response schema exposes nothing, so `kind` is `none` and calibration is
  unmeasurable there by construction — see H7.
- `prompt_variant` ∈ {`P0a`, `P0b`, `P1`…`P7`}. `P0a` is the prompt printed on Build AI's
  dataset card and `P0b` the one shipped in `prompts/`; they differ, and both are primary arms
  (`UPSTREAM-FINDINGS.md` F2). Text is pinned verbatim in `docs/upstream/`. `P1`–`P7` are the
  variants fixed in `docs/PRE-REGISTRATION.md`. No variant is added after the file is frozen.

## `HumanLabel` — the oracle

```json
{
  "frame_id":      "ego10k/f0051/w00243/v0007/000418",
  "rater":         "R1",
  "pass":          "primary",
  "rubric_rev":    "1.0.0",
  "hands_visible": 2,
  "manipulation":  true,
  "edge_case":     ["glove", "tool-occlusion"],
  "difficulty":    "hard",
  "note":          "left hand behind workpiece, thumb visible",
  "labelled_at":   "<iso8601>",
  "seconds_spent": 22
}
```

- `pass` ∈ {`primary`, `retest`}. The `retest` pass is a blind re-label of `R100` at least
  seven days after the primary pass; it yields the intra-rater agreement that stands in for
  the inter-rater agreement a single rater cannot produce. `docs/RED-TEAM.md` states plainly
  why that is a weaker instrument.
- `edge_case` tags come from the closed list in `docs/RUBRIC.md`. New tags mean the rubric
  is incomplete, which is a finding and gets a `DECISIONS.md` entry, not a silent addition.
- `difficulty` is recorded before the judge's answer is ever displayed. The labelling tool
  never shows judge output.

## `AgreementResult`

```json
{
  "comparison":   { "a": "human:R1", "b": "gemini-2.5-flash:P0" },
  "task":         "manipulation",
  "subset":       "G200-ego",
  "n":            300,
  "n_excluded":   4,
  "excluded_why": { "unparseable": 3, "timeout": 1 },
  "raw_agreement": 0.9067,
  "ac1":           0.727,
  "kappa":         0.612,
  "ci":           { "lo": 0.501, "hi": 0.714, "method": "cluster-bootstrap", "clusters": 61, "B": 10000 },
  "design_effect": 2.31
}
```

`ac1` is Gwet's AC1 and is the **primary** agreement statistic; `kappa` is reported beside it
and is never the headline. At a 96% prevalence κ is unstable to the point of sign flips
(`SURVEY.md` Track 3), which is why the choice was pre-registered rather than made after
seeing the numbers.

`ci.method` is `cluster-bootstrap` over `worker_id` wherever a grouping variable exists. On
Build AI's evaluation frames it does not — `frame_id` is a bare UUID4 (`UPSTREAM-FINDINGS.md`
F9) — so those arms use `iid` and the record says so, labelled as a **lower bound on width**.
An iid interval is never reported as though it were the real one.

Headline prevalence estimates additionally carry a `ppi` block: the bias-corrected estimate
from prediction-powered inference over human gold plus judge labels. A cluster bootstrap fixes
variance and leaves bias, and publishing a rigorously-intervalled wrong number is the error
this project exists to catch.

## `PrevalenceEstimate` — the headline number

Referenced by every published proportion.

```json
{
  "corpus":         "egocentric-10k",
  "task":           "manipulation",
  "prompt_variant": "P0a",
  "judge":          "gemini-2.5-flash",
  "naive":          { "value": 0.9166, "n": 10000 },
  "ppi": {
    "value":        0.8931,
    "ci":           { "lo": 0.8612, "hi": 0.9250, "level": 0.95 },
    "n_gold":       200,
    "n_unlabelled": 10000,
    "rectifier":    -0.0235,
    "method":       "ppi++",
    "clustered":    false,
    "cluster_by":   null,
    "why_not_clustered": "frame_id is a bare UUID4; no grouping variable shipped"
  },
  "published":      0.9166
}
```

- `naive` is the uncorrected judge proportion — what Build AI publishes. Always shown, never
  alone.
- `ppi.value` is the bias-corrected estimate of the **true** prevalence, using human gold to
  rectify the judge-labelled sample. `rectifier` is the correction applied; its sign and size
  are the finding.
- `clustered` records whether resampling grouped by participant. Where it is `false`,
  `why_not_clustered` is required and the interval is a **lower bound on width**.
- `published` carries Build AI's figure alongside, so a reader sees all three numbers at once
  without cross-referencing.

## `CalibrationReport`

```json
{
  "judge":      "gemini-2.5-flash",
  "task":       "manipulation",
  "subset":     "G200-ego",
  "confidence_kind": "verbalized",
  "ece":        0.083,
  "bins":       [ { "lo": 0.0, "hi": 0.1, "n": 0, "mean_conf": null, "accuracy": null } ],
  "note":       "empty bins are reported as empty, never merged away"
}
```

## `ProbeResult` — Result 2

```json
{
  "source_corpus":  "egocentric-10k",
  "n_frames":       "<matched across corpora by construction>",
  "backbone":       "facebook/dinov3-vits16-pretrain-lvd1689m",
  "downstream":     "<benchmark fixed by docs/SURVEY.md>",
  "metric":         "<the benchmark's own primary metric>",
  "value":          0.0,
  "ci":             { "lo": 0.0, "hi": 0.0, "method": "cluster-bootstrap" },
  "seed":           777,
  "matched_on":     ["n_frames", "n_clusters", "training_steps"]
}
```

Corpora are compared only at matched size, matched cluster count and matched training
budget. An unmatched comparison measures the sampling, not the data.

## `MeasurementCard` — the published artifact

The card is the deliverable, inherited from Assay's Environment Card. It carries:

- the verdict, and every claim tied to the record that produced it;
- **"What could not be checked"**, with a named reason per item — an empty card must never
  read as a clean bill of health;
- the sample definition, rubric revision, judge revisions and prompt variants used;
- the cluster-bootstrap intervals and the design effect;
- a content digest. A digest identifies a card and catches corruption; it is not
  tamper-evidence, because anyone editing the body can recompute it.
