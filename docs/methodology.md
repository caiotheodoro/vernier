# Methodology

The shared thesis behind `assay`, `reconforge`, `lossbench`, `specula`, `suture`, `plumb`,
`habeas` — and where vernier departs from it.

## The line

**A measurement is not a result until you know its uncertainty and what a wrong answer
costs.**

The sibling repositories apply this to model outputs: a verifier-as-oracle decides ground
truth by program, a small model is trained against it, and the score reported is
severity-weighted rather than raw, because a missed critical exception and a false alarm are
not worth the same. `assay` applies it one level up — to the environments and eval suites
that produce scores — on the argument that an auditor is itself an eval, and that a finding
is not a result until it is priced.

vernier applies it one level up again: to a **data product's published quality claim.**

## The transfer, and where the analogy breaks

In `specula`, `suture`, `plumb` and `habeas` the oracle is a program. A synthetic generator
plants a known defect; a deterministic verifier recovers it; ground truth is not a matter of
opinion, and the entire eval is reproducible by anyone with the seed.

That is not available here. Nobody can write a program that decides whether a hand is
"visibly present" in a factory frame. **The oracle has to be human**, and that swap costs
three things the sibling projects got for free:

1. **Ground truth becomes an interpretation.** `RUBRIC.md` resolves nine ambiguities by
   judgement, and a different reasonable reading yields different numbers.
2. **The oracle has a rate.** A program agrees with itself perfectly. A human does not, which
   is why `R100` exists and why intra-rater κ is reported before anything else.
3. **The oracle does not scale.** 600 labels, not 600,000. Every interval in this project is
   wide because of that, and the widths are published rather than smoothed.

Naming that cost is not a disclaimer. It is the reason the pre-registration is stricter here
than in the sibling repositories: when the oracle is a person, the protocol is the only thing
standing between a measurement and a preference.

## Why distillation is part of the method, not an extra

An audit that ends in a PDF measures one sample, once. The corpus it audits grows by an order
of magnitude every few months — 10K to 100K to 1M in five months — so a one-off number is
stale on arrival, which is the same criticism vernier makes of the published figure.

Distilling the judge into a small open model converts the audit into an **instrument**: a
buyer can run it on the batch they are actually buying, a researcher can run it on a corpus
vernier never touched, and a third party can re-run the whole audit with no API keys at all.
The distilled model deliberately reproduces the judge *including its errors*, because an
instrument that quietly improved on the thing it measures would no longer measure it.

## What gets published

Everything, including what breaks. Sibling precedent: `assay` turned its own instruments on
itself and **twelve published claims broke**; the breakage is published unedited and the
GRPO-trained Challenger that lost to a scripted floor is published as a negative result.
vernier inherits that obligation in `RED-TEAM.md`, which opens before any result exists.

An empty finding list must never read as a clean bill of health. Every card carries "what
could not be checked", with a named reason per item — the half that makes the other half
worth anything.
