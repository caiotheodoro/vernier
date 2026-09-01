# Evals card — `vernier-evals`

The prediction records behind every published figure: judge responses, distillate
predictions, and the agreement and calibration computations over them. Published so that any
number in the writeup can be recomputed from the record that produced it rather than trusted.

Shape fixed here; the full card is *produced by* the experiments named, not yet published as
one artifact. Real smoke-scale runs exist (`docs/HANDOFF.md`: E2 at n=100, E5 at n=5) but the
below describes the shape at the pre-registered scale, per `docs/DECISIONS.md` D042/D047/D048's
reframe -- not the original three-judge design this table was first written against.

## Contents

| Split | What | Produced by |
|---|---|---|
| `replication` | The live Qwen3-VL judge, both P0 arms, over `E10k-ego` — compared against Build AI's own stored `gemini-2.5-flash` labels on the identical frames (D042 redefined this from a live replication to a comparison) | E2 |
| `panel` | The live Qwen3-VL judge over `P2k` and both comparison-domain draws, alongside the stored `gemini-2.5-flash` labels as the second, frozen arm (`docs/REVIEW.md` point 2) | E4 |
| `sweep` | P0–P7, the live judge only, `P2k` | E5 |
| `gold` | Human labels, both passes, with tags, difficulty and timing | E3 |
| `instrument` | Distillate predictions, both rungs, trained on Build AI's own stored labels across all three corpora minus their `G200-*` holdouts (D047), evaluated on held-out `G200-ego` | E7 |
| `probe` | Dropped, not produced — Result 2's kill-gate is never reached (D048) | E9 |

## Statistics computed over them

Fixed in `PRE-REGISTRATION.md` before any data existed: raw agreement, Cohen's κ, Fleiss' κ,
intra-rater κ, ECE with 10 equal-width bins, cluster-bootstrap intervals over `worker_id`
(B = 10,000), design effects, and Holm–Bonferroni across the 21-test sweep family.

## The rule this card exists to enforce

**Excluded records are counted, with a reason, and removed from the denominator explicitly.**
Refusals, timeouts and unparseable responses are kept verbatim in `raw`. Silently dropping
them inflates agreement, which is precisely the class of error this project was built to
catch.

## License

Apache-2.0.
