# Evals card — `vernier-evals`

The prediction records behind every published figure: judge responses, distillate
predictions, and the agreement and calibration computations over them. Published so that any
number in the writeup can be recomputed from the record that produced it rather than trusted.

Shape fixed now; contents *produced by* the experiments named. Nothing has run.

## Contents

| Split | What | Produced by |
|---|---|---|
| `replication` | `gemini-2.5-flash` P0 over `S10k-U` and `S10k-S` — the arm that speaks to the published figures | E2 |
| `panel` | All three judges over `P2k` and both comparison-domain draws | E4 |
| `sweep` | P0–P7, all judges, `P2k` | E5 |
| `gold` | Human labels, both passes, with tags, difficulty and timing | E3 |
| `instrument` | Distillate predictions, both rungs, on `S10k-S` and held-out `G200-ego` | E7 |
| `probe` | Transfer-probe results, if the kill-gate opens | E9 |

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
