# Handoff

The resume point. A fresh session should be able to continue from this file without
re-deriving anything.

**Last updated: 2026-09-01, after Wave S, Wave 0, the P1 hygiene tier, Wave 1's full 18-unit
fan-out (all committed, all independently reviewed), real Wave 2 judge-SDK wiring, and a real,
committed `MEASUREMENT_CARD.json` — `verdict=NOT_VERIFIED`, honestly, naming every unmet claim.**

## Where this stands

**A real `MeasurementCard` exists and is committed: `MEASUREMENT_CARD.json`, `verdict=
NOT_VERIFIED`.** Regenerate with `make card`. It carries exactly one real claim (H8 --
participant-count precision disparity, pre-registered as computable from public counts alone,
no judge call or human label needed: a genuine 58.2x spread across the three corpora) and names
every other pre-registered hypothesis (H1, H1b, H2, H3, H4, H5, H6, H7) plus Result 2 in
`what_could_not_be_checked`, each with a specific `"BLOCKER:"` reason (which credential is
missing, or that the 600 human labels don't exist yet) -- so `_derive_verdict` (D038) returns
`NOT_VERIFIED` because a real blocker is present, not vacuously from having nothing to claim.
`verify_and_exit` returns nonzero, for real, via `make card`. This is the actual deliverable
`card/__init__.py`'s own docstring names as the point of the whole exercise ("an audit that
always exits zero is decoration") -- not a placeholder, and not to be conflated with either the
H8 computation itself (a real result) or the D016 live-data cross-check in the next paragraph
(a data-integrity sanity check, never presented as a hypothesis result).

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
| Decisions | `DECISIONS.md`, D001–D042 |
| Private | `docs/private/`, gitignored: outreach, country brief, email draft, self-audit log |
| Interface | `src/vernier/` — pydantic models (`models.py`) + all 18 Wave-1 units **implemented, reviewed, committed** |
| Infra | CI (`.github/workflows/ci.yml`), `make install-hooks`, `scripts/check_eval_parquets.py`, `scripts/power_simulation.py`, `scripts/rubric_pilot_check.py`, `sampling/revisions.py`, `cloud/modal_qwen3vl.py` (deployed, smoke-tested live for text) |
| Waves | `WAVES.md` — the fan-out → independent-review paradigm and every wave's acceptance/review/eval/rubric criteria |

## The next action

**The Qwen3-VL judge server is deployed and smoke-tested for real, text-only path only.**
`cloud/modal_qwen3vl.py` is live on Modal (`vernier-qwen3vl-judge`, scale-to-zero,
`min_containers=0`), health-checks pass, and a real text-only chat completion against the
deployed endpoint (`https://dev-caiotheodoro--vernier-qwen3vl-judge-server.us-east.modal.direct`)
returned a correct response (`"OK"`) with real usage stats. Two real deploy-blocking bugs were
caught only by actually running it and are fixed and committed (`8b6fd49`): Modal's own proxy
auth (`unauthenticated=True` now — the plain `openai` client can't supply Modal-workspace auth
headers) and a KV-cache OOM (`--max-model-len 8192` — the model's 262144 default demands 36GB,
the L4 has ~7GB free after weights).

**Not yet exercised: the real multimodal (image + logprobs) request path.** Fetching one real
frame's bytes from the evaluation parquet to test this stalled twice in this session (a
single-row `hf://` read via pyarrow ran 9+ minutes with no output, same slowness already noted
below re: `check_eval_parquets.py`) — killed both times, not a vernier code bug, an artifact of
streaming a single row out of a large remotely-hosted parquet without a local copy. The
multimodal request shape itself (`image_url` content block + `logprobs: true`) is independently
verified against the installed `openai` package's real response types and vLLM's own docs, but
has not been fired against the live server with a real image. **Next session should either
`hf_hub_download` the evaluation parquet locally first** (this project's own noted fix for the
same slowness, see below) **or otherwise get one real frame's bytes some other way**, then send
one real multimodal request to the deployed endpoint before trusting `judges/qwen3vl.py` end to
end.

- `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` — moot now. Per D042 the panel is Qwen3-VL only;
  `judges/gemini.py`/`judges/claude.py` are deleted, not stubbed.
- `HF_TOKEN` — still required for `S10k-U`/`S10k-S` (the sampling-design sensitivity arm, which
  needs the contact-gated `Egocentric-10K` corpus for its raw factory/worker metadata) and for
  Result 2's transfer probe at scale. **Not required** for `E10k-ego`/`E10k-ego4d`/`E10k-epic`/
  `P2k`/`G200-*`/`R100` — the evaluation release itself is `gated: False`, verified live via
  `HfApi().dataset_info(...)`.

What's left unwired: `sampling/draw.py`'s `_candidate_frames`/`_factory_worker_hours`, and
`judges/qwen3vl.py`'s `_image_bytes_for` (frame_id → real JPEG bytes — both need the same
evaluation-parquet adapter, so build it once, not twice). `_call_qwen3vl` itself is real,
tested, and now confirmed live for text; only the image path is unverified live. Follow
`WAVES.md`'s Wave 2 section (evaluation-parquet adapter, live judge harness with cost/latency
accounting, E2 replication runner, E5 prompt-sweep runner) and its own added safeguard: smoke-
test at small N before any full-scale judge run, since no dollar cap is pre-registered for judge-
panel spend (only Modal/distillation compute is, per D008). **Do not scale toward the
pre-registered sample sizes without a separate, explicit decision from Caio** — the approved
reframe plan scoped only "deploy, smoke-test, report real cost/latency," not a production run.

## Open questions

- **Item 5 of `SURVEY.md`'s "must be closed" list is the one still open**: the "16.8 pp
  prevalence spread" and "19%→54% neutral" figures remain unsourced after an extensive Wave S
  search. Drop them entirely if nothing surfaces by publication. All five other items closed —
  see `SURVEY.md`'s verification pass and `DECISIONS.md` D030.
- **EPIC-KITCHENS-100 registration requires an institutional email**, which an unaffiliated
  researcher does not have. A Result-2 risk, not a Result-1 blocker.
- **Ego4D frame redistribution is licence-restricted** to research/academic-publication
  contexts (Wave S, `SURVEY.md`); consistent with `ETHICS.md`'s existing no-republish policy,
  now with a concrete legal basis.
- **Whether the evaluation parquets contain the frames the published labels refer to** (D016)
  — partially answered, not closed: the real schema was verified live
  (`frame_id, image, source_dataset, hand_count, active_labor`, matching `UPSTREAM-FINDINGS.md`
  F9 exactly) and aggregating `hand_count`/`active_labor` reproduces every published headline
  figure exactly on all three parquets. What is NOT yet verified is per-frame decodability of
  every `image.bytes` value at scale — `scripts/check_eval_parquets.py` exists and is unit-
  tested against synthetic data (Phase 1) but has not yet been run against the real ~5.5GB
  files, since that is properly a Wave 2 "make sample" step, not something to do ad hoc outside
  the wave's own loop.

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
