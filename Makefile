# vernier -- targets are the table of contents. Most of these don't run yet: this repository
# is documentation-only until `make survey` has an answer. `test`, `typecheck`, `fixtures` and
# `validate` are Wave 0 -- the interface freeze -- and do run. The rest fail loudly (not
# silently) until the wave that implements them replaces the recipe -- see docs/HANDOFF.md.
.PHONY: help effective-n survey sample replicate judge human-labels agreement prompt-sweep check-stale-prose \
        domain-bias distil calibrate estimate probe card validate privacy-gate \
        test typecheck fixtures check-eval-parquets install-hooks

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
agreement:     ## Judge-vs-human and judge-vs-judge agreement, with intervals.
	$(NOT_YET)
prompt-sweep:  ## Prompt-sensitivity sweep (H3) over E10k-ego. Requires QWEN3VL_BASE_URL live.
	python3 scripts/e5_prompt_sweep.py
domain-bias:   ## The decisive experiment: same panel, matched Ego4D / EPIC-KITCHENS samples.
	$(NOT_YET)
distil:        ## Train the open instrument (linear probe, then Qwen3-VL LoRA).
	$(NOT_YET)
calibrate:     ## Calibration and severity-weighted reporting for the instrument.
	$(NOT_YET)
probe:         ## Result 2: transfer probe. Kill-gated -- see docs/METHOD.md.
	$(NOT_YET)
estimate:      ## PPI prevalence: naive, rectified, interval, design effect.
	$(NOT_YET)
card:          ## Emit the measurement card, including "what could not be checked".
	python3 scripts/emit_card.py

test:          ## Wave 0: run the pytest suite (contract records + fixture generator).
	python3 -m pytest

typecheck:     ## Wave 0: mypy --strict over src/vernier, tests, scripts and cloud.
	python3 -m mypy src/vernier tests scripts cloud

fixtures:      ## Wave 0: regenerate tests/fixtures/{valid,malformed}/*.json from tests/fixtures.py.
	python3 scripts/generate_fixtures.py

check-eval-parquets:  ## D016: verify evaluation parquets contain the frames the published labels refer to.
	python3 scripts/check_eval_parquets.py

check-stale-prose:  ## D050/REVIEW.md R10: fail if a retired design (e.g. the pre-D042 three-judge panel) is still described as current anywhere public.
	python3 scripts/check_stale_prose.py

validate: privacy-gate test typecheck fixtures check-stale-prose  ## All gates: structure, no placeholders, internal consistency, privacy, no stale design language.

privacy-gate:  ## Fail loudly if anything under docs/private/ is stageable.
	@if git add -A --dry-run 2>/dev/null | grep -q 'docs/private'; then \
		echo "REFUSING: docs/private/ is stageable. Fix .gitignore before committing."; exit 1; \
	else echo "privacy-gate: docs/private/ is not stageable."; fi

install-hooks: ## Wire the privacy-gate into git: .git/hooks/pre-commit -> scripts/pre-commit.
	@ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
	@echo "installed: .git/hooks/pre-commit -> scripts/pre-commit"
