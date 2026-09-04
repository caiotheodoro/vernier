"""H6, rung 1: real distillation, real cascade, real result (D061).

**Backbone substitution, disclosed, not silent**: `docs/DECISIONS.md` D034 pins the official
`facebook/dinov3-vits16-pretrain-lvd1689m`; D051 confirmed this account has no access (real
403 `GatedRepoError`, not a metadata artifact) and explicitly declined third-party re-uploads of
those same weights as an unverified substitution risk. This script uses
`facebook/dinov2-small` instead -- a *different*, official Meta checkpoint, verified live as
genuinely ungated (`gated=False` in its own Hub metadata AND a real successful download,
avoiding the exact metadata-vs-real-access gap D044/D051 both found for gated repos). This is a
real deviation from D034's pin, reported as one, not smuggled in as if DINOv2 had always been
the plan.

**Two real, separate datasets, per H6's own pre-registered split**:
- The probe trains on `gemini-2.5-flash` P0b labels (`data/rung1_stored_labels.json`, D047's
  real fix -- Build AI's own historical stored labels, not a live call), because H6's own
  fidelity diagnostic target is specifically "agreement with gemini-2.5-flash P0a" -- frozen
  pre-registered text, unrelated to which judge is in the current live panel (D042).
- The cascade's threshold is calibrated on, and its floor/coverage evaluated against, Wave 3's
  real human gold (D057/D058) -- H6's actual claim, never the judge's own labels.

Real, bounded run (laptop-runnable, per `linear_probe.py`'s own stated design goal): a real,
seeded sample of `_N_TRAIN` + `_N_FIDELITY_HOLDOUT` frames from the 29,400 stored labels (real
DINOv2 features extracted for each -- real network + compute time, not free, but small: a ViT-S
forward pass per frame), plus real DINOv2 features for all of Wave 3's 93 primary-labelled
frames, split in half for calibration vs. evaluation (`WAVES.md`'s own Wave 4 acceptance
criterion: the floor must be calibrated on data disjoint from what evaluates it).

**The fitted probe is a real, loadable artifact (`docs/DECISIONS.md` D064)**, not just the
metrics it produced: `probe.save(_PROBE_PATH)` persists it via `LinearProbe.save`/`.load`
(joblib). Loading it back is not the whole instrument by itself -- a caller also needs this
file's own `_BACKBONE` name, `_preprocess`'s exact steps, and the mean-pooling-over-patch-tokens
choice in `_extract_features`, none of which travel with the weights.
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL import Image

from vernier.distil.cascade import AbstentionCascade
from vernier.distil.linear_probe import LinearProbe, fidelity
from vernier.labels.store import HumanLabelStore
from vernier.models import FrameRef, HumanLabel, JudgeResponse
from vernier.sampling.draw import SampleName, draw_sample, image_bytes_for
from vernier.sampling.membership import load_membership

_SEED = 777
_N_TRAIN = 600
_N_FIDELITY_HOLDOUT = 150
_TARGET_FLOOR = 0.80
_TARGET_COVERAGE = 0.70
_BACKBONE = "facebook/dinov2-small"
_PROBE_PATH = Path("data/rung1_probe.joblib")

_STORED_LABELS_PATH = Path("data/rung1_stored_labels.json")
_FEATURES_CACHE_PATH = Path("data/dinov2_features.json")
_LABEL_STORE_ROOT = Path("data/labels")
_MEMBERSHIP_ROOT = Path("data/membership")
_RATER = "caio"

_E10K_SAMPLES: tuple[SampleName, ...] = ("E10k-ego", "E10k-ego4d", "E10k-epic")
_GOLD_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")


def _frame_by_id_from_e10k() -> dict[str, FrameRef]:
    by_id: dict[str, FrameRef] = {}
    for sample in _E10K_SAMPLES:
        for frame in draw_sample(sample):
            by_id[frame.frame_id] = frame
    return by_id


def _frame_by_id_from_gold() -> dict[str, FrameRef]:
    by_id: dict[str, FrameRef] = {}
    for sample in _GOLD_SAMPLES:
        for frame in load_membership(sample, _MEMBERSHIP_ROOT):
            by_id[frame.frame_id] = frame
    return by_id


def select_training_and_holdout_frame_ids(
    stored_labels: list[dict[str, Any]],
    frame_by_id: dict[str, FrameRef],
    *,
    n_train: int,
    n_holdout: int,
    seed: int = _SEED,
) -> tuple[list[str], list[str]]:
    """Real, seeded, deterministic sample of stored-label frame_ids that actually resolve to a
    real `FrameRef` (some stored labels may predate a membership redraw; skipped, not padded).
    Returns `(train_ids, holdout_ids)`, disjoint by construction (one shuffle, sliced once)."""
    candidates = [rec["frame_id"] for rec in stored_labels if rec["frame_id"] in frame_by_id]
    rng = random.Random(seed)
    rng.shuffle(candidates)
    total = n_train + n_holdout
    if len(candidates) < total:
        raise ValueError(f"only {len(candidates)} resolvable stored-label frames, need {total}")
    return candidates[:n_train], candidates[n_train : n_train + n_holdout]


def split_gold_for_calibration_and_eval(
    gold: list[HumanLabel], *, seed: int = _SEED
) -> tuple[list[HumanLabel], list[HumanLabel]]:
    """Real, seeded, disjoint 50/50 split -- `WAVES.md`'s Wave 4 acceptance criterion: the
    cascade's threshold must be calibrated on data disjoint from what evaluates it."""
    shuffled = list(gold)
    random.Random(seed).shuffle(shuffled)
    midpoint = len(shuffled) // 2
    return shuffled[:midpoint], shuffled[midpoint:]


# Real values read from facebook/dinov2-small's own preprocessor_config.json (live-fetched,
# not guessed) -- reproduced manually rather than via `transformers.AutoImageProcessor`, whose
# import chain pulls in `torchvision`, which this environment's Python cannot import
# (`ModuleNotFoundError: No module named '_lzma'` -- a real, environment-level build gap, not a
# missing pip package; rebuilding Python to fix it is out of scope for a feature-extraction
# script). `AutoModel` alone imports cleanly (verified live) since it never touches torchvision.
_RESIZE_SHORTEST_EDGE = 256
_CROP_SIZE = 224
_IMAGE_MEAN = (0.485, 0.456, 0.406)
_IMAGE_STD = (0.229, 0.224, 0.225)


def _preprocess(image: "Image.Image", torch_module: Any) -> Any:
    """Manual reproduction of `BitImageProcessor`'s real pipeline for this checkpoint: resize
    shortest edge to 256 (bicubic), center-crop to 224x224, rescale to [0,1], normalize by
    ImageNet mean/std. Returns a `(1, 3, 224, 224)` tensor, the same shape `AutoImageProcessor`
    would have produced."""
    w, h = image.size
    scale = _RESIZE_SHORTEST_EDGE / min(w, h)
    image = image.resize((round(w * scale), round(h * scale)), resample=3)  # 3 == PIL.Image.BICUBIC
    w, h = image.size
    left = (w - _CROP_SIZE) // 2
    top = (h - _CROP_SIZE) // 2
    image = image.crop((left, top, left + _CROP_SIZE, top + _CROP_SIZE))

    import numpy as np

    array = np.asarray(image, dtype=np.float32) / 255.0
    array = (array - np.array(_IMAGE_MEAN)) / np.array(_IMAGE_STD)
    tensor = torch_module.from_numpy(array).permute(2, 0, 1).unsqueeze(0).float()
    return tensor


def _extract_features(frame_ids: list[str], frame_by_id: dict[str, FrameRef]) -> dict[str, list[float]]:
    """Real DINOv2-small embeddings (mean-pooled patch tokens), one per `frame_id`, cached to
    `_FEATURES_CACHE_PATH` so a re-run resumes rather than re-extracting. Imports are local to
    this function -- real, already-declared `probes` extra dependencies (D051), but no reason
    to pay their import cost for callers that only use this module's pure sampling/splitting
    functions (tested without either)."""
    import io

    import torch
    from PIL import Image
    from transformers import AutoModel

    cache: dict[str, list[float]] = {}
    if _FEATURES_CACHE_PATH.is_file():
        cache = json.loads(_FEATURES_CACHE_PATH.read_text())

    pending = [fid for fid in frame_ids if fid not in cache]
    if pending:
        model = AutoModel.from_pretrained(_BACKBONE)
        model.eval()
        for i, frame_id in enumerate(pending, start=1):
            frame = frame_by_id[frame_id]
            image = Image.open(io.BytesIO(image_bytes_for(frame))).convert("RGB")
            inputs = _preprocess(image, torch)
            with torch.no_grad():
                output = model(pixel_values=inputs)
            embedding = output.last_hidden_state.mean(dim=1).squeeze(0).tolist()
            cache[frame_id] = embedding
            if i % 50 == 0 or i == len(pending):
                _FEATURES_CACHE_PATH.write_text(json.dumps(cache))
                print(f"[dinov2] {i}/{len(pending)} extracted", flush=True)

    return {fid: cache[fid] for fid in frame_ids}


def main() -> int:
    stored_labels = json.loads(_STORED_LABELS_PATH.read_text())
    e10k_frames = _frame_by_id_from_e10k()
    gold_frames = _frame_by_id_from_gold()

    train_ids, holdout_ids = select_training_and_holdout_frame_ids(
        stored_labels, e10k_frames, n_train=_N_TRAIN, n_holdout=_N_FIDELITY_HOLDOUT
    )
    labels_by_id = {rec["frame_id"]: rec for rec in stored_labels}

    all_ids = train_ids + holdout_ids
    features_by_id = _extract_features(all_ids, e10k_frames)

    train_features = [features_by_id[fid] for fid in train_ids]
    train_labels = [JudgeResponse.model_validate(labels_by_id[fid]) for fid in train_ids]
    probe = LinearProbe()
    probe.fit(train_features, train_labels)
    probe.save(_PROBE_PATH)

    holdout_features = [features_by_id[fid] for fid in holdout_ids]
    holdout_labels = [JudgeResponse.model_validate(labels_by_id[fid]) for fid in holdout_ids]
    fidelity_score = fidelity(probe, holdout_features, holdout_labels)

    primary_labels = HumanLabelStore(_LABEL_STORE_ROOT / _RATER).read_pass("primary")
    gold_ids = [label.frame_id for label in primary_labels if label.frame_id in gold_frames]
    gold_features_by_id = _extract_features(gold_ids, gold_frames)

    calibration_gold, eval_gold = split_gold_for_calibration_and_eval(
        [label for label in primary_labels if label.frame_id in gold_features_by_id]
    )

    cascade = AbstentionCascade(probe, lambda feats: probe.predict_proba(feats), target_floor=_TARGET_FLOOR)
    cascade._features_for = lambda frame_id: gold_features_by_id[frame_id]  # type: ignore[method-assign]

    output: dict[str, Any] = {
        "backbone": _BACKBONE,
        "probe_path": str(_PROBE_PATH),
        "n_train": len(train_ids),
        "n_fidelity_holdout": len(holdout_ids),
        "fidelity_vs_gemini_2_5_flash": fidelity_score,
        "n_calibration_gold": len(calibration_gold),
        "n_eval_gold": len(eval_gold),
        "target_floor": _TARGET_FLOOR,
        "target_coverage": _TARGET_COVERAGE,
    }
    try:
        cascade.calibrate_threshold(calibration_gold)
        coverage, agreement_floor = cascade.coverage_and_floor(eval_gold)
        output["coverage"] = coverage
        output["agreement_floor"] = agreement_floor
        output["floor_reached"] = True
        output["holds"] = agreement_floor >= _TARGET_FLOOR and coverage >= _TARGET_COVERAGE
    except ValueError as exc:
        output["floor_reached"] = False
        output["holds"] = False
        output["error"] = str(exc)

    out_path = Path("data/rung1_distillation.json")
    out_path.write_text(json.dumps(output, indent=2))
    print(json.dumps(output, indent=2))
    print(f"\nwrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
