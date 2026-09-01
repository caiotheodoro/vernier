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
