# vernier -- targets are the table of contents. `sample`, `human-labels`, `prompt-sweep`,
# `agreement`, `distil`, `card`, `test`, `typecheck`, `fixtures` and `validate` are real and run
# real code against real, collected data (docs/HANDOFF.md). `effective-n`, `survey`, `replicate`,
# `judge`, `domain-bias`, and `probe` are not wired to a target yet; they fail loudly (not
# silently) until the wave that implements them replaces the recipe -- see docs/HANDOFF.md.
# (There is deliberately no `estimate` target: PPI prevalence already runs, folded into
# `agreement` -- see that target's recipe. `docs/DECISIONS.md` D064 removed the standalone
# stub, since its own help text promised a design-effect column this repo's non-clustered PPI
# path (D039) cannot structurally supply, not just an unwired one.)
.PHONY: help effective-n survey sample replicate judge human-labels agreement prompt-sweep check-stale-prose hf-dataset hf-model space space-data lock \
        domain-bias distil calibrate probe card validate privacy-gate \
        test typecheck fixtures check-eval-parquets check-label-rules check-prose-figures margin install-hooks

NOT_YET = @echo "not yet implemented -- see docs/HANDOFF.md for which wave lands this" >&2 && exit 1
PASS ?= primary

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

effective-n:   ## H8: participant-count precision disparity per corpus (not ICC-adjusted effective N, D031). No experiment.
	$(NOT_YET)
survey:        ## docs/SURVEY.md -- novelty gate. Nothing downstream runs until this passes.
	$(NOT_YET)
sample:        ## Draw every sample in docs/PRE-REGISTRATION.md's dependency order and persist it.
	python3 scripts/draw_all_samples.py
# replicate/judge predate docs/DECISIONS.md D042's reframe (gemini-2.5-flash is deprecated;
# the panel is now the self-hosted Qwen3-VL judge alone) -- scripts/e2_replication.py is the
# real post-reframe equivalent (a comparison against Build AI's own published labels, not a
# replication) but doesn't share these targets' pre-reframe description, so it is run directly
# rather than wired here. Requires QWEN3VL_BASE_URL pointed at a live deployment.
replicate:     ## Reproduce Build AI's own protocol: 10k frames, gemini-2.5-flash, their prompt.
	$(NOT_YET)
judge:         ## Run the full judge panel over the sample.
	$(NOT_YET)
human-labels:  ## Collect human gold against docs/RUBRIC.md. Never automated. Usage: make human-labels RATER=caio [PASS=primary|retest]
ifndef RATER
	$(error RATER is required, e.g. make human-labels RATER=caio)
endif
	python3 scripts/human_labels_cli.py --rater "$(RATER)" --pass "$(PASS)"
agreement:     ## Judge-vs-human agreement (AC1/kappa, bootstrap CI), H4/H5, PPI prevalence, H7 calibration.
	python3 scripts/wave4_analysis.py
prompt-sweep:  ## Prompt-sensitivity sweep (H3) over E10k-ego. Requires QWEN3VL_BASE_URL live.
	python3 scripts/e5_prompt_sweep.py
domain-bias:   ## The decisive experiment: same panel, matched Ego4D / EPIC-KITCHENS samples.
	$(NOT_YET)
distil:        ## Train the rung-1 open instrument (DINOv2 features + linear probe) and calibrate its abstention cascade (D061).
	python3 scripts/distill_rung1.py
calibrate:     ## Folded into `make distil`: AbstentionCascade.calibrate_threshold runs there, not as a separate step.
	@echo "calibration is not a separate step -- scripts/distill_rung1.py calls AbstentionCascade.calibrate_threshold as part of 'make distil'. Run that instead." >&2
probe:         ## Result 2: transfer probe. Kill-gated -- see docs/METHOD.md.
	$(NOT_YET)
card:          ## Emit the measurement card, including "what could not be checked".
	python3 scripts/emit_card.py

space-thumbs:  ## Build the Space's thumbnail atlas from the cached eval parquet (D073). Rarely.
	python3 scripts/export_space_thumbnails.py

space-data:    ## Build the Space's precomputed JSON (space/public/data/) from committed data/.
	python3 scripts/export_space_data.py

space:         ## Build the static Space into space/dist/ (needs node; run space-data first).
	cd space && npm ci && npm run build

test:          ## Wave 0: run the pytest suite (contract records + fixture generator).
	python3 -m pytest

typecheck:     ## Wave 0: mypy --strict over src/vernier, tests, scripts and cloud.
	python3 -m mypy src/vernier tests scripts cloud

lock:          ## Re-resolve constraints.txt (universal, py3.11) -- a deliberate dependency bump, never a side effect. Verify with `make validate` after.
	uv pip compile pyproject.toml --all-extras --universal --python-version 3.11 -o constraints.txt

fixtures:      ## Wave 0: regenerate tests/fixtures/{valid,malformed}/*.json from tests/fixtures.py.
	python3 scripts/generate_fixtures.py

check-eval-parquets:  ## D016: verify evaluation parquets contain the frames the published labels refer to.
	python3 scripts/check_eval_parquets.py

check-corpus-manifest:  ## D071: reconcile the raw-corpus clip manifest against the published 2,153-worker/85-factory figures.
	python3 scripts/check_corpus_manifest.py

check-prose-figures: ## Every figure in prose still equals the file that produces it (AGENTS.md rule 2)
	python3 scripts/check_prose_figures.py

margin: ## EXPLORATORY (D079): gold-corrected margin between corpora, vs the published one
	python3 scripts/margin_analysis.py

check-label-rules: ## Report human labels breaking a machine-checkable RUBRIC.md rule (D078)
	python3 scripts/check_label_rules.py

check-stale-prose:  ## D050/REVIEW.md R10: fail if a retired design (e.g. the pre-D042 multi-judge panel) is still described as current anywhere public.
	python3 scripts/check_stale_prose.py

hf-dataset:    ## Build the Hugging Face dataset release under hf/dataset/ from committed data/ (no images).
	python3 scripts/export_hf_dataset.py

hf-model:      ## Build the Hugging Face model release (rung-1 probe + card) under hf/model/.
	python3 scripts/export_hf_model.py

validate: privacy-gate test typecheck fixtures check-stale-prose check-prose-figures  ## All gates: structure, no placeholders, internal consistency, privacy, no stale design language.

privacy-gate:  ## Fail loudly if anything under docs/private/ is stageable.
	@if git add -A --dry-run 2>/dev/null | grep -q 'docs/private'; then \
		echo "REFUSING: docs/private/ is stageable. Fix .gitignore before committing."; exit 1; \
	else echo "privacy-gate: docs/private/ is not stageable."; fi

install-hooks: ## Wire the privacy-gate into git: .git/hooks/pre-commit -> scripts/pre-commit.
	@ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
	@echo "installed: .git/hooks/pre-commit -> scripts/pre-commit"
