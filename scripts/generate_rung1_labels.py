"""Generate rung-1 distillation training labels (`docs/METHOD.md` E7) -- corrected per
`docs/review.md` R1 and `docs/DECISIONS.md` D047.

Rung 1: "linear probe on frozen features, trained on `gemini-2.5-flash` `P0a` labels over
`E10k-ego \\ G200-ego` ... evaluated against human gold on `G200-ego`." The training teacher is
Build AI's own real judge, and its labels are ALREADY STORED in the evaluation parquets
(`docs/UPSTREAM-FINDINGS.md` F9: `hand_count`/`active_labor` per frame), verified live to
reproduce the published headline figures to two decimal places on all three corpora
(`docs/DECISIONS.md` D040, D042). Reading them costs nothing and calls no live judge.

An earlier version of this script called the live Qwen3-VL judge instead, real spend
(~$0.40, ~31 minutes, caught and stopped mid-run) toward the wrong target: that trains a probe
to imitate Qwen3-VL, not the judge the published number is actually about -- self-distillation,
adding nothing, exactly as `docs/review.md` R1 identifies. See D047 for the full record.

Per R1, this covers all three evaluation arms (not just `E10k-ego`), each minus its own
`G200-*` eval-holdout set -- ~29,400 frames total, zero judge spend, making the training pool
cross-domain by construction rather than `E10k-ego`-only.

Output shape matches `judges/qwen3vl.py`'s own `JudgeResponse` records so
`distil/linear_probe.py` consumes either source unchanged: `judge="gemini-2.5-flash"` (the real
origin), `prompt_variant="P0b"` (flagged: F2 says which P0 variant produced the published
figures is not recoverable from the artifacts alone -- P0b is chosen to match `RUBRIC.md`'s own
convention of labelling against the shipped, pinned-revision file rather than the card prose,
not because it is independently confirmed), `confidence=none` (no confidence signal exists for
a stored label), `latency_ms=0`/`cost_usd=0.0` (both real: no live call was made).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal, cast

from pydantic import TypeAdapter

from published_labels import published_labels_for_sample

from vernier.models import Confidence, JudgeResponse
from vernier.sampling.draw import SampleName
from vernier.sampling.membership import load_membership

_MEMBERSHIP_ROOT = Path("data/membership")  # matches sampling/draw.py's own root; re-declared
# per D033's no-shared-file-edits convention, same as every other script this session.

# Each training arm, minus its own reserved evaluation subset -- by construction, not
# convention, the same train/eval-leak shape D031 fixed elsewhere in this project.
_TRAIN_TO_HOLDOUT: dict[SampleName, SampleName] = {
    "E10k-ego": "G200-ego",
    "E10k-ego4d": "G200-ego4d",
    "E10k-epic": "G200-epic",
}

_JUDGE_REV_UNKNOWN = (
    "unknown (Build AI's original judge call; exact API snapshot not disclosed upstream)"
)

_RESPONSE_LIST_ADAPTER = TypeAdapter(list[JudgeResponse])


def _stored_label_response(frame_id: str, hand_count: int, active_labor: bool) -> JudgeResponse:
    return JudgeResponse(
        frame_id=frame_id,
        judge="gemini-2.5-flash",
        judge_rev=_JUDGE_REV_UNKNOWN,
        prompt_variant="P0b",
        hands_visible=cast(Literal[0, 1, 2], hand_count),
        manipulation=active_labor,
        confidence=Confidence(kind="none", value=None),
        raw=f"{hand_count}\n---\n{'yes' if active_labor else 'no'}",
        status="ok",
        latency_ms=0,
        cost_usd=0.0,
    )


def generate_labels() -> list[JudgeResponse]:
    """Real stored labels for every training-arm frame not reserved for evaluation, across all
    three corpora. Zero live judge calls; reads only the already-downloaded evaluation
    parquets and the already-drawn, already-persisted sample membership
    (`scripts/draw_all_samples.py`)."""
    responses: list[JudgeResponse] = []
    for train_sample, holdout_sample in _TRAIN_TO_HOLDOUT.items():
        all_frames = load_membership(train_sample, _MEMBERSHIP_ROOT)
        eval_ids = {f.frame_id for f in load_membership(holdout_sample, _MEMBERSHIP_ROOT)}
        train_frame_ids = {f.frame_id for f in all_frames if f.frame_id not in eval_ids}
        labels = published_labels_for_sample(train_sample, train_frame_ids)
        for frame_id, (hand_count, active_labor) in labels.items():
            responses.append(_stored_label_response(frame_id, hand_count, active_labor))
    return responses


def main(argv: list[str] | None = None) -> int:
    responses = generate_labels()
    out = Path("data/rung1_stored_labels.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(_RESPONSE_LIST_ADAPTER.dump_json(responses))
    print(f"wrote {len(responses)} real stored labels to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
