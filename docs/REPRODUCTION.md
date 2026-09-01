# Reproduction

How a third party re-runs this end to end. The standard vernier applies to Build AI's
measurement applies here first: if this document does not let a stranger obtain commensurable
numbers, the project has failed on its own terms.

**Nothing here is runnable yet.** The repository is documentation-only; this file fixes the
contract that the eventual code must satisfy, so that reproducibility is a design constraint
rather than something retrofitted.

## The open-judge-only path is first-class

Two of the three judges are closed APIs. A reproduction route that required paid keys would
reproduce exactly the flaw vernier is auditing, so the open path is primary and must stay
tested:

```
make effective-n                # H8: no data, no keys, no compute at all
make sample                     # seed 777, no keys needed beyond HF access
make judge JUDGES=qwen3-vl      # open weights, local or Modal
make agreement
make estimate                   # PPI over the published human gold
make prompt-sweep JUDGES=qwen3-vl
make card
```

This yields every structural result — H8, design effects, prompt sensitivity, judge–human
agreement for the open judge, and PPI-rectified prevalence for that judge — without a single
dollar of API spend. `make effective-n` in particular needs nothing but public participant
counts, so the cheapest finding in the project is also the most reproducible one. What it
cannot yield is the replication of Build AI's own figures, which requires their judge. That
asymmetry is the point, and it is reported rather than hidden.

The full path adds `JUDGES=gemini-2.5-flash,claude,qwen3-vl` and needs the keys in
`.env.example`.

## What must be fixed for numbers to match

| | |
|---|---|
| Seed | 777, everywhere, including the bootstrap |
| Sample membership | Written to disk at draw time and committed; reproduction reads the committed membership rather than redrawing |
| Corpus revision | `corpus_rev` recorded per frame; a different HF revision is a different experiment |
| Prompts | P0–P7 verbatim from `PRE-REGISTRATION.md`; P0 is Build AI's own wording |
| Rubric | `RUBRIC.md` revision recorded on every label |
| Judge revision | `judge_rev` recorded per response; closed-API drift is unfixable from outside and is reported, not silently absorbed |
| Bootstrap | Cluster over `worker_id`, B = 10,000, wherever a grouping variable exists; iid and labelled otherwise |
| Estimator | PPI++ for prevalence; Gwet's AC1 primary for agreement, κ reported beside it |

## What cannot be reproduced, and why

- **The human labels.** 600 primary labels from one rater are published as data, but a
  reproducer cannot regenerate them; they can only re-label and compare. That comparison is
  more valuable than a match, because it supplies the inter-rater agreement this project
  cannot produce. **A reproducer who re-labels `G200-ego` should be treated as a collaborator,
  and their κ against `R1` belongs in the record.**
- **Closed-judge responses at a past revision.** Recorded verbatim in `raw` so the parse is
  checkable, but not re-callable once the endpoint moves.
- **The corpus itself.** 16.4 TB for the smallest release, obtained from the vendor under
  their terms. vernier redistributes frame identifiers and labels only.

## Verification of the artifacts, not just the code

Every published figure cites the record that produced it. A reproduction is successful when
the cited records regenerate and the figures in prose match them — which is checkable
mechanically, and is what `make validate` is for.

An earlier revision of a sibling repository hardcoded its numbers into prose and went stale
the moment twelve claims were corrected. That is the failure this convention exists to
prevent.
