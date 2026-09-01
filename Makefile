# vernier -- targets are the table of contents. Most of these don't run yet: this repository
# is documentation-only until `make survey` has an answer. `test`, `typecheck`, `fixtures` and
# `validate` are Wave 0 -- the interface freeze -- and do run. The rest fail loudly (not
# silently) until the wave that implements them replaces the recipe -- see docs/HANDOFF.md.
.PHONY: help effective-n survey sample replicate judge human-labels agreement prompt-sweep \
        domain-bias distil calibrate estimate probe card validate privacy-gate \
        test typecheck fixtures check-eval-parquets install-hooks

NOT_YET = @echo "not yet implemented -- see docs/HANDOFF.md for which wave lands this" >&2 && exit 1

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

effective-n:   ## H8: participant-count precision disparity per corpus (not ICC-adjusted effective N, D031). No experiment.
	$(NOT_YET)
survey:        ## docs/SURVEY.md -- novelty gate. Nothing downstream runs until this passes.
	$(NOT_YET)
sample:        ## Draw the stratified frame sample fixed in docs/PRE-REGISTRATION.md.
	$(NOT_YET)
replicate:     ## Reproduce Build AI's own protocol: 10k frames, gemini-2.5-flash, their prompt.
	$(NOT_YET)
judge:         ## Run the full judge panel over the sample.
	$(NOT_YET)
human-labels:  ## Collect human gold against docs/RUBRIC.md. Never automated.
	$(NOT_YET)
agreement:     ## Judge-vs-human and judge-vs-judge agreement, with intervals.
	$(NOT_YET)
prompt-sweep:  ## Prompt-sensitivity sweep over the paraphrases fixed in pre-registration.
	$(NOT_YET)
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
	$(NOT_YET)

test:          ## Wave 0: run the pytest suite (contract records + fixture generator).
	python3 -m pytest

typecheck:     ## Wave 0: mypy --strict over src/vernier, tests and scripts.
	python3 -m mypy src/vernier tests scripts

fixtures:      ## Wave 0: regenerate tests/fixtures/{valid,malformed}/*.json from tests/fixtures.py.
	python3 scripts/generate_fixtures.py

check-eval-parquets:  ## D016: verify evaluation parquets contain the frames the published labels refer to.
	python3 scripts/check_eval_parquets.py

validate: privacy-gate test typecheck fixtures  ## All gates: structure, no placeholders, internal consistency, privacy.

privacy-gate:  ## Fail loudly if anything under docs/private/ is stageable.
	@if git add -A --dry-run 2>/dev/null | grep -q 'docs/private'; then \
		echo "REFUSING: docs/private/ is stageable. Fix .gitignore before committing."; exit 1; \
	else echo "privacy-gate: docs/private/ is not stageable."; fi

install-hooks: ## Wire the privacy-gate into git: .git/hooks/pre-commit -> scripts/pre-commit.
	@ln -sf ../../scripts/pre-commit .git/hooks/pre-commit
	@echo "installed: .git/hooks/pre-commit -> scripts/pre-commit"
