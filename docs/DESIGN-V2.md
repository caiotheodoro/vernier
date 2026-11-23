# Design: vernier v2 follow-up study (second rater, registered margin estimand, expanded gold set, and vendor right of reply)

Status: **design, not a registration.** Written 2026-11-23 alongside paper v2 (`docs/DECISIONS.md` D091–D095). Nothing here is frozen, no new human labels have been collected, no paid API call has been made, no vendor outreach has been sent, and every choice marked **owner** is open. A v2 registration would live in `docs/PREREG-V2.md`, frozen at a signed git tag (and deposited outside GitHub) before the first new label is written.

## Why

The v1/v2 audit established three empirical findings — strongly asymmetric judge over-calling in both the vendor's stored `gemini-2.5-flash` labels and an open-weights judge (`Qwen3-VL-8B-Instruct-FP8`), real worker-level clustering on the raw corpus (`deff` 1.25–1.66, widening intervals 12–29\%), and unresolved comparative margins against EPIC-KITCHENS-100 — and left four items that cannot be closed from existing committed artifacts alone.

1. **Single human rater (the second-rater gate).** All 153 primary labels come from one person (the author, who also wrote `docs/RUBRIC.md` after reading Build AI's prompt), the blind re-label ran at a median separation of 2.4 hours rather than the pre-registered seven days (D076), 60 labels were added after initial results were public at three seconds per frame (D085), and the vendor's stored labels reverse direction on the EPIC-KITCHENS-100 active-manipulation cell (1 over-call vs. 2 under-calls). Until a second independent rater labels the gold set, there is no inter-rater agreement statistic and no basis to claim that VLM-derived corpus prevalences are systematically upward-biased (an "upper bound").
2. **The comparative margin estimand is exploratory.** `docs/PRE-REGISTRATION.md` registered H5 as a domain error-rate difference rather than the gold-corrected prevalence margin (`Egocentric-10K` minus `EPIC-KITCHENS-100`). Making the margin a confirmatory test requires pre-registering it before collecting additional gold frames.
3. **The comparative margin is underpowered — and clustering tightens the constraint.** Under iid PPI++ over the vendor's 9,800-frame stored-label arms, separating the active-manipulation margin ($-1.32$\,pp, 95\% CI $[-10.78, +8.14]$) from the published $+6.62$\,pp requires roughly 89 gold frames per arm — about 55 more than the 63 and 60 that exist. Post-hoc cluster sensitivity (`data/cluster_posthoc.json`, D092) shows that under Broska & Howes (2026) Cluster-Robust PPI++, worker clustering on Egocentric-10K and the 37-participant cluster cap on EPIC-KITCHENS-100 increase the required sample size further and impose an irreducible unlabelled variance floor on the EPIC arm.
4. **No vendor notification or right of reply.** Under D009, publishing before contacting Build AI was a pre-registered independence choice. Before a v2 study or archival publication, notifying Build AI gives them a right of reply and an opportunity to release a `frame_id`-to-`worker_id` (and EPIC/Ego4D participant-ID) mapping for `Egocentric-10K-Evaluation`, which is the only way to replace post-hoc cluster sensitivity bounds with exact Cluster-Robust PPI++.

## What stays

- `docs/RUBRIC.md` v1.2.0 (22 numbered rules across the two tasks) and the blind labelling tool (`make human-labels`, zero read path to judge outputs, `rules.py` rule-12 enforcement).
- The frozen membership pools (`data/membership/G200-ego.json`, `G200-epic.json`, `G200-ego4d.json`, 200 frames each, seed 777) and the vendor's stored `gemini-2.5-flash` labels over `E10k-*` (9,800 unlabelled frames per corpus).
- Primary agreement estimator: Gwet's AC1 with Cohen's $\kappa$ beside it.
- Primary prevalence estimator: PPI++ (or Cluster-Robust PPI++ per Broska & Howes 2026, arXiv:2610.09601, if cluster identifiers become available).
- Likeness and withdrawal policy (`docs/ETHICS.md` §4): any newly labelled Egocentric-10K frame remains outside the Space thumbnail atlas unless manually reviewed by eye.

## What changes in v2

### A. Second independent rater on all 153 existing frames

- **Who.** One independent rater (`R2`) who has not seen the author's (`R1`) labels, the judge outputs, the blog post, or the paper results. **Owner:** recruit `R2` (paid annotator or collaborating researcher; estimate ~60–90 minutes at 10–15 seconds per frame for 153 frames, plus ~20 minutes reading `docs/RUBRIC.md` v1.2.0).
- **Protocol.** `R2` labels all 153 already-labelled primary frames (63 `G200-ego`, 60 `G200-epic`, 30 `G200-ego4d`) in randomised order via `make human-labels RATER=<r2> PASS=primary`, with `R1` labels and judge predictions completely inaccessible.
- **Pre-registered gates.**
  - Report inter-rater Gwet's AC1 and Cohen's $\kappa$ (`R1` vs. `R2`) on ternary hand count, $\ge 1$ hand, and active manipulation, overall and per corpus, plus separately on the first 93 frames (10 s/frame median) vs. the D085 60-frame batch (3 s/frame median) to test whether the fast batch introduced rater noise.
  - Pre-register an inter-rater decidability bar (recommended: AC1 $\ge 0.70$ on both tasks; below 0.70 defers claims and returns to rubric revision).
  - Re-compute the error-direction table (`gemini-2.5-flash` and `Qwen3-VL`) separately against `R2` alone and against `R1`/`R2` consensus (plus adjudicated disagreements, blind to judge labels). Only if asymmetric over-calling persists against `R2` independently — and its corpus-level heterogeneity including EPIC-KITCHENS-100 is characterised — can an "upper bound" framing be evaluated.
  - Optional: a genuine $\ge 7$-day blind re-label on a 50-frame subset for `R2` (enforced by timestamp check in the CLI) to replace D076's 2.4-hour within-session check.

### B. Registering the comparative margin estimand

- **Primary confirmatory estimand.** The gold-corrected active-manipulation margin $\Delta_{\text{manip}} = \hat{\theta}_{\text{ego}} - \hat{\theta}_{\text{epic}}$ using Build AI's own stored `gemini-2.5-flash` labels as the model arm ($N = 9{,}800$ unlabelled frames per corpus) and consensus human gold (`R1` + `R2`, or `R2`-verified gold, decided before freeze).
- **Secondary estimand.** The gold-corrected $\ge 1$-hand margin $\Delta_{\ge 1\text{h}}$ on the same arms.
- **Decision rule (pre-registered).** Report the 95\% confidence interval for $\Delta_{\text{manip}}$ against both $0$ and the published margin ($+6.62$\,pp):
  - *Published margin excluded:* upper bound of the 95\% CI $< +6.62$\,pp.
  - *Null unresolved:* 95\% CI contains both $0$ and $+6.62$\,pp.
  - *Lead confirmed:* lower bound of the 95\% CI $> 0$.
- **Cluster-aware variance rule.** If Build AI releases worker/participant identifiers for `Egocentric-10K-Evaluation`, use closed-form Cluster-Robust PPI++ (Broska & Howes, 2026, arXiv:2610.09601) accounting for partially labelled clusters. If no identifiers are released, report the iid PPI++ interval as a lower bound on width alongside the pre-registered cluster-sensitivity bound from `scripts/cluster_posthoc.py`.

### C. Labelling the extra gold frames per arm

- **Sample size.** Under iid PPI++ over the vendor's 9,800-frame arms, excluding $+6.62$\,pp at the current point estimate ($-1.32$\,pp) requires $\approx 89$ gold frames per arm (`data/margin_exploratory.json`), i.e., **26 more on `G200-ego`** (63 $\to$ 89) and **29 more on `G200-epic`** (60 $\to$ 89) — **55 frames total**.
- **Cluster-adjusted buffer.** Under conservative direct $\sqrt{\text{deff}}$ inflation (`data/cluster_posthoc.json`, D092), the target rises to roughly **115 gold frames per arm** (+52 on `G200-ego`, +55 on `G200-epic`, **107 frames total**, still well within the 200-frame frozen `G200-*` pools). Under EPIC-KITCHENS-100's 37-participant cap, high within-participant ICC could raise the unlabelled variance floor enough that extra frames on `G200-epic` yield diminishing returns; `docs/PREREG-V2.md` should fix the exact target $n$ in advance (recommended: **120 per arm** on `G200-ego` and `G200-epic`, i.e., +57 and +60 new frames, dual-labelled by `R1` and `R2`, ~45–60 minutes per rater) with no optional stopping.
- **Frame selection.** Draw deterministically from the unlabelled remainder of the frozen `G200-ego` and `G200-epic` pools (seed 777, preserving the exact frozen order already in `data/membership/G200-*.json`). All new frames already have stored `gemini-2.5-flash` labels and live `Qwen3-VL` labels committed in `space/public/data/frames.json` and `data/gold_judged/`, so **zero additional GPU or API spend** is required.

### D. Vendor notification and right of reply

- **Timing.** Send Build AI the v2 preprint (`paper/vernier.pdf`), repository URL, dataset URL, and Space URL before submitting to a venue or publishing a v2 follow-up, offering a fixed reply window (**Owner:** e.g., 14 days).
- **Specific technical asks (framed constructively, no speculation on intent):**
  1. Confirm whether any factual statement about `Egocentric-10K-Evaluation` or `Egocentric-100K-Evaluation` is inaccurate.
  2. Consider publishing a `frame_id` $\to$ `(factory_id, worker_id)` mapping for `Egocentric-10K-Evaluation` (and participant IDs for the Ego4D and EPIC-KITCHENS-100 evaluation parquets) so exact Cluster-Robust PPI++ can be computed on the published sample.
  3. Confirm whether any of the 24 likeness-reviewed Space thumbnails require withdrawal via `scripts/export_space_thumbnails.py --exclude`.
- **Recording.** Log the date sent and any public response (or "no reply within window") in `docs/DECISIONS.md`; keep private correspondence details out of public files unless the vendor consents to publication.

## What the owner decides before freezing `docs/PREREG-V2.md`

1. Recruitment and compensation/collaboration terms for independent rater `R2`.
2. Final gold target per arm (`89` iid minimum vs. `120` cluster-buffered vs. full `200` per arm) and whether to include `G200-ego4d` beyond the existing 30 dual-labelled frames.
3. Whether `R1` and `R2` also run a $\ge 7$-day blind re-label on 50 frames to close D076.
4. Timing and exact wording of the Build AI notification email (`docs/private/`).
5. External timestamping of `docs/PREREG-V2.md` (signed git tag pushed to GitHub plus an OSF / Zenodo / archive deposit before labelling begins, closing D090's registration-clock gap).

## Order of work once decided

1. Draft and review `docs/PREREG-V2.md` with owner-written predictions and stopping rules.
2. Freeze with a signed git tag and external timestamp deposit.
3. Run `R2` blind over the 153 existing frames (+ new frames up to the registered $n$, dual-labelled by `R1` and `R2`).
4. Run the analysis pipeline once (`wave4_analysis.py`, `margin_analysis.py`, `cluster_posthoc.py`, or exact Cluster-Robust PPI++ if cluster IDs are supplied).
5. Notify Build AI, incorporate any factual correction or published reply, and release `paper-v3.0`.
