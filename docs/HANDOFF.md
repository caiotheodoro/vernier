# Handoff

The resume point. A fresh session should be able to continue from this file without
re-deriving anything.

**Last updated: 2026-09-04 — (D071/D072) H2 is measured and closed.** The raw-corpus adapter
D065 declined to size turned out to be small: ffmpeg's `subfile` protocol extracts one frame
from an h265 mp4 inside a tar over HTTP range requests, so no new dependency was needed, and a
tar header is 512 bytes at a computable offset, so `scripts/build_corpus_manifest.py` indexed
all 19,495 shards (192,903 clips) in 23 minutes moving ~150MB against a ~16TB corpus. H2 then
ran at the pre-registered N=10,000 on both arms and **does not hold**: design effect 1.25–1.66
against a threshold of 2. Real — every figure exceeds 1, so an iid interval here is genuinely
too narrow — but by less than pre-registered. `what_could_not_be_checked` drops from two items
to one; Result 2 alone remains, and the verdict stays `NOT_VERIFIED`. Two things found on the
way: `worker_id` is only unique *within* a factory, which would have collapsed ~2,144 clusters
into ~85 and inflated the design effect into a false positive (D071); and the corpus ships
2,144 workers against a published 2,153 (`UPSTREAM-FINDINGS.md` F12).

**Still open, in order:** Result 2 (blocked for two reasons the adapter did not touch);
`REVIEW.md` R2, now much cheaper than when it was written — the ground-truth `worker_id` this
work produced can calibrate a DINOv2 pseudo-cluster proxy against real labels, which is the
only route to saying anything about the design effect on *Build AI's own frames*
(`RED-TEAM.md` A13). The independent review of D071/D072 `WAVES.md` requires has now run
(D074): the verdict stands, the numbers reproduce bit-for-bit, and the pre-registration turned
out to state H2's threshold two ways; the card's claim text is corrected in `emit_card.py` and
the committed `MEASUREMENT_CARD.json` is regenerated with `make card` together with
`make space-data`, since the Space's `stats.json` pins the card digest.

**Prior header — (D068) the card's own H2/Result 2 text was found actively
contradicting D065 (still said "confirmed NOT authorized... 403" after access was granted) --
fixed, along with the same stale claim independently duplicated in `README.md` and
`docs/BENCHMARK.md`. `llms.txt`'s stale "nothing has run yet" status line (invisible to the
lint, which only scanned `.md`/`Makefile`) is a third occurrence of a pattern this project has
now hit three times -- fixed, and the lint's scan path widened again. `README.md` now states the real
Egocentric-100K result in its Status block and a new section. Prior (D066/D067): E2 extended to
`Egocentric-100K-Evaluation`, Build AI's current
product (D066/D067): real access was granted (terms accepted), a real synthetic-`frame_id`
scheme fills the gap left by the vendor's own removal of that column (F10), and three real bugs
(a `draw_sample` dispatch gap, a revision-check repo mismatch, a pyarrow chunking limitation,
and a `"true"/"false"` vs `"yes"/"no"` schema mismatch) were found and fixed by the smoke test
and the full run respectively -- none silently patched over. Real result: **2/3 headline
figures within +/-2pp of Build AI's own current published numbers, 2-hands the outlier
(6.14pp)** -- the identical structural pattern the original `E10k-ego` run found on their
superseded release. Cost $9.06. Also did a real, near-zero-cost discovery spike into the raw
`Egocentric-10K` WebDataset shards (D065): confirmed video, not stills -- a materially bigger
adapter than assumed, not attempted this round. Prior round (D064): `HumanLabel.difficulty` is
now a
real closed `Literal["easy","medium","hard"]` (a real, disclosed "emedium" typo in committed
label data corrected); the dead `make estimate` target (its own help text promised a
design-effect column this repo's non-clustered PPI structurally cannot supply) is removed, not
wired; the rung-1 probe is now a real, loadable artifact (`LinearProbe.save`/`.load`, joblib,
`data/rung1_probe.joblib`, tracked in git), not just a metrics JSON. Prior round (D062/D063):
real result data
(`data/membership`, `data/labels`, `data/gold_judged`, and every small computed-result JSON) is
now tracked in git, not just local; stale pre-data/pre-model prose in README/AGENTS/Makefile is
fixed and `check_stale_prose.py`'s reach widened (it now also scans `Makefile`, not just
`*.md`); H4 and intra-rater AC1 claims now carry a real bootstrap CI; `cascade.py`'s
`calibrate_threshold` now uses a Wilson-score lower bound instead of a raw point estimate
(closing the specific gap its own docstring named), and H6's real numbers changed as a real
consequence -- the floor is now reported unreachable at 95% confidence on the real, small
calibration split, not "floor met, coverage short" as before. Prior to that: Wave 3 (reduced
target, D057/D058) and Wave 4's real intra-rater/H4/H5/PPI/H7/H6 analysis (D059-D061) all
complete; the card carries 15 real claims. Prior baseline (2026-09-02): full-N E2/E5 run
completed for real (D054/D055/D056). Earlier baseline (2026-09-01): Wave S, Wave 0, the P1
hygiene tier, Wave 1's full 18-unit fan-out.**

## Where this stands

**A real `MeasurementCard` exists and is committed: `MEASUREMENT_CARD.json`, `verdict=
NOT_VERIFIED`.** Regenerate with `make card`. It now carries 15 real claims: H8
(participant-count disparity), **H1/H1b/H3 from the full-N E2/E5 run (D056)** -- H1 fails its
own criterion (2-hands 6.32pp outside +/-2pp), H1b is null, H3's headline prediction is not
supported -- **intra-rater reliability, H4, H5, and six PPI-corrected prevalence estimates
(D059)**, off Wave 3's real reduced-target human gold (93 primary, 34-overlap retest) and a
real live-judge run over all three `G200-*` sets (600 frames, `P0b`,
`scripts/judge_gold_sets.py`), **H7 (calibration, D060)**, and **H6 (distillation, D061)**:

- **Intra-rater (the pre-registration's own first falsification check): passes.** AC1=0.876
  (95% iid bootstrap CI [0.725, 1.000]) for hand_count, 0.904 ([0.743, 1.000]) for manipulation,
  n=34 -- both above the 0.70 gate. The audit is not deferred, at reduced precision (n=34, not
  the pre-registered 100).
- **H4: does not hold, direction reversed.** AC1(judge,human) hand_count=0.795 (95% CI [0.687,
  0.894]), manipulation=0.899 (95% CI [0.807, 0.969]) -- the pre-registered prediction
  (hand_count higher) is not what the real data shows. Intervals are new (D063): a real
  additional statistic, not a replacement for the point estimates.
- **H5: does not hold, direction reversed.** Judge error rate on manipulation: Egocentric
  9.09%, EPIC-KITCHENS-100 0.00% -- EPIC-KITCHENS-100 has the *lower* error, opposite the
  prediction. Already known underpowered even at full pre-registered size (D035); a null/
  reversed result here is genuinely ambiguous, not a clean refutation.
- **PPI-corrected prevalence, all 3 domains x 2 tasks**: real point estimates + 95% CIs for
  Ego4D and EPIC-KITCHENS-100 for the first time (E2 never touched them), plus a second,
  PPI-corrected view of Egocentric-10K. Not clustered (D039, still unfixed) -- each interval is
  a disclosed lower bound on true width.
- **H7: ECE=0.1505 (hand_count), 0.0645 (manipulation)** -- a real, disclosed deviation from
  "P7 only" (the self-hosted judge exposes real logprob confidence on every call, not just P7,
  D052/D053), read straight off the already-collected `P0b` data, no new judge calls. Weak
  calibration curve by construction: 99% of frames land in the single [0.9, 1.0] confidence bin
  (greedy decoding, D053), so ECE mostly reflects that one bin, not a real spread.
- **H6: does not hold.** Real rung-1 distillation on `facebook/dinov2-small` -- a disclosed,
  live-verified-ungated substitute for D034's gated DINOv3 pin (D051 found no access, and
  explicitly rejected unverified third-party re-uploads of the *same* weights; DINOv2 is a
  different, official checkpoint, not that same risk). Teacher fidelity vs. `gemini-2.5-flash`
  0.6933 (target >=0.90, not met). `AbstentionCascade`, calibrated on a real n=46 split of Wave
  3's human gold: as of D063, the threshold search requires a 95%-confidence Wilson-score lower
  bound on prefix accuracy to clear `target_floor`, not the raw point estimate (closing
  `cascade.py`'s own previously-named no-safety-margin gap) -- on this real, small split, the
  0.80 floor is now reported **unreachable at any coverage > 0, at 95% confidence**. Same
  overall outcome as before (H6 does not hold), reached more honestly this time; D061's original
  point-estimate result had instead reported floor 0.8421 (met) at coverage 0.4043 (not met).
  As of D064, the fitted probe is a real, loadable artifact -- `LinearProbe.save`/`.load`
  (joblib), `data/rung1_probe.joblib`, ~5-20KB, tracked in git -- not just this metrics JSON;
  loading it back still needs the backbone name, `_preprocess`, and the pooling choice, all
  named in `distill_rung1.py`'s own docstring, not packaged as a separate inference script.

One item remains in `what_could_not_be_checked` (Result 2), with a specific `"BLOCKER:"`
reason -- since D071 the raw-corpus adapter exists, so what remains is the institutional
EPIC-KITCHENS-100 registration and the absence of downstream-task labels in the release -- so
`_derive_verdict` (D038) returns `NOT_VERIFIED` because a real blocker remains, not vacuously.
**This "1 unmet" count is a different bucket from "checked and negative"**: H1 (2-hands
fails), H1b (null), H2 (design effect below 2, D072), H4/H5 (reversed), H6 (does not hold),
and H7 (weak calibration) are all real, checked claims in
`claims`, not blocked ones -- `what_could_not_be_checked` counts only items that could not run
at all, never a tally of "everything that isn't wrong." `verify_and_exit` returns nonzero,
for real, via `make card`. Not a placeholder, and not to be conflated with either the H8
computation itself or the D016 live-data cross-check in the next paragraph (a data-integrity
sanity check, never presented as a hypothesis result).

**Wave S, Wave 0, the P1 tier, and Wave 1 are all done and committed. Wave 2 is real, wireable
work in progress — but every path to a VERIFIED card needs a credential this environment does
not have (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `HF_TOKEN`), plus the 600 human labels (Wave
3, which is explicitly Caio's own work, not automatable). One load-bearing exception was found
and used: the evaluation release itself (`builddotai/Egocentric-10K-Evaluation`) is `gated:
False`, verified live — unlike the corpus datasets `.env.example` warns are contact-gated — so
its three parquets are downloadable with no token at all.**

**P1 tier, fully closed** (was open at the last handoff): CI (`.github/workflows/ci.yml`), the
privacy-gate git hook (`make install-hooks`), `scripts/check_eval_parquets.py` (D016, offline-
tested against synthetic parquet data), the HF revision pin (`sampling/revisions.py`, sourced
from `docs/upstream/PROVENANCE.json`), the H5/R100 power simulation (`scripts/power_simulation.py`,
D035 — found H5 underpowered at the pre-registered n and R100's 0.70 gate close to a coin flip
at the boundary; sizes unchanged, limitation recorded), an offline rubric pilot self-check
(`scripts/rubric_pilot_check.py`, D036 — found and fixed a real orphan tag, `RUBRIC.md` → 1.2.0),
the DINOv3 backbone pin (D034, `facebook/dinov3-vits16-pretrain-lvd1689m`, verified against the
real HF Hub listing), and honest non-no-op Makefile targets for every unrun experiment.

**Wave 1: all 18 units implemented, independently reviewed, and committed**, following
`WAVES.md`'s fan-out → independent-review loop (`agentgraph dispatch --tool claude` to produce,
`--tool opencode` to review, ACCEPT-only commits). 43 → 278 tests, `mypy --strict` clean,
`make validate` green throughout. One review's REJECT was a verified false positive (isolation
ambiguity from several units being produced concurrently in one shared tree before any commit —
resolved by checking two independent sources, not by trusting either report; see the `judges/
base.py` commit message). Four new decisions came out of real findings surfaced during review,
not invented afterward: **D037** (a frozen stub signature was genuinely unimplementable —
`agreement.core`'s statistic functions needed a `task` parameter the original stub had no way to
carry), **D038** (named `card`'s verdict-derivation conventions, which were sound but undocumented
outside one private helper), **D039** (a real, disclosed-but-mislabeled gap: `PPIBlock.clustered
=True` overstates what's actually cluster-robust — not fixed, needs a schema decision once Wave 2
supplies a real participant join for the unlabelled pool), and **D040** (starting Wave 2 exposed
that `FrameRef.fps`/`.codec` were unimplementable for real eval-arm data — the real parquet schema,
read live, carries no video-level column at all; both fields now join the existing null-together
group). `compute_j`/`compute_delta_j` (calibration) are honestly flagged as placeholders rather
than guessing arXiv 2605.06939's exact formula.

**The judge panel was reframed — see `docs/DECISIONS.md` D042 for the full record.** Real
credentials (`.env`, gitignored) surfaced that `gemini-2.5-flash` — the exact model Build AI's
published metric is based on, and H1's literal subject — is deprecated for new API keys
(confirmed live, 404). Caio separately ruled out Anthropic and judged auditing an obsolete model
pointless given how far SOTA has moved. **`judges/gemini.py` and `judges/claude.py` (real
`google-genai`/`anthropic` SDK wiring, built and independently reviewed earlier the same
session) are deleted, not kept as dead code** — D041 (the `claude-sonnet-5` pin) is explicitly
reversed. H1/H1b are redefined from a live replication to a comparison: Build AI's own
already-published numbers (never presented as an independent replication of themselves) vs. a
live call to the new judge. **The panel is now one self-hosted judge, `Qwen/Qwen3-VL-8B-
Instruct-FP8`**, served via vLLM's OpenAI-compatible mode — Modal first (~$0.80/hr for an L4,
verified live), AWS once Modal credits run out, same client code either way.
`judges/qwen3vl.py`'s `_call_qwen3vl` seam (already built and reviewed in Wave 1 as unit 6) is
where this lands, alongside a new `infra/modal_qwen3vl.py` serving the model. `_image_bytes_for`
(frame_id → real JPEG bytes) is still unwired regardless of judge choice, since it needs the
evaluation-parquet adapter (`sampling.draw._candidate_frames`'s own still-unwired seam) to land
first.

Also fixed while starting this: `scripts/check_eval_parquets.py --parquet` used `type=Path`,
which silently collapses a `hf://...` URI's `//` and breaks pyarrow's filesystem resolution --
caught only by actually running the CLI against the real, ungated evaluation release, not by
its existing (pure-function-only) test suite. Fixed, and now has its own regression test at the
CLI-argument-parsing boundary. Separately noted, not fixed (an operational point, not a bug):
checking membership against a parquet via repeated `hf://` fsspec reads pulls the full ~1.8GB
`image` column regardless of how few frames are being checked, since a random UUID4 `frame_id`
ordering touches nearly every row group — Wave 2's real usage should download each parquet once
locally (`hf_hub_download`) and check against that, not re-stream it remotely per check.

`SURVEY.md` returned **PROCEED, narrowed**: the contribution is H5 (cross-corpus judge
confound) plus judge-as-instrument, not judge validation, which is prior-arted. The survey also
caught four methodological errors in `PRE-REGISTRATION.md` v1.1.0, all fixed in v1.2.0 —
PPI over cluster-bootstrap-alone, Gwet's AC1 over Cohen's κ, balanced gold for H5's
interaction, and H8. Catching those is what the gate was for.

**Wave S (8 dispatched audit workers, `agentgraph dispatch`) closed all six remaining "must be
closed before publication" items and caught three further mis-citations**: D021's PPI citation
was wrong (2408.15204 is Confidence-Driven Inference, not PPI — the real PPI paper is 2301.09633),
D024's EPIC-KITCHENS-100 participant count was wrong (37, not ~45 — that was the kitchen count),
and a working-table citation (2503.05965) claimed to support H3 but does not. See `DECISIONS.md`
D030 for the full record. **Wave 0 landed, its gate passed, and it is committed** (`ea75148`):
pydantic models for every `CONTRACTS.md` record, typed stubs for the nine `ARCHITECTURE.md`
units, pytest (43 passed), mypy --strict (clean), and a fixture generator (14 valid + 19
malformed/refused cases) — `make validate` green end to end.

**Three independent AI audit reviews (`docs/private/reviews.txt`) were then cross-checked
against the actual repo in two passes, not trusted from their prose** — a distillation
train/eval leak, a `FrameRef`/evaluation-frame contract contradiction, a clustering
self-contradiction, a mislabelled "effective N," and several validator gaps were all confirmed
live and fixed (`DECISIONS.md` D031). A second, independent re-audit of that fix then caught
what D031 missed — an incomplete `AgreementCI` validator, an untouched sibling gap in
`PPIBlock.cluster_by`, the H8 relabel not reaching the `estimation` module's own identifiers,
and this file's own stale test/fixture counts and "uncommitted" claim (`DECISIONS.md` D032).
The lesson, consistent with this project's own methodology: a self-audit's first pass is not
the last word — verify the fix the same way you verified the original claim.

A direct read of Build AI's published artifacts produced eleven findings, several of which
corrected this repository's own earlier claims. See `UPSTREAM-FINDINGS.md`.

The repository was created in one session from a scoping investigation of Build AI
(build.ai) and a decision to open a research collaboration by publishing an independent
measurement rather than by making an approach. The full context, including the outreach
sequencing, is in `docs/private/OUTREACH.md`, which is gitignored and never influences a
finding.

## What exists

| | |
|---|---|
| Root | `README.md`, `CONTRACTS.md`, `AGENTS.md`, `Makefile`, `llms.txt`, `pyproject.toml` skeleton, `.env.example`, `.gitignore`, `LICENSE` |
| Protocol | `PRE-REGISTRATION.md` (rev 1.3.0, **frozen by commit**), `RUBRIC.md` (rev 1.2.0), `METHOD.md` |
| Framing | `README.md`, `methodology.md`, `LINEAGE.md`, `COVERAGE.md`, `ETHICS.md` |
| Self-criticism | `RED-TEAM.md`, fourteen attacks, opened before any result |
| Design | `ARCHITECTURE.md`, `CONTRACTS.md` |
| Output shape | `DATASET_CARD.md`, `MODEL_CARD.md`, `EVALS_CARD.md`, `BENCHMARK.md`, all deliberately unfilled |
| Reproducibility contract | `REPRODUCTION.md` |
| Survey | `SURVEY.md`, **complete**, verdict PROCEED-narrowed |
| Upstream facts | `UPSTREAM-FINDINGS.md`, F1–F11, with pinned snapshots in `docs/upstream/` |
| Decisions | `DECISIONS.md`, D001–D073 |
| Private | `docs/private/`, gitignored: outreach, country brief, email draft, self-audit log |
| Interface | `src/vernier/` — pydantic models (`models.py`) + all 18 Wave-1 units **implemented, reviewed, committed** |
| Infra | CI (`.github/workflows/ci.yml`), `make install-hooks`, `scripts/check_eval_parquets.py`, `scripts/power_simulation.py`, `scripts/rubric_pilot_check.py`, `sampling/revisions.py`, `cloud/modal_qwen3vl.py` (deployed, smoke-tested live for text) |
| Waves | `WAVES.md` — the fan-out → independent-review paradigm and every wave's acceptance/review/eval/rubric criteria |

A live E2 or E5 run now also leaves per-frame records behind, next to its checkpoints: one
`JudgeResponse` per JSON line in `data/<out-stem>.<variant>.responses.jsonl` for E2 (`P0a`,
`P0b`) and `data/<out-stem>.{hand,manip}.responses.jsonl` for E5, written by
`scripts/judge_responses_io.py` and read back with its `read_responses` (which dedupes on
`(frame_id, prompt_variant)`). Gitignored by default; a run that backs a card claim gets a
per-file negation. Forward-only -- the committed aggregates predate this and have no jsonl.
`docs/DECISIONS.md` D069.

## The next action

**The Qwen3-VL judge is deployed and fully smoke-tested live end to end, image + logprobs
included — real correct output.** `cloud/modal_qwen3vl.py` is live on Modal
(`vernier-qwen3vl-judge`, scale-to-zero, `min_containers=0`; a cold start after idle takes
~5 minutes, observed live). The evaluation parquet (`egocentric_10k.parquet`, real HF repo is
**three separate parquet files**, one per corpus arm — `egocentric_10k.parquet`→`E10k-ego`,
`ego4d.parquet`→`E10k-ego4d`, `epic_kitchens.parquet`→`E10k-epic`, not one file filtered by a
column, confirmed via `HfApi().list_repo_files`) was downloaded locally
(`hf_hub_download`, ~1.79GB, ~25 min at this session's network speed) after two remote
single-row `hf://` reads stalled 9+ minutes each and were killed — a real fix for real slowness,
recorded here so it isn't rediscovered: **always `hf_hub_download` the file locally before
reading individual rows/images out of it; never stream single-row reads over `hf://`.**

A real `Qwen3VLJudge.judge_frame` call against a real frame (`cc94d1f8-749a-400f-82e1-
de35158cfc18`) returned `status: "ok"`, `hands_visible: 2`, `manipulation: true`, both
**exactly matching that frame's real published `hand_count`/`active_labor` labels**, latency
~950ms, cost ~$0.0002/call (Modal L4 warm-container attribution). Two real bugs were caught
only by this live call and are fixed, tested, and committed:

- **`docs/DECISIONS.md` D043 — the parsing contract was built on a false premise.** D014/F1
  claimed the shipped prompts specify a JSON response schema; they don't — every prompt
  variant (P0-P7) asks for a bare `0`/`1`/`2` or `yes`/`no` (P7 adds a comma + confidence),
  verified against a fresh live download of Build AI's own prompt files. The real model
  answered correctly and vernier's own parser called it `"unparseable"` until this was fixed.
  `judges/base.py`'s three parsing functions are rewritten around the real format; all of that
  file's tests (and `test_judges_qwen3vl.py`'s mocked raw responses) rewritten to match.
- `Qwen3VLJudge._client`'s `base_url` was missing vLLM's `/v1` path segment — every real call
  404ed until fixed (own regression test added).

Two earlier deploy-blocking bugs from this session's prior pass are also fixed and committed
(`8b6fd49`): Modal's own proxy auth (`unauthenticated=True` — the plain `openai` client can't
supply Modal-workspace auth headers) and a KV-cache OOM (`--max-model-len 8192` — the model's
262144 default demands 36GB, the L4 has ~7GB free after weights).

- `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` — moot now. Per D042 the panel is Qwen3-VL only;
  `judges/gemini.py`/`judges/claude.py` are deleted, not stubbed.
- `HF_TOKEN` — still required for `S10k-U`/`S10k-S` (the sampling-design sensitivity arm, which
  needs the contact-gated `Egocentric-10K` corpus for its raw factory/worker metadata) and for
  Result 2's transfer probe at scale. **Not required** for `E10k-ego`/`E10k-ego4d`/`E10k-epic`/
  `P2k`/`G200-*`/`R100` — the evaluation release itself is `gated: False`, verified live via
  `HfApi().dataset_info(...)`.

**The E10k-* evaluation-parquet adapter is now real and fully wired, closing the loop end to
end with zero manual glue.** `sampling/draw.py`'s `_candidate_frames` (real per-sample HF
parquet download + `FrameRef` pool, including real decoded `width`/`height` via a new Pillow
dependency, since the parquet carries neither) and the new `sampling/draw.image_bytes_for`
(real, process-cached `frame_id → JPEG bytes` lookup) are both committed and tested.
`Qwen3VLJudge._image_bytes_for` is now a one-line delegation to `image_bytes_for`, not a raise.
Verified live twice: `draw_sample("E10k-ego")` → a real frame → `judge.judge_frame()` → real
image bytes resolved automatically → real vLLM call → `status: "ok"`, and **the live judge's
answer matched Build AI's own published `hand_count`/`active_labor` label exactly on both
frames tried**. `S10k-U`/`S10k-S` still raise `NotImplementedError` — the raw, contact-gated
Egocentric-10K corpus is a different dataset whose real schema hasn't been inspected yet;
`_factory_worker_hours` is unwired for the same reason.

**`scripts/e2_replication.py` (H1/H1b) and `scripts/e5_prompt_sweep.py` (H3) are both real,
tested, and smoke-tested live** — the live judge harness with cost/latency accounting
`WAVES.md`'s Wave 2 section calls for is these two scripts plus the `JudgeResponse.cost_usd`/
`latency_ms` accounting already built into `qwen3vl.py`, not a separate third artifact. Real
runs at n=5/n=20/n=100 all completed with every response `status: "ok"` (300/300 real calls
across the three E2 runs). At **n=100** (the largest run so far, `data/e2_n100.json`,
gitignored): per-frame agreement against Build AI's own published labels was 90% (hand count
exact) / 95% (active labor); real cost was ~$0.09 total, ~213s/198s latency for the P0a/P0b
passes; H1's `>=1 hand` figure landed within tolerance (1.42pp), `2 hands` and `active
manipulation` did not (5.66pp, 2.34pp) — genuinely informative now, but **still far short of
the pre-registered N=10,000 for a real confidence interval**, and P0a/P0b showed zero
disagreement at this n (H1b). IPR/PAR (`e5_prompt_sweep.py`) is a flagged, faithful-but-not-
pinned construction of 2604.16413's definition — the paper's exact formula isn't in hand, only
`SURVEY.md`'s excerpt of it.

**Superseded by D054/D055/D056**: the n=100/n=5 figures above were the largest runs at the time
they were written. Caio has since authorized, and this session has run, both scripts at the
full pre-registered scale (E2 N=10,000, E5 N=2,000/8 variant-passes) — real H1/H1b/H3 results
now exist and are folded into `MEASUREMENT_CARD.json` (see "Where this stands" above and
`DECISIONS.md` D056 for the exact figures). The n=100/n=5 numbers above are kept as a record of
what was known at the time, not as the current state.

**Wave 3 is done for real: 93 primary labels (balanced 33/30/30 across
`G200-ego`/`G200-ego4d`/`G200-epic`, D057's reduced target) and 60 retest labels (34
real-overlapping with primary, via `--retest-from-primary`, D058's fix for the original
4-overlap gap).** `scripts/judge_gold_sets.py` then real-judged all three `G200-*` sets (600
frames, `P0b`), and `scripts/wave4_analysis.py` computed the real intra-rater/H4/H5/PPI/H7
results -- all folded into the card, D059/D060. See "Where this stands" above for the actual
numbers.

**What's left is one named blocker** (Result 2). H2 was the other and is now measured and
closed as a real, failed hypothesis (D071 built the adapter, D072 ran it: design effect
1.25-1.66 across two arms and three tasks, against a pre-registered 2). Result 2 does not
reduce to the same engineering: the adapter removed one of D048's three reasons, and the
remaining two each stand alone -- no institutional EPIC-KITCHENS-100 email, and no
downstream-task labels in the release to probe against at all.

**UPDATE 2026-09-02 (`docs/DECISIONS.md` D054): the full-N run is authorized and in progress.**
Caio approved N=10,000. First attempt: **P0a completed** (10,000/10,000; H1 = `>=1 hand`
95.45% within ±2pp, `2 hands` 82.66% **outside**, `active manipulation` 91.28% within);
**P0b crashed at 2,800** on an uncaught transient 503 (`_call_qwen3vl` had no retry). Fixed:
retry/backoff in `_call_qwen3vl`, `--resume` in `e2_replication.py` (complete checkpoint →
reconstructed with no judge calls; partial → resumed), per-variant checkpoint+resume in
`e5_prompt_sweep.py`. Re-run harness: **`scripts/run_full_e2_e5.sh`** (idempotent, `--resume`
both steps) — **launch it detached in `tmux`** (`tmux new-session -d -s vernier_run "…"`); a
plain `&` / agent background shell gets reaped on parent exit (observed twice). D055 widened
the in-call retry budget to ~19 min after a second death, this one from a **Modal preemption**
(the L4 is preemptible) whose ~11-min cold-start outran D054's 126s budget. The deployed judge URL is now persisted in `.env` as `QWEN3VL_BASE_URL`
(recover with `python3 -m modal run cloud/modal_qwen3vl.py` — note: needs modal ≥1.5, i.e.
`python3 -m modal`, not the older `modal` on PATH). P0a's 3 supplementary per-published-label
agreement fields were lost in the crash and come back `null` with
`reconstructed_from_checkpoint: true` — a deliberate call (not a hypothesis input), see D054.

**`scripts/draw_all_samples.py` is new, real, and closes a gap that would otherwise have
silently blocked Wave 3: nothing previously ran the sample-drawing DAG end to end and persisted
it.** `sampling.membership.py`'s own docstring says membership is written to disk before any
judge or labelling happens; nothing had actually done that. Running it the first time
immediately surfaced a real, pre-existing bug (**`docs/DECISIONS.md` D045**):
`_load_parent_membership` passed a pre-built `<root>/<sample>.json` file path where
`load_membership` expects the root directory, so every real subset draw (`P2k`, `G200-*`,
`R100`) would have raised `MembershipNotFoundError` 100% of the time — hidden until now because
every existing test monkeypatches `load_membership` without checking its `path` argument.
Fixed, regression-tested, and verified live: all eight currently-unblocked samples now draw and
persist with the exact pre-registered counts (`E10k-ego`/`E10k-ego4d`/`E10k-epic` 10,000 each,
`P2k` 2,000, `G200-*` 200 each, `R100` 100) and zero duplicate `frame_id`s.

**`labels/tool.py`'s `_pending_frames` is now real too, and Wave 3 has no remaining engineering
blocker.** Reads the real, just-persisted membership (`G200-ego`/`G200-ego4d`/`G200-epic` for
the 600 primary labels, `R100` for the 100 blind retest) through a real, per-rater
`HumanLabelStore`. Verified live: `next_frame(pass_="primary", rater=...)` and
`next_frame(pass_="retest", rater=...)` both return a real frame with zero manual glue.

**`scripts/human_labels_cli.py` is new: the actual interactive tool Caio runs** (`make
human-labels RATER=caio [PASS=primary|retest]`) — shows each frame's real image (opens in the
OS's default viewer), prompts for both `RUBRIC.md` tasks plus edge-case tags, difficulty, and a
note, times the frame automatically, and writes via the real `HumanLabelStore`. Building it and
running one real integration check before calling it done immediately surfaced **`docs/
DECISIONS.md` D046**: `sampling.draw.image_bytes_for` was keyed by `frame.sample`, which broke
for every subset sample (`P2k`/`G200-*`/`R100` relabel `sample`, discarding which root `E10k-*`
arm a frame came from — `R100` unions three different root arms, so `frame.sample` alone can
never disambiguate). A real `G200-ego4d` frame from `next_frame()` raised `NotImplementedError`
before the fix — exactly the frames Wave 3 needs. Fixed: it now searches all three root arms by
`frame_id` (the only key unique across the whole release). Verified live end to end after the
fix: both `next_frame(pass_="primary", ...)` and `next_frame(pass_="retest", ...)` resolve to a
real, decodable image.

**The 600+100 human labels themselves are still entirely Caio's own work — nothing here does
that — but there is no more code standing between "start labelling" and actually doing it.**

**`docs/REVIEW.md` (independent, fresh-context review, dated 2026-09-01) caught a real, costly
design mistake in rung-1 distillation before it finished running — `docs/DECISIONS.md` D047.**
`scripts/generate_rung1_labels.py` was calling the live Qwen3-VL judge to generate rung-1
training labels; `docs/METHOD.md` E7 actually specifies training on `gemini-2.5-flash`'s own
labels (the judge behind the published number), which are not missing — they're the
`hand_count`/`active_labor` columns already shipped in the evaluation parquets, verified to
reproduce the published figures exactly (D040, D042). The flawed run was killed after ~31 real
minutes (~$0.40 spent) rather than the full ~$5/~5.8hr it would have cost for the wrong target.
**Fixed and re-run for real**: the corrected script reads the real stored labels directly —
zero live calls, ~1 second runtime, 29,400 real labels across all three corpora (extended
beyond `E10k-ego` alone per the review's own recommendation, since it's free either way). The
live-calling mechanism wasn't discarded — repurposed into `scripts/generate_qwen_comparison_labels.py`
as the live comparison-judge arm for E4/E6, which is what it's actually for.

Also recorded from that same work: real smoke data shows naive client-side concurrency
(`scripts/judge_concurrency.py`) measurably **hurts** throughput on the current single-container
Modal deployment (sequential ~0.47 frames/sec vs. ~0.36 at 4 workers vs. ~0.26 at 8 workers) —
single-GPU contention on short bursts, not the hoped-for speedup. `--max-workers` defaults to 1
in the comparison-judge script for this reason; revisit only with real evidence at a run long
enough for Modal's autoscaling to actually add containers.

**`docs/REVIEW.md`'s cheap, pre-data recommendations are done — `docs/DECISIONS.md` D048.** R9
(Result 2 is now explicitly dropped everywhere, not "kill-gated"/"pending"), R5's disclosure
half (a new `RED-TEAM.md` A15 and `COVERAGE.md` row for the pretraining-contamination confound
on H5), and the full stale-prose sweep across 13 files (all still describing the pre-D042
three-judge design) are all committed. Two real factual bugs caught in the same pass:
`RUBRIC.md` had gloves attributed to the wrong prompt variant (P3, not P4); `RED-TEAM.md` had a
variant-count typo. `PRE-REGISTRATION.md` gained an `## Amendments` section (frozen text
untouched, appended-only, pointing at D042/D044/D047/D048). Also corrected: `METHOD.md` E8's
"calibration restricted to P7" was only ever true for Build AI's own closed-API measurement —
the self-hosted judge's real logprob confidence works under the published bare-value format
too, confirmed live.

**R7 and R10 are also done now** (`docs/DECISIONS.md` D049, D050): the rung-3 guarantee
mechanism is pinned (Learn-then-Test / conformal risk control, `distil/cascade.py`'s current
point-estimate threshold search left as-is with a docstring pointer — the real algorithm
rewrite is separate, real statistics work, not done here), and `make validate` now runs
`scripts/check_stale_prose.py`, a real drift lint for exactly the class of staleness D048 found
by hand. Running it live caught two more real hits this session's own D048/D049 prose had just
introduced, fixed by rewording, not by adding exemptions.

**R2 was attempted and is blocked (`docs/DECISIONS.md` D051) — a real, third access wall found
this session, not a hypothetical one.** `facebook/dinov3-vits16-pretrain-lvd1689m` (D034's
pinned backbone) is gated, and this account is not authorized for it — a real `hf_hub_download`
returns `GatedRepoError`, the same pattern as `S10k-U`/`S10k-S` (D044) and now a *third* gated
resource this session found blocked only by actually trying to download it (`HfApi`'s own
metadata said "not gated" for this exact repo; the real download disagreed). `torch`/
`transformers` are added to the `probes` extra regardless — the real, already-decided
dependency, not a new one. Unofficial third-party mirrors of the same weights exist and aren't
gated, but are **not used** without a real checksum verification against the official
release, which nothing here has done. **Worth surfacing to Caio as a pattern, not three
separate one-offs**: this HF account's gated-content access appears narrower than its
metadata-read access across at least three unrelated resources now.

**R4 is done at smoke scale (`docs/DECISIONS.md` D052): 100% judge self-agreement**, 20 real
frames × 3 repeats, on both tasks. Real and reassuring, but `n=20` cannot rule out rare
disagreement — re-run against the real 600 gold frames once Wave 3 exists, for the actual R4
result this is a preliminary version of.

**The real gap D052 found is now fixed (`docs/DECISIONS.md` D053): `temperature=0.0`/`seed=777`
are pinned on every real judge call.** `judges/qwen3vl.py` previously left sampling entirely
at the server's own defaults, unpinned — the one place this project's own "seed 777,
everywhere" convention (`REPRODUCTION.md`) didn't reach. Verified live: vLLM accepts both, and
a real post-fix call returned the same correct answer for a frame checked earlier this session,
now with `confidence.value == 1.0`. **D052's 100%-agreement result predates this fix** and
measured the previously-unpinned configuration — real and valid on its own terms, just not the
same setup real calls run under now.

**Still open from `docs/REVIEW.md`, genuinely requiring either real spend, real time, or
Caio's own action — tracked in D048/D049/D051/D052, not lost:** R3 (a second `R100` rater,
~35 min of someone else's time), R6 (a pre-data gold-size amendment for H5 — **time-critical,
must land before the first label is written**), R8 (authorize the full-N E2/E5 run — the same
"explicit decision from Caio" boundary this file has held throughout), and R5's own live
contamination probe.

Note for whoever runs this next: `scripts/draw_all_samples.py`'s `ego4d.parquet`/
`epic_kitchens.parquet` downloads twice hung indefinitely at a fixed byte count via HF's
default Xet transfer backend (confirmed reproducible, not a one-off) — set
`HF_HUB_DISABLE_XET=1` before running it (or any fresh `hf_hub_download` of a large file in
this environment) to force the plain HTTP path, which completed both downloads reliably
(with its own automatic resume-on-timeout, observed working).

Still unwired, but as of D065, no longer unverified:

1. **`HF_TOKEN` now DOES unblock the raw `Egocentric-10K`/`Egocentric-100K` corpora.** Caio
   accepted the gated-access terms; live-confirmed (`dataset_info()` succeeds, real
   `intrinsics.json` bytes actually downloaded from both repos). The earlier 403
   `GatedRepoError` this file used to report here is resolved, not a current blocker.
2. **The raw corpus is real WebDataset video shards, inspected live for the first time
   (D065)**: one real shard = 2 clips (`.mp4`, h265, 1920x1080, 30fps, ~7 min each) + 2
   companion per-clip `.json` files (`worker_id`/`factory_id`/`duration_sec`/`fps`, no per-frame
   `timestamp_s`/`frame_index`) + one per-worker `intrinsics.json` (camera calibration only).
   **Confirmed: video, not stills** — a real adapter needs real video decoding (extract a frame
   at a chosen timestamp from an h265 MP4), a materially bigger and structurally different task
   than `_frames_from_eval_parquet`'s single `pq.read_table` call, and a genuinely new kind of
   dependency this project doesn't have yet (no `av`/`decord`/`ffmpeg`-wrapper in
   `pyproject.toml`). One shard out of 19,495 — D065's own "Reverses if" names what would
   overturn this.

`_factory_worker_hours` is the same gap. `WAVES.md`'s "Egocentric-10K streaming draw for the
sampling-design arm" line item is this — scope it as its own investigation once a broader,
multi-shard spike confirms D065's shape holds generally, not as an extension of the E10k-*
adapter's pattern (parquet vs. video-shard decoding are different problems).

## Open questions

- **Item 5 of `SURVEY.md`'s "must be closed" list is the one still open**: the "16.8 pp
  prevalence spread" and "19%→54% neutral" figures remain unsourced after an extensive Wave S
  search. Drop them entirely if nothing surfaces by publication. All five other items closed —
  see `SURVEY.md`'s verification pass and `DECISIONS.md` D030.
- **EPIC-KITCHENS-100 registration requires an institutional email**, which an unaffiliated
  researcher does not have. A Result-2 risk, not a Result-1 blocker.
- **Ego4D frame redistribution is licence-restricted** to research/academic-publication
  contexts (Wave S, `SURVEY.md`). This is the reason `ETHICS.md` §4 excludes Ego4D's 30
  human-labelled frames from the atlas D073 ships, and EPIC-KITCHENS-100's 30 with it.
- ~~**Whether the evaluation parquets contain the frames the published labels refer to**
  (D016)~~ — **closed, real, run at scale.** `scripts/check_eval_parquets.py` run for real
  against all three evaluation parquets and the real membership `scripts/draw_all_samples.py`
  wrote: `E10k-ego` (10,000), `E10k-ego4d` (10,000), `E10k-epic` (10,000), and `G200-ego`
  (200) all report "all N frames present and decodable" — real assertion, not a manual step,
  matching `WAVES.md`'s Wave 2 acceptance criterion exactly.

Settled since the last update: there is no public `builddotai/Egocentric-1M` (404), so no
public release could make the MPJPE guarantee checkable; and Ego4D/EPIC access is off Result
1's critical path because their frames ship inside the evaluation release.

## What must not drift

- The rater never sees judge output. Enforced in `labels`, not by discipline.
- No agreement statistic is computed before all 600 primary labels exist.
- Intra-rater agreement on `R100` below 0.70 defers the audit and makes the rubric the
  deliverable.
- AC1 is primary, κ is secondary, PPI is the headline estimator — all decided before data.
- Intervals cluster over `worker_id` wherever a grouping variable exists, and say so plainly
  where it does not.
- `make privacy-gate` passes before any commit.
