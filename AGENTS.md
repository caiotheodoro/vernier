# vernier — orientation for agents and reviewers

**Putting error bars on a dataset vendor's quality claim, and distilling the judge into an
instrument anyone can re-run.** `README.md` is the argument. This file is the operating
rules.

**Current state: mid-experiment.** Real data drawn and persisted, the live judge deployed and
called for real at smoke scale, matching Build AI's own published labels on every frame
checked. No human label exists yet — Wave 3 is the critical path. No model trained.
`docs/HANDOFF.md` is the resume point.

## The claim

A measurement is not a result until you know its uncertainty and what a wrong answer costs.
vernier does not claim Build AI's numbers are wrong; it claims nobody knows how wrong they
could be — and builds the thing that would tell you.

## Five rules, in force from the first commit

**1. Pre-registration is binding.** `docs/PRE-REGISTRATION.md` is frozen before any frame is
fetched. Sample sizes, statistics, prompt variants, hypotheses and stopping rules do not
change because a result was disappointing. If one must change, it changes in the open: a
`docs/DECISIONS.md` entry saying what changed, when, why, and what the number was before.
A deviation recorded is a limitation; a deviation unrecorded is misconduct.

**2. No transcribed numbers.** Every figure in prose cites the file that produces it. An
earlier revision of a sibling repository hardcoded its numbers and went stale the moment
twelve claims were corrected. Prose that carries a number the pipeline no longer produces is
a bug, and `make validate` should catch it. The same applies to a *design* the project no
longer has, not just a number — `docs/DECISIONS.md` D048 found thirteen files still describing
the pre-D042 panel of three live judges after it was retired; `scripts/check_stale_prose.py`
(`docs/DECISIONS.md` D050, `docs/REVIEW.md` R10) is `make validate`'s check for this.

**3. The judge is never the oracle.** Human labels against `docs/RUBRIC.md` are the only
ground truth in this repository. A judge's output is data being measured, never a target to
match. The labelling tool must never display judge output to the rater, before or during a
pass.

**4. Self-audit before publishing.** Every instrument vernier applies to Build AI's
measurement gets applied to vernier's own. `docs/RED-TEAM.md` opens before results exist and
is expected to break claims. Anything that breaks gets published broken.

**5. `docs/private/` never leaves the machine.** It holds outreach strategy and the country
brief. It is gitignored, it is never quoted in a public document, and its content never
influences a finding. Run `make privacy-gate` before any commit. If the repository is ever
published, verify the ignore rule survived the publish path — a private directory that leaks
into an artifact aimed at the party it discusses is the worst available outcome for this
project.

## What is deliberately published as a weakness

Written down now, before it can be softened by results:

- **One human rater.** There is no inter-rater agreement statistic, because there is one
  person. The substitute is a blind re-label of `R100` at least seven days later, giving
  *intra*-rater agreement — a weaker instrument, and `docs/RED-TEAM.md` says how.
- **The rater has read Build AI's prompt.** `docs/RUBRIC.md` was written knowing the
  definitions being audited. That is anchoring, and it is not removable at n=1.
- **Three judges are not three independent opinions.** They share pretraining data and
  architecture lineage. Panel agreement is therefore an upper bound on judge reliability,
  not a measure of it.
- **MPJPE is not checkable.** Half of Build AI's advertised SLA needs pose annotations the
  public release does not ship. `docs/COVERAGE.md` states the uncovered half.
- **There is no public `builddotai/Egocentric-1M`.** The Hub returns 404 and the org hosts
  four datasets. Everything runs on the 10K/100K releases, and every claim names which
  release it was measured on. `docs/UPSTREAM-FINDINGS.md` F6.

## Order of work

`docs/SURVEY.md` gates everything. If independent validation of a VLM judge on egocentric
data is already published, stop and re-scope rather than proceed — a redundant result is
worth less than the honesty of noticing.

Then: freeze `docs/PRE-REGISTRATION.md` → `make sample` → `make replicate` → `make
human-labels` → `make agreement` → `make prompt-sweep` → `make domain-bias` → `make distil`
→ `make calibrate` → kill-gate → `make probe` → `make card`.

## Map

| | |
|---|---|
| What is committed before any result is seen | `docs/PRE-REGISTRATION.md` |
| The annotation rules their prompt still leaves undefined | `docs/RUBRIC.md` |
| What their published artifacts actually say | `docs/UPSTREAM-FINDINGS.md` |
| The protocol, experiment by experiment, with its cost | `docs/METHOD.md` |
| The literature, and the novelty gate | `docs/SURVEY.md` |
| What vernier does not measure | `docs/COVERAGE.md` |
| Attacks on vernier's own findings | `docs/RED-TEAM.md` |
| Provenance and what it limits | `docs/ETHICS.md` |
| Module boundaries and their seams | `docs/ARCHITECTURE.md` |
| Every record schema | `CONTRACTS.md` |
| Reproducing all of it, including with an open judge only | `docs/REPRODUCTION.md` |
| What is inherited, and from where | `docs/LINEAGE.md` |
| Decisions and what would reverse them | `docs/DECISIONS.md` |
| Where the work stands | `docs/HANDOFF.md` |

Apache-2.0.
