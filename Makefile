# vernier -- targets are the table of contents. Nothing here runs yet:
# this repository is documentation-only until `make survey` has an answer.
.PHONY: help effective-n survey sample replicate judge human-labels agreement prompt-sweep \
        domain-bias distil calibrate estimate probe card validate privacy-gate

help:
	@grep -E '^[a-z-]+:.*?## .*$$' $(MAKEFILE_LIST) | sed 's/:.*## /\t/'

effective-n:   ## H8: effective N per corpus from public participant counts. No experiment.
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
validate:      ## All gates: structure, no placeholders, internal consistency, privacy.

privacy-gate:  ## Fail loudly if anything under docs/private/ is stageable.
	@if git add -A --dry-run 2>/dev/null | grep -q 'docs/private'; then \
		echo "REFUSING: docs/private/ is stageable. Fix .gitignore before committing."; exit 1; \
	else echo "privacy-gate: docs/private/ is not stageable."; fi
