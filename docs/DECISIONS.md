# Decisions

Every decision, its reason, and what would reverse it. Append-only; entries are amended with
a dated note rather than rewritten.

Seeded 2026-08-31 from the scoping session that created this repository.

---

## D001 — Audit the quality judge, not the pose SLA

Build AI advertises guarantees on "3D pose MPJPE, diversity, and quality". Only the quality
axis is checkable from the public release, which ships metadata and per-worker fisheye
intrinsics but no pose annotations.

**Reverses if:** Egocentric-1M access opens and ships pose annotations, making some part of
the MPJPE claim externally checkable. Then `COVERAGE.md` changes and the scope decision is
revisited — it does not silently expand.

## D002 — Human gold as oracle, not a program

Every sibling repository uses verifier-as-oracle: a program decides ground truth. No program
can decide whether a hand is "visibly present" in a factory frame, so the oracle is a person.
`methodology.md` records the three things that swap costs.

**Reverses if:** nothing. This is forced by the domain.

## D003 — Cluster bootstrap over `worker_id`, never iid

192,900 clips from 2,153 workers. Frames from one worker share scene, lighting, task, gloves
and calibration, so an iid interval understates its width by the design effect. Every
published interval clusters by worker; iid intervals appear only beside them, labelled, to
exhibit the effect.

**Reverses if:** nothing. An iid interval on this data would be wrong.

## D004 — Draw both `S10k-U` and `S10k-S`

"10,000 randomly sampled frames" does not determine a sampling design, and Build AI does not
say which was used. Rather than guess, draw both and publish the gap as a result.

**Reverses if:** Build AI documents the design. Then the matching arm becomes the replication
and the other becomes the sensitivity analysis — the experiment is unchanged, only its
labelling.

## D005 — One rater, with a blind re-label instead of a second rater

600 primary labels are affordable for one person; a second rater is not, at this budget.
`R100` re-labelled blind after ≥7 days gives intra-rater agreement, which measures
consistency, not correctness.

**Reverses if:** a second rater becomes available. That is a strict improvement and would be
taken; the intra-rater pass stays regardless, since it is cheap and independently
informative.

## D006 — The panel includes an open-weights judge

vernier's criticism is that a closed, single-shot measurement cannot be independently
re-run. A panel of only closed APIs would reproduce that flaw exactly. Qwen3-VL makes the
audit re-runnable end to end with no API keys.

**Reverses if:** nothing. This is load-bearing for the argument.

## D007 — Distil the judge, including its errors

The distilled model targets `gemini-2.5-flash` P0 labels, not human gold. An instrument that
quietly improved on the judge would no longer measure the judge.

**Reverses if:** nothing — though a *second*, separately named model trained on human gold
would be a legitimate follow-up and would not be called the instrument.

## D008 — Result 2 is kill-gated

A matched three-corpus transfer probe may not fit the free-credit budget. A half-finished
second result damages the first, so the gate is at entry and the drop is recorded.

**Reverses if:** compute materially increases.

## D009 — Publish first, then contact Build AI

Deliberate. Publishing first keeps the work independent research rather than something
negotiated in advance, and the artifact is designed so both outcomes are useful to them: a
confirmation with intervals they did not have, or a problem found before a customer found it.

**Reverses if:** a finding turns out to be a live security or privacy exposure rather than a
measurement question. That would warrant private disclosure first, and the reasoning would be
recorded here before acting.

## D010 — The ethics discussion is scholarly and public; the country brief is private

`ETHICS.md` records what is and is not knowable about provenance from the public release, and
the limits that places on conclusions. It is standard for dataset work and it strengthens the
paper. The Brazil/LGPD material and all outreach framing live in `docs/private/`, gitignored,
and never influence a finding.

**Reverses if:** nothing. Mixing the two would make the research read as leverage.

## D011 — Repository named `vernier`

The auxiliary scale that adds resolution to an existing instrument. The project does not
replace Build AI's measurement; it adds precision to it. Consistent with the sibling naming
line — `assay`, `specula`, `plumb`, `suture`, `keel`, `habeas`.

## D012 — Ornith-1.5 is not in the judge panel

Considered and rejected on a fact: Ornith-1.5 (397B MoE / 35B MoE / 9B dense) is text-only —
reasoning, coding and agentic tasks. It cannot judge frames.

**Reverses if:** a multimodal Ornith ships. Separately, Ornith-9B remains a candidate for a
*Challenger* probe — an agent attempting to score well on the quality metric without doing
the work — which is a different role and is a stretch item, not a panel seat.

## D013 — Documentation before code

The entire finding is that a measurement was published without a stated protocol. Improvising
this project's own protocol would be self-refuting. `PRE-REGISTRATION.md` freezes before
`src/` exists.

**Reverses if:** nothing.

---

## D014 — "One-line prompt" was wrong; corrected everywhere

Drafts through 2026-08-31 described Build AI's judge as running "a one-line prompt", taken
from press coverage. Reading `builddotai/Egocentric-10K-Evaluation` directly showed structured
prompts: role line, explicit task, explicit definition, five bulleted rules, constrained JSON
response schema. Corrected in `README.md`, `AGENTS.md`, `llms.txt`, `RUBRIC.md` and
`PRE-REGISTRATION.md`.

The audit's premise is unchanged — no human gold, no agreement statistic, no interval, no
prompt-sensitivity analysis, no cross-domain accuracy test — but the characterisation was
unfair and is fixed. `UPSTREAM-FINDINGS.md` F1.

**Reverses if:** nothing. It was a factual error.

## D015 — P0 is two prompts, `P0a` and `P0b`, both run

The dataset card and `prompts/active_manipulation.txt` differ in four places, and which
produced 91.66% is not recoverable from the published artifacts. Rather than pick one, both
are primary arms and the gap is hypothesis H1b.

**Reverses if:** Build AI states which was used. Then the other becomes a sensitivity arm.

## D016 — Audit their published frames, not a re-draw

The evaluation release ships the judged frames themselves for all three corpora (~5.5 GB,
Apache-2.0, ungated). Measuring on those frames removes sampling difference from the
replication entirely — a materially stronger design than `1.0.0`'s re-draw. The corpus draws
`S10k-U` and `S10k-S` are retained solely as the sampling-design sensitivity arm.

**Consequences:** Ego4D and EPIC-KITCHENS-100 access is no longer required (D017); `P2k`
becomes `P2k`, drawn from their Egocentric arm; all three `G200-*` sets are drawn from
their frames.

**Reverses if:** the parquets turn out not to contain the frames actually judged — checkable
against the published per-frame labels, and the first thing `make sample` must verify.

## D017 — Ego4D and EPIC-KITCHENS-100 access is not on the critical path

Retires the `1.0.0` deviation clause. Their frames arrive inside the evaluation release under
Apache-2.0. Independent access would still be needed for Result 2's transfer probe at scale,
and that remains kill-gated.

Survey Track 2 separately established that both are obtainable — Ego4D via click-through with
~48 h approval and 14-day credential expiry; EPIC-KITCHENS-100 under CC BY-NC 4.0 requiring an
institutional email and ~2 working days. The institutional-email requirement is a real
obstacle for an unaffiliated researcher and is now a Result-2 risk rather than a Result-1
blocker.

## D018 — Calibration is reported for P7 only

Both published prompts constrain output to a bare integer or a `yes`/`no` enum. No confidence,
no logprob. Calibration cannot be measured on the published protocol without changing it, so
it is measured on variant P7 and labelled as a property of that variant. Calibration-under-P0
goes in "what could not be checked". Hypothesis H7. `UPSTREAM-FINDINGS.md` F8.

**Reverses if:** an open-weights judge exposes logprobs under the unmodified schema, which
would give calibration for that judge on the published protocol. Then it is reported for that
judge only, and still not for the closed ones.

## D019 — Cite HD-EPIC and EgoCross rather than claim an empty field

Survey Track 2 found HD-EPIC (arXiv 2502.04144) runs a real inter-annotator-agreement
pipeline — ≥3 annotators, temporal-IoU agreement, a hard 0.3 threshold, best-2 merge — for
fine-grained action timing. It is the field's one rigorous IAA precedent and must be cited and
distinguished, not ignored: it validates *annotation*, not a model-produced corpus-level
quality statistic.

**Amended by D030** — the best-2 merge has a condition Wave S found in the appendix, not
previously recorded here.

EgoCross (arXiv 2508.10729) shows MLLM performance is domain-sensitive across egocentric
domains. It is adjacent supporting evidence for H5, not a test of it, and must be positioned
that way.

**Reverses if:** closer prior art turns up. `SURVEY.md` Track 3 is the gate that decides.

---

## D020 — The contribution is H5 and judge-as-instrument, not judge validation

`SURVEY.md` Track 3 returned PROCEED with a narrowing that changes how this work is presented.
Validating a VLM judge against human labels is routine and heavily prior-arted; leading with it
invites an easy rejection and undersells the work.

What is genuinely open: **no prior work both compares corpora on a common metric with a shared
labeller and tests whether that labeller is equally accurate across the compared domains.** E3
and E4 are infrastructure supporting H5; they are not the claim.

**Reverses if:** closer prior art appears. The original clause named LIME (2607.02417) as that
risk; it was opened and **refuted** — see D029. No live reversal condition currently stands.

## D021 — PPI is the primary estimator; the cluster bootstrap supports it

A cluster bootstrap corrects variance and leaves bias untouched. Reporting a wide interval
around an uncorrected judge-derived proportion would be a rigorously-intervalled wrong number —
a more sophisticated version of the error being audited.

Prediction-powered inference (2408.15204) uses the small human-gold sample to debias the large
judge-labelled sample and returns a valid interval for the *true* prevalence. Clustered
resampling runs **with** it, not instead of it.

**Amended by D030** — the 2408.15204 citation was wrong; see D030 for the correction.

**Reverses if:** the gold sample proves too small for PPI to beat the naive estimator, in which
case the naive estimate is reported with the bias direction named and unquantified.

## D022 — Gwet's AC1 is the primary agreement statistic

At 96% prevalence the kappa paradox makes Cohen's κ near-uninformative and unstable. Rao &
Callison-Burch (2606.00093) document protocol choices alone moving accuracy 0.551→0.899 **and
flipping κ's sign with no verdict changes**. AC1 is primary; κ is reported beside it so
readers who expect κ can find it.

Decided before any label exists, which is the only time this decision can be made honestly.

## D023 — Human gold is balanced 200/200/200

H5's estimand is an interaction, P(judge error | domain), not a main effect. An unbalanced
split does not identify it. `1.1.0`'s 300/150/150 would have failed. Total labelling is
unchanged at 600 primary.

## D024 — H8 is reported first, before any labelling

Effective N differs across the three compared corpora by close to an order of magnitude —
EPIC-KITCHENS-100 has roughly 45 participants against Ego4D's ~931. "10,000 frames each" is
presented as three estimates of equal precision and is not.

This is computable from public participant counts with no experiment at all, which makes it
the cheapest real finding in the project and the first thing to publish.

**Reverses if:** the participant counts are wrong. They are secondary-sourced in the survey and
must be confirmed against each corpus's own documentation before publication.

**Amended by D030** — participant counts confirmed against primary sources and corrected.

## D025 — The panel needs an error-dependence estimate

Three judges sharing pretraining lineage do not supply three independent opinions
(2607.08535). Panel agreement was already flagged as an upper bound in `RED-TEAM.md` A3;
`1.2.0` adds an explicit estimate of judge-error dependence rather than leaving the caveat
qualitative.

---

## D026 — The instrument abstains and carries a floor (Trust-or-Escalate)

Supersedes the plain-distillation half of D007. Reading 2407.18370 in full showed the mechanism
is stronger than "cite it as an ancestor": confidence estimation plus a cascade gives a *provable*
human-agreement floor at a user-specified level. Their precedent — on Chatbot Arena, where GPT-4
alone rarely reached 80% human agreement, a cascade guaranteed >80% at ~80% coverage with much
cheaper models.

A buyer measuring the batch they are purchasing needs a floor they can rely on, not an average
they must trust. H6 is rewritten as coverage-at-a-floor, and `distil` gains a third rung.

**D007 survives in the part that matters:** training targets remain the judge's labels, not human
gold, so the instrument still measures the judge rather than quietly improving on it. Teacher
fidelity is still reported — as the diagnostic, not the claim.

**Reverses if:** the cascade cannot reach a useful floor at usable coverage, in which case the
faithful distillate ships alone and the failure is reported as a negative result.

## D027 — H3's direction is prior-supported, and the writeup says so

IPR/PAR (2604.16413) find LLM annotation "exhibits substantial stochastic variation in
interpretative tasks, while appearing more stable in knowledge-based tasks". Hand-count is
perceptual; active manipulation is interpretative. H3 predicted exactly that split, and was
written before the paper was read.

That makes H3 a confirmation rather than a discovery. Claiming it as novel once this citation is
known would be the kind of thing this project exists to catch. Prompt sensitivity is reported as
IPR/PAR rather than as a home-made spread statistic.

## D028 — Compute J and ΔJ

2605.06939 supplies two diagnostics vernier was not computing: judge quality **J**, and
cross-model calibration instability **ΔJ**. Together they say when a shared-calibration
comparison is unreliable — which is precisely the situation Build AI is in, applying one judge's
calibration across three corpora and comparing the results.

Cheap to compute, directly on the critical path for H5, and it turns "the comparison may be
confounded" into a measured statement.

## D029 — LIME does not exist as prior art; D020's reversal clause is void

D020 named LIME (2607.02417) as the condition that would reverse the narrowed framing. Opened
directly: it is a vision-language camera-motion generator for robotics (Sun, Li, Yang, Zhang,
Engelbracht, Hong, Cadena, Pollefeys, Blum), with no judge validation and no 91.3% figure.

The claim was tagged `[S]` and checked before being relied on. **The reversal clause in D020 is
void**, and the narrowed contribution stands on stronger ground than when it was written.

One mis-attribution means the base rate is not zero, so every remaining citation is audited
before publication rather than after. That audit is Wave S of the implementation plan.

## D030 — Wave S corrections: three mis-citations and a stale figure

Wave S (2026-08-31, dispatched as 8 independent citation-audit workers) is the audit D029
promised. It caught three further mis-citations and one stale figure, each verified against
the primary source, each recorded here per this document's own amendment rule rather than
silently edited into the entries above.

1. **D021's PPI citation was wrong.** `2408.15204` was cited as "Prediction-powered inference."
   It is not — it is *"Can Unconfident LLM Annotations Be Used for Confident Conclusions?"*
   (Gligorić, Zrnic, Lee, Candès, Jurafsky), which introduces **Confidence-Driven Inference**, a
   refinement built on top of PPI, not PPI itself. The actual PPI paper is **arXiv 2301.09633**
   (Angelopoulos, Bates, Fannjiang, Jordan, Zrnic). D021's valid-interval property still holds
   under either paper; the citation is corrected to 2301.09633, and 2408.15204 is now cited
   separately as CDI, an alternative estimator worth evaluating on its own terms. `LINEAGE.md`
   updated to match.

2. **D024's participant counts were wrong.** EPIC-KITCHENS-100 was recorded as "roughly 45
   participants," secondary-sourced. The primary source (arXiv 2006.13256, full text) states
   *"increasing the total number of subjects and kitchen environments to 37 and 45
   respectively"* — 45 is the kitchen/environment count, 37 is the participant count. Ego4D was
   recorded as "~931"; Ego4D's own site states *"collected from 923 unique participants."*
   Egocentric-10K's 2,153 was already primary-sourced and is unchanged. Corrected figures: **37
   / 923 / 2,153**, close to two orders of magnitude of spread rather than one. `BENCHMARK.md`
   and `SURVEY.md` updated to match.

3. **D019's HD-EPIC description was incomplete, not wrong.** The ≥3-annotator, temporal-IoU,
   best-2-merge pipeline is confirmed verbatim in the appendix, with one condition not
   previously recorded: best-two merging applies only when pairwise IoU exceeds 0.5; below
   that threshold only the single best annotator's label is kept.

4. **A citation in `SURVEY.md`'s working table, not load-bearing in any decision here, was
   refuted.** `2503.05965` was listed as supporting H3's "active manipulation is a
   rating-indeterminate rubric" framing. It does not discuss active manipulation, hand-counting,
   or any egocentric-video task — its actual rating-indeterminacy examples are toxic language,
   factuality, helpfulness, and relevance. D027, which is what actually grounds H3, already
   cites only IPR/PAR (2604.16413) and required no change. `SURVEY.md` corrected to remove the
   false attribution.

`PRE-REGISTRATION.md`'s frozen text is left as originally frozen, per its own rule; this entry
is the amendment record for the participant-count and PPI-citation corrections that affect it.

**Reverses:** nothing — all four are corrections to citation fidelity, not to the hypotheses,
protocol, or stopping rules. No experiment result is affected, since none has been run.

## D031 — Refinement-plan corrections: a real leak, a contract gap, and a mislabelled statistic

Three independent AI audit reviews of this repo (`docs/private/reviews.txt`) were cross-checked
against the actual files rather than trusted from their prose. Every claim checked came back
confirmed. Recorded here per this document's own amendment rule, before Wave 0 is committed.

1. **Distillation had a real train/eval leak, not just a doc typo.** `METHOD.md` E7 said train
   on `E10k-ego`, evaluate on `G200-ego`; `MODEL_CARD.md` said train on `S10k-S` — the two
   already disagreed. Worse: `G200-ego ⊆ P2k ⊆ E10k-ego` by construction
   (`PRE-REGISTRATION.md`'s own sample definitions), so METHOD.md's literal protocol had all
   200 held-out evaluation frames already inside the 10,000-frame training set. Fixed: both
   docs now specify training on `E10k-ego \ G200-ego`, keeping the instrument distilling from
   Build AI's own audited evaluation set with the overlap explicitly excluded, rather than
   switching to an unrelated corpus draw.

2. **`FrameRef` could not represent an evaluation-arm frame.** `worker_id` (and `factory_id`,
   `clip_id`, `timestamp_s`) were typed as required non-null fields, but Build AI's evaluation
   parquets ship none of them — bare UUID4 `frame_id` only (`UPSTREAM-FINDINGS.md` F9). Nothing
   stopped a fabricated placeholder from silently satisfying the type, which would have violated
   `CONTRACTS.md` rule 1 ("a number whose origin cannot be reconstructed is not publishable").
   Fixed: all four fields are now nullable, null together (never partially), with a required
   `why_no_provenance` reason — mirroring the existing `PPIBlock.why_not_clustered` pattern.
   `BENCHMARK.md` R4 and `METHOD.md` E6 previously stated their domain-bias model is
   "cluster-robust by participant" unconditionally, for analyses that run on exactly these
   provenance-null `G200-*` frames — also fixed, now hedged to match
   `PRE-REGISTRATION.md`'s already-correct "cluster-robust where a grouping variable exists."

3. **H8's "effective N" was a raw participant-count comparison, not an effective N.** D024/D030
   and `SURVEY.md`/`BENCHMARK.md` labelled the 37/923/2,153 participant-count comparison
   "effective N" — no ICC or design-effect-adjusted computation exists anywhere in the repo to
   justify that term (`grep` for `kish|ICC|intraclass` returns nothing). `BENCHMARK.md`'s own
   R0 table already has separate `Participants` and `Effective N` columns with the latter
   marked `—`, which was the tell. Renamed throughout to "participant-count precision
   disparity" — a true ICC-adjusted effective N is only computable once R100/primary labelling
   produces real cluster-size and outcome-variance data, and belongs to `estimation`'s existing
   post-data `design_effect` computation, not to H8's pre-labelling arithmetic.

4. **Five contract validators had gaps, all empirically confirmed live** (constructing the
   "should be rejected" case succeeded before this fix): `JudgeResponse` only nulled
   `hands_visible` on non-`ok`, not `manipulation`; `Confidence` had no `kind`/`value`
   coupling or range check; `AgreementCI` allowed `cluster-bootstrap` with `clusters=None`;
   `HumanLabel.pass_` serialized as `"pass_"` against `CONTRACTS.md`'s own `"pass"` example;
   frozen records allowed in-place mutation of nested `list`/`dict` fields. All five hardened,
   each with a new malformed fixture proving the rejection is real.

`PRE-REGISTRATION.md`'s frozen text is left as originally frozen; this entry is the amendment
record.

**Reverses:** nothing in the hypotheses or stopping rules. Items 1–2 are correctness fixes to
what the pipeline can even represent; item 3 is a labelling correction with no numeric change;
item 4 is validator hardening. No experiment result is affected, since none has been run.

## D032 — D031 was incomplete; a second independent audit caught what it missed

D031 was committed (`ea75148`) claiming five validator gaps hardened and a clean rename. It was
not fully true. A second, independent audit pass — a fresh review with no stake in D031's own
narrative, told to be skeptical of the fix the same way the original three reviews were
skeptical of the repo — found four real gaps in what D031 claimed to have closed:

1. **`AgreementCI`'s validator was half-fixed.** D031 required `clusters` when `method ==
   "cluster-bootstrap"`, but not `B`, and did not forbid either field when `method == "iid"`.
   Confirmed live: `AgreementCI(method="cluster-bootstrap", clusters=10, B=None)` and
   `AgreementCI(method="iid", clusters=10, B=10000)` both constructed successfully before this
   fix. Now requires both `clusters` and `B` for `cluster-bootstrap`, and forbids both for `iid`.

2. **A sibling gap in the same class of bug, named in the same review-3 paragraph as the
   `AgreementCI` gap, was never touched.** `PPIBlock(clustered=True, cluster_by=None)` still
   validated after D031 — the existing `why_not_clustered`-required-when-`False` validator had
   no symmetric check that `cluster_by` is required when `True`. Fixed: the validator now
   checks both directions.

3. **The H8 relabel (D031 item 3) was applied to docs but not to code.**
   `src/vernier/estimation/__init__.py` still defined `def effective_n(...)` with a docstring
   calling it "H8: effective N per corpus," directly contradicting the just-corrected
   `docs/BENCHMARK.md` ("Effective N is a distinct, not-yet-computed quantity"). Renamed to
   `participant_count_disparity`, docstrings updated to match. `docs/COVERAGE.md`'s summary
   table also still claimed E4 is unconditionally "cluster bootstrap over `worker_id`" — the
   same clustering self-contradiction D031 item 2 fixed in `BENCHMARK.md`/`METHOD.md` but
   missed in `COVERAGE.md`. Reworded to match.

4. **`HANDOFF.md` was stale and, after `ea75148` landed, actively false**: it said "left
   uncommitted pending review" after the commit had already happened, and cited pytest/fixture
   counts (30 passed, 13+7 fixtures) that predated D031's own new tests (now 43 passed,
   14+19 fixtures — several added by D031 and D032 themselves). Updated to the current, correct
   numbers, and to point at both D031 and this entry.

The pattern worth naming: **a self-audit's first pass is not the last word.** D031 was produced
in the same context that wrote the code being fixed. This entry exists because that context was
checked by a different one, per this project's own `AGENTS.md` doctrine on validator
independence — and the check found real gaps, not just polish.

`PRE-REGISTRATION.md`'s frozen text is unaffected; nothing here changes a hypothesis, stopping
rule, or published number, since none exists yet.

**Reverses:** nothing. All four items are completions of validator/naming work D031 claimed to
have finished but had not.

## D033 — Wave 1's file-ownership rule was unenforceable against the built layout; fixed

The unpublished Wave 1 plan (18 units, one agent per module directory, "no agent edits a shared
file") was checked against the actual Wave 0 file layout and found unenforceable: four module
groups had multiple planned units sharing one physical file.

- `judges` — the Gemini, Claude, and Qwen3-VL adapters (three separate units) all lived in one
  `adapters.py`. Split into `judges/gemini.py`, `judges/claude.py`, `judges/qwen3vl.py`.
- `sampling` — the draw unit and the reserves/membership unit shared `sampling/__init__.py`.
  Split into `sampling/draw.py` (draw + the `normalize_worker_id` corpus-adapter seam, since
  draw is what calls it) and `sampling/membership.py` (write/load/replace-undecodable).
- `agreement` — the AC1/κ/Fleiss unit and the error-dependence unit shared
  `agreement/__init__.py`. Split into `agreement/core.py` and `agreement/dependence.py`.
- `estimation` — the PPI unit, the cluster-bootstrap unit, and the H8 unit shared
  `estimation/__init__.py`. Split into `estimation/ppi.py`, `estimation/bootstrap.py`, and
  `estimation/disparity.py`.

Each package's `__init__.py` is now a thin re-export shim, mirroring the pattern
`judges/__init__.py` already used correctly for `base.py`/`prompts.py`. This is a pure move —
`pytest` (43 passed) and `mypy --strict` (clean, 32 source files) are unchanged before and
after.

`estimation/disparity.py`'s `participant_count_disparity` function keeps the D032 rename; no
file in this split reintroduces "effective N" as a function or module name.

Recorded per this document's own amendment rule, same tier as Wave 0 itself: the whole point of
an interface freeze is that the fan-out that depends on it doesn't collide, and this is that
freeze catching up to its own stated rule before Wave 1 is dispatched rather than after.

**Reverses:** nothing. Pure file reorganization; no hypothesis, contract, or public function
signature changed — only which file each lives in.

## D034 — Backbone pinned: DINOv3 ViT-S/16, not ViT-B/16

`SURVEY.md` named DINOv3 (2508.10104) but left the size an open choice, "ViT-S/16 or
ViT-B/16." `docs/HANDOFF.md`'s P1 tier listed "pinning the DINOv3 backbone choice" as still
open. Pinned: **`facebook/dinov3-vits16-pretrain-lvd1689m`** — the LVD-1689M general-purpose
checkpoint (not the SAT493M satellite-imagery variant, which is the wrong domain), ViT-S/16,
frozen. Verified live against the Hugging Face Hub listing, not assumed from the paper name.

**Why S over B:** rung 1 of `distil` is pre-registered as "laptop-runnable... the baseline
that must be beaten before anything more expensive is justified" (`METHOD.md` E7), and
`probe`'s Result 2 is separately kill-gated on compute budget (D008). The smaller backbone
reduces feature-extraction cost across every corpus draw it touches (`S10k-U`, `S10k-S`,
`G200-*`, the domain-bias arms) without a stated reason to prefer B/16's extra capacity for a
frozen-feature linear probe or transfer-probe task. `CONTRACTS.md`'s `ProbeResult.backbone`
placeholder and `tests/fixtures.py`'s stray `"dinov2-large"` value (a DINOv2/DINOv3 naming
inconsistency, not a deliberate choice) are both corrected to this pin.

**Reverses if:** rung 1's linear probe fails to beat the naive-judge-proportion baseline and a
capacity-limited failure mode is suspected — then re-run rung 1 against
`facebook/dinov3-vitb16-pretrain-lvd1689m` before concluding the rung itself doesn't work.

## D035 — H5 is underpowered at the pre-registered n; R100's 0.70 gate has real boundary noise

Run before Wave 3 commits any labelling time, per `docs/HANDOFF.md`'s P1 tier ("H5/R100 power
simulation"). `scripts/power_simulation.py`, seed 777, 20,000 Monte Carlo reps per cell. Both
findings are real and neither changes a frozen number — see "Reverses," below.

**H5.** A two-proportion test for the pre-registered ≥5pp domain-bias effect
(`PRE-REGISTRATION.md` line 197), at `n=200`/arm (the balanced-gold size fixed by D023), α=0.05:

| baseline judge-error rate | power |
|---|---|
| 0.05 | 0.48 |
| 0.10 | 0.33 |
| 0.15 | 0.27 |
| 0.20 | 0.23 |
| 0.25 | 0.20 |
| 0.30 | 0.19 |

Power stays well under the conventional 0.80 target across every plausible baseline — it is
*never* better than roughly a coin flip, and falls to ~1-in-5 at higher baseline error rates.
**This means a null H5 result at n=200 is genuinely ambiguous between "no domain-bias effect
at the pre-registered ≥5pp threshold" and "an effect that size exists but this sample can't
reliably surface it."** H5's actual pre-registered analysis is a point estimate with an
interval, not a significance test against a power target — so this does not invalidate the
plan — but the ambiguity above must be stated plainly if H5 comes back null, not glossed over
as if a clean negative result had been obtained.

**R100.** For a grid of "true" intra-rater AC1 values, the probability that a single n=100
retest clears the pre-registered 0.70 gate (assuming 90% label prevalence, stated as an
assumption per `docs/HANDOFF.md`'s own high-published-proportion figures, not measured):

| true AC1 | P(measured AC1 ≥ 0.70) |
|---|---|
| 0.60 | 0.10 |
| 0.65 | 0.25 |
| 0.70 | 0.50 |
| 0.75 | 0.79 |
| 0.80 | 0.95 |
| 0.85 | 1.00 |
| 0.90 | 1.00 |

**At exactly the pre-registered threshold, the gate is a coin flip by construction** — a rater
whose true reliability is exactly 0.70 has ~50% odds of measuring below it and deferring the
audit unnecessarily, or (symmetrically) a rater at 0.65 has a nontrivial ~25% chance of
appearing to clear 0.70 by sampling noise alone. This is inherent to `n=100` and not a flaw in
the stopping rule itself; it means a measured AC1 landing within roughly ±0.05 of 0.70 should
be read as "near the boundary, not decisively on either side of it" when the result is reported,
rather than treated as a clean pass/fail.

Both tables are reproducible: `python3 scripts/power_simulation.py --n-sims 20000`.

**Reverses:** nothing. `PRE-REGISTRATION.md`'s n=200/arm and R100's n=100 are frozen and are
not changed by this entry, per `AGENTS.md` rule 1 — a size change would need its own dated
amendment, and neither finding here is a discovered error in the original sizing, only a
quantification of the power/precision it actually carries. Recorded so the limitation is
visible before Wave 3 spends the labelling budget, and so H5/R100 results are reported with
this context rather than read as more decisive than the sample size supports.

## D036 — Rubric pilot (offline self-check) found an orphan tag; fixed in RUBRIC.md 1.2.0

Run in place of a human pilot-labelling pass, per `docs/HANDOFF.md`'s P1 tier and Caio's own
call on scope (offline check, no labelling time spent). `scripts/rubric_pilot_check.py` parses
`RUBRIC.md`'s closed tag list and cross-checks it against every rule's `` tag `x` ``/``
tagged `x` ``/`` Tagged `x` `` annotation, in both directions: a tag in the closed list that no
rule ever attaches ("orphan"), and a tag a rule attaches that isn't in the closed list
("undeclared").

**Found:** `dark` was an orphan. The closed tag list (`## Tag list, closed`) includes it, but
the only mention of darkness anywhere in the rubric was Rule 9's "ambiguous ownership,
unidentifiable blur, darkness" as one of three example causes routed to the single
`undecidable` tag — no rule ever told a rater when to use `dark` on its own, as opposed to
`undecidable`. A rater hitting a dim-but-still-judgeable frame had no instruction at all.

**Fixed, `RUBRIC.md` → 1.2.0:** a new Rule 9 ("Low light") tags `dark` when illumination is
poor but a judgement is still reachable, and reserves `undecidable` (renumbered Rule 10) for
when it genuinely is not — "`dark` and `undecidable` are never the same frame's tag for the
same reason." `find_undeclared_tags` found nothing in the other direction; every other
`Tagged`/`tag`/`tagged` annotation in the rubric already matched a closed-list tag.
`tests/fixtures.py`'s three `rubric_rev` values and every cross-reference to the rubric's
revision (`METHOD.md`, `WAVES.md`, `HANDOFF.md`) are updated to 1.2.0 alongside this entry, per
`AGENTS.md` rule 2 — a stale revision string is exactly the "no transcribed numbers" bug that
rule exists to catch.

`tests/test_rubric_pilot_check.py::test_real_rubric_is_internally_consistent` locks in the
fixed state against the real file, so a future rubric revision that reintroduces an orphan or
undeclared tag fails a test rather than shipping silently.

**Reverses:** nothing pre-registered. `PRE-REGISTRATION.md`'s frozen text and every hypothesis
are unaffected — this corrects a gap in the rubric's own internal completeness, the same class
of fix `RUBRIC.md`'s own text names as the reason it went from 1.0.0 to 1.1.0.

## D037 — `agreement.core`'s frozen stubs gained a required `task` parameter

Wave 1 unit 10 (`docs/WAVES.md`), during implementation, found the frozen stubs for
`raw_agreement`, `gwet_ac1`, `cohens_kappa`, `fleiss_kappa`, and `intra_rater_kappa`
unimplementable as written: each took `labels: list[HumanLabel]` and
`responses: list[JudgeResponse]` with no way to say which of the two comparable fields
(`hands_visible` for the hand-count task, `manipulation` for the manipulation task) to compare.
Both fields are always populated together on an `"ok"` response (`models.py`'s
`JudgeResponse` validator), so nothing in the data itself disambiguates which one a given call
means to measure — the same `labels`/`responses` pair could be a hand-count agreement query or
a manipulation agreement query, and the frozen signature had no way to say which.

**Fixed:** each function gained a required `task: str` parameter appended after its existing
arguments. All prior positional arguments keep their position, order, and type — this is
additive, not a reordering. `build_agreement_result` already carried `task: str` for the same
reason; the parameter now reaches every function it calls internally.

Caught and disclosed by the implementing worker in the module's own docstring before any
review; the independent `opencode` review (`docs/WAVES.md`'s loop) confirmed the reasoning
sound (`SIGNATURE_CHANGE_VERDICT: sound`) and required this entry exist before the unit could
be committed — the same amendment discipline `docs/DECISIONS.md` D033 already applied to
Wave 1's file-ownership plan, applied here to a signature gap in the same interface freeze.

**Reverses:** nothing in `CONTRACTS.md`, `PRE-REGISTRATION.md`, or any hypothesis — this is a
correction to an unimplementable Wave 0 stub signature, not a change to what any statistic
means or how it's computed. No other Wave 1 unit called these functions before this fix, so
the blast radius is contained to `agreement/core.py` itself and its own tests.

## D038 — `card`'s verdict-derivation conventions, named here so they're not implicit

Wave 1 unit 18 (`docs/WAVES.md`) had to invent how `build_card` derives `MeasurementCard.verdict`
(`verdict: str` is unconstrained in `models.py` — a plain string field, not a `Literal` — so
its meaning lives entirely in convention, not the schema) since the frozen signature carries no
`verdict` parameter. The independent `opencode` review confirmed the logic itself sound but
flagged, correctly, that two project-level conventions were buried in one unit's private helper
rather than recorded where a future caller would find them. Recorded here per that finding.

**The rule:** `verdict = "VERIFIED"` iff (a) every `PrevalenceEstimate` passed to `build_card`
has a matching `Claim` with `record_type == "PrevalenceEstimate"` and `record_ref` equal to
that estimate's natural key, and (b) no `UncheckedItem` in `what_could_not_be_checked` is a
hard blocker. Otherwise `"NOT_VERIFIED"`. An extra `Claim` with no matching estimate is ignored
(the contract is "every estimate has a claim," not "every claim has an estimate") — ties
naming a check that was actually run to a real estimate, without requiring the reverse.

**Two conventions, now named:**
1. **The `record_ref` natural key** for a `PrevalenceEstimate`:
   `f"{corpus}/{task}/{prompt_variant}/{judge}"`. Any `Claim` tying itself to a
   `PrevalenceEstimate` must use this exact format for `_derive_verdict` to recognize it — a
   differently-formatted but semantically-equivalent `record_ref` silently reads as unclaimed
   and fails the card toward `NOT_VERIFIED` (fail-safe, but uninformatively so).
2. **The `"BLOCKER:"` prefix** on an `UncheckedItem.reason` (case-insensitive, leading
   whitespace tolerated) marks it a hard blocker — sufficient on its own to force
   `NOT_VERIFIED` regardless of claim coverage. Every other `UncheckedItem` is informational:
   named per `CONTRACTS.md`'s "what could not be checked" rule, but does not itself fail the
   card. Any code constructing an `UncheckedItem` for a genuinely fatal gap must use this
   prefix, or `_derive_verdict` will not see it as one.

**Reverses:** nothing pre-registered — this names conventions the implementation already
carried; no verdict any card would have produced changes as a result of writing this down.

## D039 — PPI's `clustered=True` overstates what's actually clustered; recorded as a known gap

Wave 1 unit 12's `estimation/ppi.py` (`docs/WAVES.md`) only clusters HALF of the PPI variance
it reports. `cluster_by` (when set) sends the gold-residual term through
`estimation.bootstrap.cluster_bootstrap_ci`, but the unlabelled-pool term stays an unclustered
analytic plug-in (`Var(f)/N`) regardless — `HumanLabel`/`JudgeResponse` carry no shared
participant identifier today, and joining to `FrameRef.worker_id` for the unlabelled pool is
out of this module's reach. The module's own docstring flags this as "a known scope gap, not a
silent guess." The independent `opencode` review agreed the disclosure was honest but flagged,
correctly, that the returned `PPIBlock.clustered = True` does not say so: per `CONTRACTS.md`'s
"absence is explicit" rule, a reader of the record alone — without the module's source comment
— has no way to know only one of the interval's two variance terms is actually cluster-robust.

**Not fixed here.** `PPIBlock.clustered` is a plain `bool` in the already-frozen `CONTRACTS.md`/
`models.py` schema; there is no vocabulary for "partially clustered" (`CONTRACTS.md`'s own
`PrevalenceEstimate` example only shows `clustered: false` with a `why_not_clustered` reason,
the opposite gap). Giving this its own state — a three-way `"none" | "gold-only" | "full"`
field, or a `clustered_note` alongside the bool — is a schema change, and schema changes belong
to a scoped decision with the actual affected callers in view (Wave 2's live judge harness,
which is what would finally supply a real `worker_id` join for the unlabelled pool), not a
Wave-1 unit fixing its own frozen contract mid-implementation.

**Until then:** any code or writeup consuming `PrevalenceEstimate.ppi.clustered` for the PPI
estimator specifically must read this entry, not just the field, before treating `True` as
"the whole interval is cluster-robust." The naive/cluster-bootstrap `AgreementCI` path
(`estimation.bootstrap.cluster_bootstrap_ci`, used directly by `agreement.core`) is unaffected
— this gap is specific to `ppi_estimate`'s two-term variance decomposition.

**Reverses if:** Wave 2 gives the unlabelled judge pool a `worker_id` join (via `FrameRef`),
at which point both variance terms can be clustered and `clustered=True` becomes fully honest
again — a follow-up decision at that point, not before.

## D040 — `FrameRef.fps`/`codec` join the eval-arm null-together group

Starting Wave 2's real evaluation-parquet adapter (`docs/WAVES.md`) surfaced a genuine gap in
the Wave 0 `FrameRef` freeze: `fps: float` and `codec: str` were required, non-nullable fields,
but the real evaluation parquet schema — read live, not assumed —
(`hf://datasets/builddotai/Egocentric-10K-Evaluation@d74b7883.../egocentric_10k.parquet`, and
confirmed identical on the `ego4d`/`epic_kitchens` siblings) is exactly `frame_id: string,
image: struct<bytes, path>, source_dataset: string, hand_count: int32, active_labor: string`
— no video-level column at all. There is no real fps or codec to report for an `E10k-*`/
`P2k`/`G200-*`/`R100` frame, the identical root cause `docs/UPSTREAM-FINDINGS.md` F9 already
gives for the missing `factory_id`/`worker_id`/`clip_id`/`timestamp_s`: the evaluation release
ships extracted stills with no source-video reference, full stop.

**Fixed:** `fps`/`codec` are now `float | None`/`str | None` and join the existing
null-together group, now six fields, sharing the same `why_no_provenance` requirement.
`width`/`height` stay required for every frame — unlike fps/codec, they are always recoverable
by decoding the frame's own image bytes (verified the evaluation parquet's `image` struct
carries standard decodable image bytes), independent of any source-video metadata.

**Verified live**, without any HF credential (the evaluation release is `gated: False`,
`private: False` — unlike the contact-gated `Egocentric-10K`/`Egocentric-100K` corpus
datasets `.env.example` warns about): aggregating each evaluation parquet's own
`hand_count`/`active_labor` columns exactly reproduces every published headline figure
(Egocentric-10K 3.58/96.42/76.34/91.66%, Ego4D 32.67/67.33/36.95/50.07%, EPIC-KITCHENS-100
9.63/90.37/61.05/85.04% — all matched to two decimal places). This is a data-integrity
cross-check, not H1's replication: H1 requires vernier's own independent `gemini-2.5-flash`
call, and reading Build AI's own recorded per-frame answers back out of their own published
parquet would be circular if presented as a replication — it is not used as one anywhere.

**Blast radius, checked directly:** exactly two files constructed an eval-arm-style `FrameRef`
before this fix (`tests/fixtures.py`'s `FrameRef.eval_arm_no_provenance`, and Wave 1 unit 1's
own `tests/test_sampling_draw.py::_eval_frame`, used across six of that unit's tests) — both
updated to null `fps`/`codec` alongside the existing four fields. Every malformed-fixture case
that already tested partial-null rejection (`FrameRef__missing_worker_id`,
`FrameRef__partial_provenance_null`, `FrameRef__null_provenance_missing_reason`) still
constructs frames with non-null `fps`/`codec`, so they remain valid violations under the
6-field validator without needing any change. `python3 -m pytest` (278 passed) and `mypy
--strict` (clean) confirmed after the fix; `make fixtures` regenerated exactly one file
(`FrameRef__eval_arm_no_provenance.json`).

**Reverses:** nothing pre-registered, and nothing in any already-committed Wave 1 unit's
production logic — no unit reads `FrameRef.fps`/`.codec` today. This is a correction to an
unimplementable-for-real-data Wave 0 field requirement, discovered the same way D031/D033/D037
were: by actually trying to use the frozen interface against real inputs rather than trusting
it was complete.

## D041 — Second frontier judge pinned to `claude-sonnet-5`, not Opus

`docs/PRE-REGISTRATION.md`'s judge panel table names "Claude (Opus/Sonnet 5)" without choosing
between them — the same kind of open size choice D034 resolved for the DINOv3 backbone. Wiring
`judges/claude.py`'s real API call (Wave 2 prep) forced the choice: pinned to
**`claude-sonnet-5`**.

**Why Sonnet over Opus:** cost. Public per-token list pricing at time of writing is $2/$10 per
million input/output tokens for Sonnet 5 versus Opus's materially higher rate, and the panel's
purpose ("second frontier judge, different lineage") is satisfied by either — this project has
no stated reason to prefer Opus's extra capacity for a bounded classification task
(hand-count/manipulation), and D008/METHOD.md's compute-cost discipline (Result 2's kill-gate,
rung 1's "laptop-runnable" framing) favors the cheaper choice whenever nothing else forces the
more expensive one.

**Verified, not assumed:** the exact model literal `"claude-sonnet-5"` is a real, currently
valid value in the installed `anthropic` SDK's own `Message.model` type (checked against the
installed package's type definitions, not guessed from documentation prose).

**Reverses if:** Sonnet 5 turns out to refuse or systematically mis-parse the response schema
at a rate that makes it a worse "second opinion" than Opus would be — checkable only once real
calls happen (Wave 2), not before.

## D042 — Judge panel reframed: `gemini-2.5-flash` is dead, Anthropic is out, one self-hosted judge remains

Testing the real credentials Caio provided mid-Wave-2 surfaced a genuine, unforeseeable blocker,
verified live against a fresh API key, not assumed: `models/gemini-2.5-flash` — the exact model
Build AI's published quality metric is based on, and the literal subject of pre-registered H1 —
returns `404 NOT_FOUND`:

> "This model models/gemini-2.5-flash is no longer available to new users. Please update your
> code to use models/gemini-3.6-flash for the latest features and improvements."

Confirmed this wasn't a formatting fluke (tried both `gemini-2.5-flash` and the fully-qualified
`models/gemini-2.5-flash`); the model still appears in `client.models.list()` but is closed to
generation calls for a new key. Separately, Caio ruled out Anthropic entirely and judged
auditing an already-obsolete model pointless now that "sota is at another bar" — asking to
reframe the study rather than route around the outage.

**What this means for H1/H1b.** A live replication of "does `gemini-2.5-flash` reproduce its
own published figures" is now permanently impossible for a new key, and would be scientifically
invalid to fake with a substitute model (measuring model Y and calling it a replication of
model X's claim is a category error, not a workaround). **H1 and H1b are redefined from a live
replication to a comparison**: the "old" side uses Build AI's own already-published numbers —
legitimate here specifically because it is never presented as an independent replication of
those numbers, only as the historical record being compared against (this was independently
verified live to exactly match the evaluation parquet's own `hand_count`/`active_labor` columns,
to two decimal places, across all three corpora — see D040's live cross-check). The "new" side
is a live call to the current judge on the same frames. This is a materially different, weaker
claim than the original H1 — reported as such, not dressed up as the original replication.

**Judge panel: three judges down to one.** Options considered and rejected, in order:
- **GPT-5.4-mini (OpenAI)** — the first recommendation: no data-residency question, cheap
  (~$0.75/$4.50 per 1M tokens), actively maintained. Rejected only because Caio preferred an
  open-weights, self-hosted judge over any paid API.
- **DeepSeek v4-pro / v4-flash-vision-exp, GLM-4.6V (Zhipu)** — cheaper still, and genuinely
  competitive vision models, OpenAI-API-compatible. Rejected on a real flag, not benchmarks:
  both route to China-hosted infrastructure with no confirmed non-China data-residency option,
  which intersects with corpus-licensing questions this project already tracks (`ETHICS.md`,
  Ego4D's redistribution restriction to research/academic contexts) — a compliance question
  worth resolving before wiring, not a latency/cost tradeoff, and it was never resolved because
  Caio chose self-hosting instead of forcing that resolution.
- **Qwen3-VL-30B-A3B (MoE, 4-bit) / Qwen3-VL-32B (dense, 4-bit)** — both fit a single L4's 24GB
  only via aggressive quantization with no first-party checkpoint, a real accuracy risk on
  exactly the subtle visual judgment calls (glove occlusion, partial hands) this task lives on.

**Pinned: `Qwen/Qwen3-VL-8B-Instruct-FP8`**, self-hosted. The only option with a first-party
(not community) quantization and comfortable L4 headroom; this bounded classification task
doesn't need the larger variants' extra capacity enough to justify the quantization-accuracy
gamble. Served via vLLM's OpenAI-compatible mode — Modal first (~$0.80/hr for an L4, verified
live, `min_containers`/`scaledown_window` per Modal 1.0's naming for warm serving), AWS once
Modal credits run out, same client code either way (the point of the OpenAI-compatible-server
choice: swapping backends is a deployment change, not a code rewrite).

`src/vernier/judges/gemini.py` and `judges/claude.py` (real `google-genai`/`anthropic` SDK
wiring, built and independently reviewed earlier the same session per `docs/WAVES.md`'s loop)
are retired along with their tests — real, working code, but no longer part of the design, and
this project's own minimalism rule doesn't keep unused code around "just in case."

**Reverses D041** (`claude-sonnet-5` pinned as the second frontier judge) — moot now that
Anthropic is out of the panel entirely, not merely deprioritized.

**Reverses if:** access to `gemini-2.5-flash` reappears for this account (e.g. a grandfathered
path) — this alone does NOT license silently reverting to the original three-judge design
without checking with Caio first, since the reframe was also a deliberate judgment call about
SOTA having moved on, not purely a forced-by-unavailability decision.

---

## D043 — The published "JSON response schema" claim (D014/F1) was wrong; judge parsing rewritten

Caught by an actual live call, not inspection: the Qwen3-VL judge server, deployed and
smoke-tested this session, was fed the real, pinned `P0b` hand-count prompt against a real
frame and answered `"2"` — correct, matching that frame's real published `hand_count` label
exactly — and `judges/base.py`'s `parse_hand_count_response` classified it `"unparseable"`.
Same result for the manipulation task (`"yes"`, correct, unparseable).

Root cause: D014/`UPSTREAM-FINDINGS.md` F1 claimed Build AI's shipped prompts specify "a
constrained JSON response schema (`hand_count` as INTEGER; `answer` as an enum of `yes`/`no`)".
That is false. Read directly, both pinned prompt files
(`docs/upstream/P0a-hand_count.txt`/`P0b-hand_count.txt`, `P0a-active_manipulation.txt`/
`P0b-active_manipulation.txt` — byte-identical to a fresh live download of Build AI's own
`prompts/*.txt` from the evaluation-release repo, re-verified this session) end in a bare-value
instruction: "Return only one of: 0, 1, 2. No extra words." and 'Respond only with: "yes" or
"no."'. Every derived variant (`judges/prompts.py`, P1-P7) preserves that bare-value ending;
P7's confidence extension appends a comma and a number, still not JSON:
"...followed by a comma and a confidence value... No extra words." F1 conflated the
*evaluation parquet's stored column schema* (`hand_count: int32`, `active_labor: "yes"/"no"` —
a real schema, just not a *prompted* one, confirmed via the parquet footer) with what the
prompt actually instructs the model to emit — and this went uncaught through Wave 1's fixture-
and-mock-based tests because every test's own mocked "raw response" was written in the same
(wrong) JSON shape the code expected, so parser and test agreed with each other and disagreed
with reality together.

**Fixed**: `judges/base.py`'s `parse_hand_count_response`, `parse_manipulation_response`, and
`build_confidence` rewritten around one shared regex (`_VALUE_RE`) matching the real format —
a bare `0`/`1`/`2` or `yes`/`no` (case-insensitive, tolerant of surrounding quotes/backticks and
a trailing period, since that much noise isn't a content deviation), optionally followed by a
P7-style `, <confidence>`. `_extract_json_object` (JSON extraction, markdown-fence handling)
deleted — nothing in the real format ever needs it. All 28 of that file's tests rewritten
against real bare-value fixtures instead of JSON ones; `test_judges_qwen3vl.py`'s mocked
`_call_qwen3vl` return values updated the same way. Re-ran the live call after the fix: same
frame, same prompt, `status: "ok"`, `hands_visible: 2`, `manipulation: true` — both matching
the frame's real published labels.

Also caught and fixed in the same pass, same root cause (a real live 404, not assumed):
`Qwen3VLJudge._client`'s `base_url` was missing the `/v1` path segment vLLM's OpenAI-compatible
server actually serves at — `openai.OpenAI()`'s *default* base_url already ends in `/v1`, but
the client does not append it for a custom one. Every real call would have 404ed regardless of
the parsing fix above. Fixed alongside, with its own regression test
(`test_client_base_url_appends_v1_for_vlllms_openai_compatible_routes`).

Corrected everywhere the false JSON claim appeared in a live (non-frozen, non-gitignored) doc:
`docs/UPSTREAM-FINDINGS.md` F1 (correction appended, not silently rewritten — the false claim
stays visible with the correction attached, matching this project's own "correction discipline
... applied first to itself" framing), `README.md`, `llms.txt`. `AGENTS.md`/`docs/RUBRIC.md`/
`docs/PRE-REGISTRATION.md` never actually carried the claim despite D014 listing them.

The lesson, consistent with `docs/HANDOFF.md`'s own recorded ones (D031/D032): a claim read
from an upstream artifact and then relied on by hand-written mocks, without ever being
exercised against the real thing, can be wrong in a way that a fully-green test suite hides
completely — cross-checking against a live call is what surfaced this, matching this project's
own repeated finding that self-consistent code and tests are not the same thing as correct
code.

**Reverses if:** nothing. It was a factual error, corrected against primary sources (the real
prompt files, re-verified live) and a real live call.

---

## D044 — `HF_TOKEN` does not actually unblock the raw Egocentric-10K corpus

Corrects a claim this session itself made earlier (`docs/HANDOFF.md`, since fixed): that
`HF_TOKEN` was "confirmed to unblock" `builddotai/Egocentric-10K` (the raw, gated corpus
`S10k-U`/`S10k-S` need). That was based on `HfApi().dataset_info(...)`/`list_repo_files(...)`
succeeding — which HF permits against gated-repo *metadata* regardless of access — not on an
actual file download. A real `hf_hub_download` against the same repo, same token, returns
`GatedRepoError: 403 ... you are not in the authorized list`. The account behind this token has
not been granted access to this specific gated dataset; a real, outstanding blocker, not a
code gap.

Separately, checking `list_repo_files` (which does work) shows the raw corpus is not a parquet
at all: `factory_{NNN}/workers/worker_{NNN}/factory{NNN}worker{NNN}_part{NN}.tar` — WebDataset
tar shards, plus one `intrinsics.json` per worker. `S10k-U`/`S10k-S`'s real adapter will need
tar extraction, and, if the shards hold video rather than still frames, frame extraction on top
— a different shape of work than the evaluation-release parquet adapter, not a same-pattern
port of it.

**Lesson, same shape as D043's**: a claim in this repo's own docs, made from a metadata-only
check, was taken as "access confirmed" and repeated without a real download ever being
attempted. Caught this time before any code was written against it, not after.

**Reverses if:** the account behind `HF_TOKEN` is granted access to
`builddotai/Egocentric-10K` (Caio requesting/confirming it on the dataset page) — at which
point `S10k-U`/`S10k-S` wiring can proceed, starting from an actual look at one real `.tar`
shard's contents, not from this entry's own untested assumption about what's inside them.

---

## D045 — `_load_parent_membership` was passing a file path where a directory was expected

Caught only by actually running `scripts/draw_all_samples.py` end to end for the first time,
against real written membership -- not by any existing test, all of which monkeypatch
`membership.load_membership` without ever checking the `path` argument it receives.

`membership.load_membership(sample, path)`'s own contract is that `path` is the membership
ROOT DIRECTORY; it appends `<sample>.json` itself. `sampling/draw.py`'s
`_load_parent_membership` instead called it as
`membership.load_membership(parent, _membership_path(parent))`, where `_membership_path`
already returned the full file path (`_MEMBERSHIP_ROOT / f"{parent}.json"`). Every real subset
draw (`P2k`, `G200-ego`, `G200-ego4d`, `G200-epic`, `R100`) would have looked for
`data/membership/<parent>.json/<parent>.json` -- a path that can never exist -- and raised
`MembershipNotFoundError`, 100% of the time, the moment anything tried to actually draw one of
them against real on-disk membership rather than a monkeypatched pool.

**Fixed**: `_load_parent_membership` now passes `_MEMBERSHIP_ROOT` directly; the now-fully-
redundant `_membership_path` helper (used nowhere else) is deleted. A new regression test
(`test_load_parent_membership_passes_the_root_directory_not_a_file_path`) asserts the exact
`path` value `load_membership` receives, which none of the existing monkeypatch-based tests
did -- that gap in what was being asserted, not a gap in what was being run, is why this
shipped through Wave 1's review undetected.

Verified live end to end after the fix: `scripts/draw_all_samples.py` (new this session, see
below) drew and persisted all eight currently-unblocked samples in the real pre-registered
dependency order --`E10k-ego`/`E10k-ego4d`/`E10k-epic` (10,000 each), `P2k` (2,000),
`G200-ego`/`G200-ego4d`/`G200-epic` (200 each), `R100` (100) -- each with zero duplicate
`frame_id`s. `S10k-U`/`S10k-S` skip cleanly (D044).

**Lesson, third time this session (D043, D044, now this)**: a mocked/monkeypatched test suite
that never exercises the real call it's standing in for can hide a wiring bug indefinitely.
Each of these three was caught by the same intervention -- actually running the real thing,
end to end, against real data -- not by more unit tests written the same way as the ones that
already existed.

**Reverses if:** nothing. It was a real bug, fixed and verified live.

---

## D046 — `image_bytes_for` was keyed by `frame.sample`, breaking every subset-sample frame

Caught building `scripts/human_labels_cli.py` (new this session) and running a real, non-
interactive integration check against it before considering it done -- not by any existing
test, since `image_bytes_for` had none of its own before this.

`image_bytes_for(frame)` looked up `_eval_frame_bytes_by_id(frame.sample)`, i.e. it only ever
searched the ONE evaluation parquet named by `frame.sample`. That is correct for a frame whose
`sample` is one of the three root arms (`E10k-ego`/`E10k-ego4d`/`E10k-epic`) but wrong for
every subset sample: `_draw_subset`/`_draw_r100` (`sampling/draw.py`) relabel `sample` to the
subset's own name (`P2k`, `G200-*`, `R100`) via `model_copy`, discarding which root arm a frame
actually came from. `R100` is the sharpest case -- it draws from the *union* of three different
root arms, so `frame.sample == "R100"` can never by itself say which of the three files to
search. A real call, `image_bytes_for()` on a real `G200-ego4d` frame returned by
`labels.tool.next_frame()`, raised `NotImplementedError` (the `_download_eval_parquet` guard
firing on `"G200-ego4d"`, a name `_EVAL_PARQUET_FILENAME` never had) -- exactly the frames
Wave 3's labelling tool needs to show a rater.

**Fixed**: `image_bytes_for` now searches all three root arms' cached `frame_id -> bytes` maps
in turn (`frame_id`, a UUID4, is the only key unique across the whole release), returning the
first hit. `S10k-U`/`S10k-S` frames keep their own explicit `NotImplementedError` -- a
different, unwired dataset, not folded into the same not-found path as a real missing frame.
Five new tests cover the root case, a subset-sample case, the R100-union case, the
S10k-U/S10k-S case, and a genuinely-not-found case -- `image_bytes_for` had zero tests of its
own before this.

Verified live end to end: `next_frame(pass_="primary", ...)` returns a real `G200-ego4d`
frame, `image_bytes_for` resolves it to a real, PIL-decodable 2560x1920 JPEG; the `retest` pass
similarly resolves a real `R100` frame to a real 1920x1440 JPEG.

**Lesson, fourth time this session (D043, D044, D045, now this)**: the common thread across
all four is a function with no test of its own, or tests that share the same gap the function
has -- caught only by actually calling the real thing with real, representative input, not by
adding more tests shaped like the ones that already existed.

**Reverses if:** nothing. It was a real bug, fixed and verified live.

---

## D047 — Rung-1's real distillation teacher was wrong; caught by an independent review, not by this session's own checking

`docs/review.md` (an independent, fresh-context review of the whole repository post-D042,
dated 2026-09-01) found a real, costly design mistake in `scripts/generate_rung1_labels.py`
that this session had already started running against real infrastructure: `docs/METHOD.md`
E7 states rung 1 trains "on `gemini-2.5-flash` `P0a` labels" -- the judge behind the published
number, so the instrument reproduces *that judge*, errors included (D007's stated reason: an
instrument that improved on the thing it measures would stop measuring it). The script instead
called the live Qwen3-VL judge to *generate* those training labels. But `gemini-2.5-flash`'s
own labels are not missing -- they are the `hand_count`/`active_labor` columns already shipped
in the evaluation parquets (`docs/UPSTREAM-FINDINGS.md` F9), verified live to reproduce the
published headline figures to two decimal places on all three corpora (D040, D042's own live
cross-check). Training on fresh Qwen3-VL calls instead distils a substitute judge nobody's
published claim rests on; rung 2 as originally scoped (a Qwen3-VL LoRA fitted to Qwen3-VL-8B's
own labels) would have been self-distillation, adding nothing.

**Real cost of the mistake, stopped before it completed**: the flawed run was live against the
deployed Modal judge for ~31 minutes (real API spend, roughly $0.40 at observed per-call
rates) before being killed on reading the review. The full run, had it completed, would have
spent ~$5 and ~5.8 hours producing labels for the wrong teacher.

**Fixed**: `scripts/generate_rung1_labels.py` rewritten to read the real, already-stored
`gemini-2.5-flash` labels directly from the pinned evaluation parquets -- zero live judge
calls, zero cost, real runtime ~1 second. Per the review's own recommendation, extended beyond
`E10k-ego` alone to all three evaluation arms (`E10k-ego`/`E10k-ego4d`/`E10k-epic`), each minus
its own `G200-*` eval-holdout set -- 29,400 real labels generated and verified (sensible
distribution: `hands_visible>=1` at ~84.7% pooled across all three corpora, consistent with
Ego4D's and EPIC-KITCHENS-100's own lower published rates pulling the blend down from
Egocentric-10K's 96.42% alone). The stored-label extraction logic is now shared
(`scripts/published_labels.py`) between this script and `scripts/e2_replication.py`, which
already needed the identical real-parquet read for its own H1 comparison.

The live-Qwen3-VL-calling mechanism (`scripts/judge_concurrency.py` plus the per-frame call
loop) is not discarded -- it is real, tested infrastructure with a real, different use: Qwen3-VL
as the live *comparison* judge for E4 (judge-vs-judge agreement) and E6 (domain bias), a second
judge arm alongside the frozen `gemini-2.5-flash` labels, per the review's second point ("the
panel is two judges, not one"). Repurposed into `scripts/generate_qwen_comparison_labels.py`,
correctly framed as the comparison arm, not the distillation teacher.

Also recorded from the same concurrency work, independent of this mistake: naive client-side
concurrency (`ThreadPoolExecutor`, up to 8 workers tested) measurably HURT real throughput on
the current single-container Modal deployment (sequential ~0.47 frames/sec vs. ~0.36 at 4
workers vs. ~0.26 at 8 workers) -- single-GPU contention on short bursts, not the hoped-for
speedup; Modal's own autoscaling needs longer sustained load than a smoke-scale test exercises
to add containers. `generate_qwen_comparison_labels.py` defaults `--max-workers=1` for this
reason, pending real evidence at a run size long enough for autoscaling to matter.

**Not yet absorbed from `docs/review.md`, tracked as follow-up, not done in this entry**: R2
(pseudo-cluster design effect), R3 (second rater on R100), R4 (judge test-retest), R5
(pretraining-contamination confound on H5), R6 (pre-data gold-size amendment), R7 (pin the
rung-3 guarantee mechanism), R8 (authorize the full-N E2/E5 run), R9 (explicitly kill Result 2),
R10 (a drift lint for stale prose), and the stale-prose sweep across `README.md`, `AGENTS.md`,
`PRE-REGISTRATION.md`'s judge-panel table, `METHOD.md`, `EVALS_CARD.md`, `REPRODUCTION.md`,
`RED-TEAM.md`, `ARCHITECTURE.md`, `BENCHMARK.md`, and `RUBRIC.md`'s P3/P4 mislabel. This entry
closes only the one item large enough to be actively spending money and running against the
wrong target: R1 itself.

**Lesson**: this is the first bug this session caught via an external review rather than by
running the thing itself and checking the result -- the same real-verification discipline
(D043-D046), applied from a second, independent context instead of the one that wrote the
code, per this project's own validator-independence practice. It found something none of this
session's own live runs would have surfaced, because the running code was internally
consistent and "worked" by every test that shared its own assumption about the teacher.

**Reverses if:** nothing. It was a real, verified design mistake, caught, and fixed before
completion.

---

## D048 — Absorbing `docs/REVIEW.md`: kill Result 2, disclose the pretraining confound, correct stale pre-D042 prose

Bundles three of `docs/REVIEW.md`'s recommendations into one entry, per its own suggested
order ("R9, R1, R5 and the stale-prose sweep... all documentation, all pre-data, all cheap").
R1 was large enough to warrant its own entry (D047); this one covers the rest of that bundle.

**R9 — Result 2 (the transfer probe) is dropped, explicitly.** Every document still described
it as "kill-gated" or "pending", which a reader cannot distinguish from "not yet attempted".
The real reasons it does not run, all already on the record separately, are restated together
here for the first time: the raw Egocentric-10K corpus is inaccessible to this account
(D044); EPIC-KITCHENS-100 registration requires an institutional email this project does not
have (`SURVEY.md`); and the evaluation release ships no downstream-task labels to probe
against at all, regardless of access. The kill-gate (a timeboxed compute spike) is never
reached — the inputs it would need do not exist for this project, which is a stronger and
more final statement than "the gate is closed." Updated: `README.md`, `docs/METHOD.md` E9,
`docs/BENCHMARK.md` R6, `docs/COVERAGE.md`, `docs/ARCHITECTURE.md` `probe`, `docs/WAVES.md`.

**R5 — the pretraining-contamination confound on H5 is disclosed, not mitigated.** EPIC-
KITCHENS-100 and Ego4D are public and plausibly in Qwen3-VL's own pretraining mix; the gated,
November-2025 Egocentric-10K almost certainly is not. Pretraining exposure would bias judge
accuracy in the *opposite* direction from H5's prediction, so a null H5 result has three
readings (no effect / underpowered per D035 / contamination masking a real effect) that cannot
currently be told apart. Recorded as `docs/RED-TEAM.md` A15 and a new `docs/COVERAGE.md` row.
The review's proposed cheap probe (ask the judge to name the source dataset per frame, report
accuracy per corpus as a memorisation signal) is NOT run in this entry — a real live-judge
cost, deferred alongside R8's scale-up decision, tracked as still-open.

**Stale pre-D042 prose corrected** across `README.md` (status block, Result 2), `AGENTS.md`
(current-state line), `docs/METHOD.md` (E2, E4, E5, E7, E8), `docs/EVALS_CARD.md`, `docs/
REPRODUCTION.md`, `docs/RED-TEAM.md` (A3, A7, A11, A15 new), `docs/ARCHITECTURE.md` (`judges`,
`probe`), `docs/BENCHMARK.md` (R1, R6), `docs/COVERAGE.md`. Two real factual bugs also caught
and fixed in the same pass, independent of D042: `docs/RUBRIC.md` Task 1 rule 3 said gloves are
"why P4 exists" — P3 is gloves, P4 is reflections, per `PRE-REGISTRATION.md`'s own table; and
`docs/RED-TEAM.md` A4 said "Eight variants × three figures is 21" — the real count is seven
variants (7 × 3 = 21, the arithmetic was already right, only the word was wrong).

**`docs/PRE-REGISTRATION.md` gets a new `## Amendments` section**, appended per the review's
own recommendation — the frozen text above it is untouched, word for word; the new section only
points at this entry and D042/D044/D047, so a reader of the frozen document is not misled about
what actually happened since it froze. This is itself the kind of change `PRE-REGISTRATION.md`'s
own rules permit (a `DECISIONS.md`-tracked amendment, not a silent rewrite) — recorded here so
the permission is on the record, not just exercised.

**Also corrected, a real capability gap in the frozen calibration claim (`docs/METHOD.md` E8,
review point 3, not R5 or R9 but adjacent):** "calibration restricted to P7" was true only for
Build AI's own closed-API measurement (their schema exposes no confidence under any prompt).
The self-hosted Qwen3-VL judge exposes a real answer-token logprob regardless of prompt variant
(`judges/qwen3vl.py`, confirmed working live against real frames, `docs/HANDOFF.md`) —
calibration of the open judge under the *published* bare-value P0 format is a real, measurable
result, not gated to P7. The "what could not be checked" entry for H7 should narrow once this
is actually computed at scale; not done in this entry.

**Not done in this entry, tracked as open follow-up from `docs/REVIEW.md`:** R2 (pseudo-cluster
design effect on Build AI's own frames), R3 (a second rater on `R100`), R4 (judge test-retest),
R6 (pre-data gold-size/allocation amendment for H5 — time-critical: must land before the first
label is written), R7 (pin the rung-3 guarantee mechanism), R8 (authorize the full-N E2/E5
run), R10 (a drift-lint script for `make validate`), and R5's own live probe (disclosed here,
not run).

**Reverses if:** access to the raw Egocentric-10K corpus and an institutional EPIC-KITCHENS-100
affiliation both materialise — then Result 2's kill-gate re-opens as originally pre-registered,
per R9's own stated reversal condition.

---

## D049 — Pin the rung-3 guarantee mechanism (`docs/REVIEW.md` R7): Learn-then-Test / conformal risk control

H6 promises "an agreement floor against human gold, at a stated coverage" — a finite-sample
statistical guarantee. `distil/cascade.py`'s current `calibrate_threshold` does not deliver
one: it finds the highest-coverage confidence threshold whose *empirical* accuracy on
`held_out_gold` clears `target_floor`, with no correction for the finite size of that
held-out set. The code's own docstring already flags this ("No safety margin... this can pick
a threshold that clears `target_floor` on this particular sample by chance without reliably
clearing it on new data"), caught by an earlier independent review pass before this one. R7's
point is sharper: "reports a floor" is a promise, not yet a procedure, and naming the
mechanism in advance is what makes a finite-sample guarantee at `n≈100-200` achievable at all
— choosing it after seeing results would be exactly the kind of post-hoc analysis choice this
project's own pre-registration discipline exists to prevent.

**Pinned mechanism: Learn-then-Test (Angelopoulos, Bates, Candès, Jordan, Lei, 2110.01052) /
conformal risk control**, the machinery Trust-or-Escalate (2407.18370, already cited in
`MODEL_CARD.md`) itself builds on. Concretely: a grid of candidate confidence thresholds, a
per-threshold p-value against the target error rate via a concentration inequality (Hoeffding-
Bentkus), and a family-wise-valid procedure (e.g. fixed-sequence testing over the grid, ordered
by increasing coverage) to select the threshold with the highest coverage whose bound still
controls the true error rate at the stated confidence level (e.g. 90%) — not just the observed
rate on `held_out_gold`.

**Calibration/scoring split, pre-declared**: with 200 gold frames on `G200-ego`, threshold
search uses Build AI's own stored labels (`docs/DECISIONS.md` D047's free, zero-live-call
labels) wherever the diagnostic in `distil/linear_probe.py`'s `fidelity` needs a threshold
sweep; `G200-ego`'s human gold is reserved *solely* for verifying the floor the mechanism
selects, never for searching over candidate thresholds — the same held-out discipline
`calibrate_threshold`'s own docstring already requires of its caller, now given a concrete
split to follow rather than left to the caller's judgment alone.

**Not done in this entry**: the actual Learn-then-Test implementation. `distil/cascade.py`'s
current point-estimate `calibrate_threshold` is left as-is, with a docstring pointer added to
this entry — rewriting the threshold-selection algorithm to a real finite-sample-valid
procedure is a separate, real statistics-engineering task, not a naming exercise, and a rushed
half-implementation risks a subtler bug than the current, honestly-flagged limitation.
`docs/MODEL_CARD.md`'s rung-3 row updated to name the pinned mechanism.

**Reverses if:** nothing. H6 as pre-registered needs a named, pre-declared mechanism to be
checkable at all, and this is that mechanism.

---

## D050 — A drift lint for stale design language (`docs/REVIEW.md` R10)

`AGENTS.md` rule 2 already said prose carrying a number the pipeline no longer produces is a
bug, and `make validate` should catch it — but that only ever ran a check for numbers. D048
found thirteen files still describing the pre-D042 three-judge panel as current design, weeks
after it was retired, caught only by an independent review reading every file by hand. A
mechanical check for exactly this class of drift did not exist.

`scripts/check_stale_prose.py`, wired into `make validate` as `check-stale-prose`: fails if
`"three judges"`, `"three-judge panel"`, `"documentation only"`, `"no judge has been called"`,
or `"JUDGES=gemini"` appears in any public `.md` file, outside `docs/DECISIONS.md`,
`docs/UPSTREAM-FINDINGS.md`, `docs/LINEAGE.md`, `docs/REVIEW.md`, `docs/WAVES.md` (its Wave-1
unit table is deliberately a historical record), and `docs/RED-TEAM.md` (its own stated rule:
"Attack" paragraphs are "published unedited" once written — an attack posed using the language
of the flaw it describes is not itself a stale claim, and editing it to dodge a lint would
violate the file's own discipline).

**Deviates from `docs/REVIEW.md` R10's literal pattern list in one place, deliberately**: R10's
own proposed list includes a bare `gemini-2.5-flash` match. Checked live before adopting it:
14 files legitimately mention `gemini-2.5-flash` post-D047/D048 (it is the real, correct name
of the model whose *stored* labels rung 1 trains on) — a lint on the bare model name would have
immediately failed on the exact fixes that corrected the real staleness. Dropped from the
pattern list for that reason; the other four patterns describe a state or design with no
legitimate current use in any context, so they stay as R10 specified them.

Running the real lint against the current repo (before this entry's own fixes) found five real
hits, two of which were newly introduced by this session's own D048/D049 prose (`docs/METHOD.md`,
`docs/PRE-REGISTRATION.md`'s new Amendments section) — both fixed by rewording around the
trigger phrase without changing meaning (e.g. "three judges" → "three live judges"), not by
carving out more exemptions. `README.md` and `docs/DATASET_CARD.md` had two further real,
previously-uncaught hits, fixed the same way D048 fixed the rest.

`AGENTS.md` rule 2 extended by one sentence to name this check.

**Reverses if:** nothing. A drift lint is a permanent addition, not a point-in-time fix — it
exists specifically so this class of staleness cannot recur silently.

---

## D051 — R2 (pseudo-cluster design effect) is blocked: the pinned DINOv3 checkpoint is gated, and this account lacks access

Attempted `docs/REVIEW.md` R2 (embed every `E10k-*` frame with the pinned DINOv3 backbone,
cluster by similarity, run the cluster bootstrap over the pseudo-clusters as an exploratory
proxy for H2) as the next zero-cost, no-human-label item. Real, same pattern as D044: a live
`hf_hub_download` of `facebook/dinov3-vits16-pretrain-lvd1689m/config.json` (`docs/DECISIONS.md`
D034's pinned backbone) returns `GatedRepoError: 403 ... you are not in the authorized list`.
`HfApi().list_models()`'s own `gated` field for this repo is unreliable here -- it reported
`None` (not gated) for the same repo a real download attempt just refused, the same
metadata-vs-real-access gap D044 already found once this session, confirmed a second time on a
different resource.

`torch`/`transformers` (real, already-implied dependencies for this pre-registered backbone,
not new ones) added to the `probes` extra regardless -- declaring the real dependency now costs
nothing and is correct whenever access resolves.

Several unofficial third-party re-uploads of the same weights exist and are not gated
(`vincentamato/dinov3-vits16-pretrain-lvd1689m-pt-outputs`, `Fanqi-Lin-IR/dinov3_vits16_pretrain`,
others found via a live search). **Not used**: D034 pinned the *official* Meta checkpoint,
verified live against the real Hub listing specifically to avoid exactly this kind of
unverified substitution; a third-party mirror could silently carry different weights, and
nothing in this session verified any of them against a known checksum for the real release.
Substituting one without that verification would risk the same category of problem D034's own
pinning discipline exists to prevent, for an exploratory analysis whose whole point is to be a
trustworthy proxy.

R2 is not attempted further this session. Caio's real options: request Meta's manual access
grant for the gated checkpoint (real HF Hub UI action, unknown turnaround time); accept a
verified third-party mirror after checking it against a real weight checksum; or drop R2 as
also out of reach, alongside `S10k-U`/`S10k-S` (D044) and Result 2 (D048) -- all three of this
session's real, checked-not-assumed access blockers now point at the same underlying
constraint: this HF account's gated-content authorization is narrower than its metadata-read
access, discovered three separate times by three separate real download attempts rather than
once and generalized.

**Reverses if:** access to the pinned checkpoint is granted, or a third-party mirror is
verified against a real checksum for the official release.
