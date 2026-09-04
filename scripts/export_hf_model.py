"""Build the Hugging Face model release, `caiotheodoro/vernier-rung1-probe`, under `hf/model/`:
the fitted rung-1 probe (`data/rung1_probe.joblib`, D064), the result it produced
(`data/rung1_distillation.json`, D061/D063), and a card whose every number is read from that
result file -- `AGENTS.md` rule 2 applies to the model card too.

This is a negative result shipped as one. The card says so in its first line.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DATA = _REPO_ROOT / "data"
_REPO_URL = "https://github.com/caiotheodoro/vernier"
_DATASET_URL = "https://huggingface.co/datasets/caiotheodoro/vernier"


def _readme(r: dict[str, Any]) -> str:
    return f"""---
license: apache-2.0
library_name: sklearn
pipeline_tag: image-classification
base_model: {r["backbone"]}
tags:
  - egocentric
  - hand-detection
  - distillation
  - negative-result
  - vernier
datasets:
  - caiotheodoro/vernier
  - builddotai/Egocentric-10K-Evaluation
---

# vernier rung-1 probe

**Not an instrument yet.** A logistic-regression probe on frozen `{r["backbone"]}` features,
trained to reproduce `gemini-2.5-flash`'s hand-count judgements on egocentric factory frames,
wrapped in an abstention cascade calibrated on human gold. It does not clear its
pre-registered bar, and this card exists so the failure is inspectable rather than absent.

| | value | pre-registered target | met |
|---|---:|---:|---|
| teacher fidelity vs `gemini-2.5-flash` (n = {r["n_fidelity_holdout"]} held-out) | {r["fidelity_vs_gemini_2_5_flash"]:.3f} | ≥ 0.90 | no |
| agreement floor, 95% Wilson lower bound (n = {r["n_calibration_gold"]} calibration gold) | unreachable | ≥ {r["target_floor"]:.2f} | no |
| coverage at that floor | — | ≥ {r["target_coverage"]:.2f} | no |

`floor_reached = {str(r["floor_reached"]).lower()}`, `holds = {str(r["holds"]).lower()}`. The cascade's own
message: *{r["error"]}*

## What it is

- Backbone: `{r["backbone"]}` -- a disclosed substitute for the pre-registered
  `facebook/dinov3-vits16-pretrain-lvd1689m`, which is gated for this account
  (`docs/DECISIONS.md` D051/D061 in the repo).
- Features: mean-pooled patch tokens from the last hidden state.
- Preprocessing, reproduced by hand so `torchvision` is not a dependency: resize shortest
  edge to 256 (bicubic), center-crop 224×224, scale to [0, 1], normalise by ImageNet
  mean/std.
- Head: `sklearn.linear_model.LogisticRegression`, trained on n = {r["n_train"]} frames labelled
  by Build AI's own stored `gemini-2.5-flash` `P0b` output (the judge is the target on purpose:
  an instrument that improved on the thing it measures would stop measuring it).
- Cascade: abstain when `predict_proba` max is below a threshold chosen so the Wilson 95%
  lower bound on accuracy against held-out human gold clears the floor. On this data no
  threshold does.

## Load

```python
from vernier.distil.linear_probe import LinearProbe  # pip install git+{_REPO_URL}
probe = LinearProbe.load("rung1_probe.joblib")
```

Feature extraction (`_preprocess`, `_extract_features`) lives in the repo's
`scripts/distill_rung1.py`; the weights alone are not the instrument.

## Why publish a model that fails

The dataset release and the measurement card claim this artifact exists and reports these
numbers. A loadable probe with a stated failure is checkable; a missing one is not.
Human gold here is n = {r["n_calibration_gold"] + r["n_eval_gold"]} (calibration {r["n_calibration_gold"]}, evaluation
{r["n_eval_gold"]}); a larger gold set, the pre-registered backbone, or the rung-2 LoRA could move this
either way. None of that has been run.

Data: [{_DATASET_URL}]({_DATASET_URL}). Code and decision log: [{_REPO_URL}]({_REPO_URL}).

## License

Apache-2.0.
"""


def export(out_dir: Path) -> None:
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    result = json.loads((_DATA / "rung1_distillation.json").read_text())
    shutil.copy(_DATA / "rung1_probe.joblib", out_dir / "rung1_probe.joblib")
    shutil.copy(_DATA / "rung1_distillation.json", out_dir / "rung1_distillation.json")
    (out_dir / "README.md").write_text(_readme(result))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", type=Path, default=_REPO_ROOT / "hf" / "model")
    args = parser.parse_args(argv)
    export(args.out)
    print(json.dumps({"out": str(args.out), "files": sorted(p.name for p in args.out.iterdir())}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
