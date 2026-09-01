# Red team

**Opened before any result exists.** That is deliberate: attacks written after the fact are
selected for being survivable. Everything below is an attack on vernier's own findings,
recorded now, to be answered with evidence later — and published unedited when the answer is
bad.

Sibling precedent sets the expectation. `assay` turned its instruments on itself and twelve
of its published claims broke, with three real behavioural bugs falling out. Expect breakage
here too.

## A1 — The oracle is one person

**Attack.** Every agreement number in this project is measured against a single rater. There
is no inter-rater agreement, so there is no evidence that a second competent person applying
`RUBRIC.md` would produce the same labels. κ(judge, human) may be measuring the rater's
idiosyncrasies as much as the judge's errors.

**Partial answer.** `R100`, re-labelled blind after ≥7 days, gives intra-rater agreement (AC1,
with κ beside it). **This is
strictly weaker**: consistency is not correctness, and a rater who is reliably wrong scores
well on it. A stopping rule (intra-rater κ < 0.70 defers the audit) bounds the damage but
does not remove it.

**Status: unmitigated.** It is a real limitation and stays on the front page of any writeup.

## A2 — The rater is anchored on the thing being audited

**Attack.** `RUBRIC.md` was written after reading Build AI's prompt. The rubric's nine
resolutions could have been chosen, unconsciously, to make the judge look better or worse.

**Partial answer.** The rubric was frozen before any frame was labelled and before any judge
output was seen, and it follows the published intent rather than improving on it. That
constrains post-hoc adjustment, not initial framing.

**Status: unmitigated at n = 1.** Declared, not fixed.

## A3 — Three judges are not three opinions

**Attack.** Panel agreement is reported as though the judges were independent. They share
pretraining data, architectural lineage, and probably training images. Correlated errors
inflate Fleiss' κ and make the panel look more reliable than it is.

**Answer.** Panel agreement is reported explicitly as an **upper bound** on judge
reliability, never as a measure of it, and judge–human agreement is always reported
alongside. `COVERAGE.md` lists judge independence as assumed false.

## A4 — Multiplicity in the prompt sweep

**Attack.** Eight variants × three figures is 21 comparisons. Something will look
significant.

**Answer.** Holm–Bonferroni over the 21-test family, declared in `PRE-REGISTRATION.md` before
any variant ran, and H3 is stated as an effect size (≥ 5 pp) rather than as a p-value. Any
finding outside the pre-registered family is labelled exploratory in those words.

## A5 — The design-effect result could be an artifact of the sampling

**Attack.** `S10k-S` caps at one frame per clip; `S10k-U` does not. The two arms therefore
differ in clustering *by construction*, so a design-effect gap between them proves nothing
about Build AI's sample.

**Answer.** The design effect is computed **within** each arm separately against its own iid
counterfactual, never by differencing the arms. The `S10k-U` figure is the one that speaks to
the published number, because uniform-over-frames is the literal reading of what they
published. Stated here so the comparison is not made carelessly later.

## A6 — Replication failure could be ours

**Attack.** If H1 fails, the likeliest cause is that vernier drew a different sample or
parsed responses differently — not that Build AI is wrong.

**Answer.** Both sampling designs are run, `judge_rev` is recorded per response, parse
failures are counted by reason rather than dropped, and P0 is used verbatim. If H1 still
fails, the report says "we could not reproduce it, under these two designs, at this
revision", and does not upgrade that to "the published figure is wrong". The failure is
reported without being investigated until it disappears — a rule that exists precisely
because the temptation runs the other way.

## A7 — The judge version moves under us

**Attack.** `gemini-2.5-flash` is an API name, not a fixed artifact. The model answering in
2026 is not necessarily the one that produced the November 2025 figures, so a replication
failure may be a version difference and nothing more.

**Answer.** `judge_rev` is recorded per response and any mid-experiment change is a
`DECISIONS.md` entry. But the underlying problem cannot be fixed from outside, and it is
**itself a finding**: a quality SLA whose measurement instrument is a versionless third-party
API cannot be reproduced by its own vendor either. That belongs in the writeup regardless of
how H1 lands.

## A8 — Distillation could look good for the wrong reason

**Attack.** H6's ≥ 0.90 agreement threshold is easy to clear when the base rate is 96%. A
model that always answers "two hands visible" would score well.

**Answer.** Agreement is reported against the trivial constant-answer baseline in every case,
per class rather than pooled, and with a chance-corrected statistic rather than raw agreement
as the headline. Note the tension: κ is near zero for a constant predictor, which is what makes
it useful here — but at 96% prevalence κ is unstable to the point of sign flips, which is why
AC1 is primary (D022). **Both are reported**, because neither alone is trustworthy at this
prevalence, and any writeup quoting one without the other fails this entry. If this is not done in the eventual results, this entry
is the evidence that it was known and skipped.

## A9 — The domain-bias experiment has small arms

**Attack.** 200 human-labelled frames per comparison domain is thin for detecting a 5 pp
interaction, particularly with cluster-robust standard errors.

**Answer, partial.** The arms were rebalanced to 200 per domain (D023) — H5's estimand is an
interaction and 150/150 against 300 would not have identified it at all. Power is still
limited and is acknowledged in advance rather than discovered afterwards. If H5's interval is wide and includes zero, the reported conclusion is
"underpowered, not null" — the two are different and conflating them would be exactly the
error vernier is auditing.

**Status: a real weakness of the design**, accepted because the alternative is not labelling
the comparison domains at all.

## A10 — The whole project could be redundant

**Attack.** Someone may already have validated a VLM judge on egocentric data.

**Answer.** `SURVEY.md` is a hard gate before any experiment. If the answer is yes, the
project stops. The value of noticing exceeds the value of a duplicated result.

## A11 — Reproducibility, checked against vernier's own standard

**Attack.** vernier criticises a measurement that cannot be independently re-run. Two of the
three judges are closed APIs behind paid keys.

**Answer.** Qwen3-VL is in the panel specifically so the full audit is re-runnable with no
API keys, and `REPRODUCTION.md` documents the open-judge-only path as a first-class route
rather than a degraded one. If that path is ever broken or untested, this criticism lands in
full.

## A13 — H2 is now measured somewhere other than where it is claimed

**Attack.** The design effect is measured on vernier's own corpus draws, then asserted to apply
to Build AI's published figures. Their sample is not vernier's sample. If their 10,000 frames
happened to be drawn one-per-worker, the design effect on their number would be near 1 and the
argument collapses.

**Answer, partial.** True, and the reason it cannot be settled is itself the finding: their
release ships no grouping variable, so nobody can check (`UPSTREAM-FINDINGS.md` F9). The
licensed claim is therefore narrow — *the corpus has this design effect, and any interval on a
frame-level statistic drawn from it inherits some of it* — and the writeup must not upgrade
that to a statement about their specific draw. If this distinction is blurred anywhere in the
eventual results, this entry is the evidence it was known in advance.

## A14 — Reporting a vendor's commit history

**Attack.** F10 and F11 read a public commit log and report that an identifier column was
deliberately removed and that prompt files lost a version suffix. That is close to inferring
intent from a repository's private-feeling history, and it invites an uncharitable reading the
evidence does not support.

**Answer.** The history is public, the facts are exact commit titles, and both findings are
written with the inference deliberately withheld: vernier records that reproducibility
regressed and that it is trivially fixable, and states in both entries that it makes no claim
about why. Any draft that speculates on motive fails this entry and should be cut. The test
before publishing: would this paragraph read as fair to the person who wrote that commit?

## A12 — The private directory

**Attack.** This repository contains a gitignored directory of outreach strategy concerning
the party whose work it audits. If it leaked, or if it shaped a finding, the research would
be worthless.

**Answer.** `make privacy-gate` fails if anything under `docs/private/` is stageable;
`AGENTS.md` forbids quoting it in any public document; `ETHICS.md` and every finding are
written without reference to it. This entry exists so that the conflict is disclosed by the
project itself rather than discovered in it.
