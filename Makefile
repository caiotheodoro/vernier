# vernier -- targets are the table of contents. Most of these don't run yet: this repository
# is documentation-only until `make survey` has an answer. `test`, `typecheck`, `fixtures` and
# `validate` are Wave 0 -- the interface freeze -- and do run.
.PHONY: help effective-n survey sample replicate judge human-labels agreement prompt-sweep \
        domain-bias distil calibrate estimate probe card validate privacy-gate \
        test typecheck fixtures

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

effective-n:   ## H8: participant-count precision disparity per corpus (not ICC-adjusted effective N, D031). No experiment.
survey:        ## docs/SURVEY.md -- novelty gate. Nothing downstream runs until this passes.
sample:        ## Draw the stratified frame sample fixed in docs/PRE-REGISTRATION.md.
replicate:     ## Reproduce Build AI's own protocol: 10k frames, gemini-2.5-flash, their prompt.
judge:         ## Run the full judge panel over the sample.
human-labels:  ## Collect human gold against docs/RUBRIC.md. Never automated.
agreement:     ## Judge-vs-human and judge-vs-judge agreement, with intervals.
prompt-sweep:  ## Prompt-sensitivity sweep over the paraphrases fixed in pre-registration.
domain-bias:   ## The decisive experiment: same panel, matched Ego4D / EPIC-KITCHENS samples.
distil:        ## Train the open instrument (linear probe, then Qwen3-VL LoRA).
calibrate:     ## Calibration and severity-weighted reporting for the instrument.
probe:         ## Result 2: transfer probe. Kill-gated -- see docs/METHOD.md.
estimate:      ## PPI prevalence: naive, rectified, interval, design effect.
card:          ## Emit the measurement card, including "what could not be checked".

test:          ## Wave 0: run the pytest suite (contract records + fixture generator).
	python3 -m pytest

typecheck:     ## Wave 0: mypy --strict over src/vernier, tests and scripts.
	python3 -m mypy src/vernier tests scripts

fixtures:      ## Wave 0: regenerate tests/fixtures/{valid,malformed}/*.json from tests/fixtures.py.
	python3 scripts/generate_fixtures.py

validate: privacy-gate test typecheck fixtures  ## All gates: structure, no placeholders, internal consistency, privacy.

privacy-gate:  ## Fail loudly if anything under docs/private/ is stageable.
	@if git add -A --dry-run 2>/dev/null | grep -q 'docs/private'; then \
		echo "REFUSING: docs/private/ is stageable. Fix .gitignore before committing."; exit 1; \
	else echo "privacy-gate: docs/private/ is not stageable."; fi
