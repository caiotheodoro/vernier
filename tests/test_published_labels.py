"""Behavioural tests for `scripts/published_labels.py`.

Didn't exist before D066 -- a real, pre-existing gap, not something D066 introduces. The single
most important case here is the `E100k-ego` join-key-space check: `draw.py` and
`published_labels.py` each independently import `synthetic_frame_id` from the same place, but
if that ever stopped being true (a drifted second implementation), the join would silently
return nothing for every frame, not raise -- exactly the failure mode a crash-only test suite
would miss.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from published_labels import _parse_active_labor, published_labels_for_sample  # noqa: E402

from vernier.sampling.draw import synthetic_frame_id  # noqa: E402


def _real_jpeg_bytes(width: int, height: int) -> bytes:
    import io

    from PIL import Image

    buf = io.BytesIO()
    Image.new("RGB", (width, height), color="blue").save(buf, format="JPEG")
    return buf.getvalue()


def _write_labelled_parquet(
    path: Path, rows: list[tuple[str, bytes, int, str]], *, with_frame_id: bool
) -> None:
    """`rows` is `(frame_id, image_bytes, hand_count, active_labor)`. `with_frame_id=False`
    mirrors the real 100K-eval schema (`docs/UPSTREAM-FINDINGS.md` F10): no `frame_id` column
    at all."""
    columns: dict[str, pa.Array] = {
        "image": pa.array(
            [{"bytes": r[1], "path": None} for r in rows],
            type=pa.struct([("bytes", pa.binary()), ("path", pa.string())]),
        ),
        "hand_count": pa.array([r[2] for r in rows], type=pa.int32()),
        "active_labor": pa.array([r[3] for r in rows], type=pa.string()),
    }
    if with_frame_id:
        columns = {"frame_id": pa.array([r[0] for r in rows], type=pa.string()), **columns}
    pq.write_table(pa.table(columns), str(path))


def _patch_hf_hub_download(monkeypatch: pytest.MonkeyPatch, path: Path) -> None:
    monkeypatch.setattr("huggingface_hub.hf_hub_download", lambda **kwargs: str(path))


def test_published_labels_for_sample_10k_joins_by_real_frame_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpeg = _real_jpeg_bytes(8, 8)
    path = tmp_path / "eval.parquet"
    _write_labelled_parquet(path, [("frame-a", jpeg, 2, "yes")], with_frame_id=True)
    _patch_hf_hub_download(monkeypatch, path)

    result = published_labels_for_sample("E10k-ego")

    assert result == {"frame-a": (2, True)}


def test_published_labels_for_sample_100k_joins_by_synthetic_frame_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real regression case: E100k-ego has no frame_id column, so the join must succeed
    using synthetic_frame_id -- the same id `sampling/draw.py`'s FrameRef pool would carry for
    this exact image, computed independently but via the same imported function."""
    jpeg = _real_jpeg_bytes(8, 8)
    path = tmp_path / "eval_100k.parquet"
    _write_labelled_parquet(path, [("unused", jpeg, 1, "no")], with_frame_id=False)
    _patch_hf_hub_download(monkeypatch, path)

    result = published_labels_for_sample("E100k-ego")

    assert result == {synthetic_frame_id(jpeg): (1, False)}


def test_published_labels_for_sample_100k_filters_by_requested_frame_ids(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    jpeg_keep = _real_jpeg_bytes(8, 8)
    jpeg_drop = _real_jpeg_bytes(4, 4)
    path = tmp_path / "eval_100k.parquet"
    _write_labelled_parquet(
        path, [("_", jpeg_keep, 2, "yes"), ("_", jpeg_drop, 0, "no")], with_frame_id=False
    )
    _patch_hf_hub_download(monkeypatch, path)

    result = published_labels_for_sample("E100k-ego", {synthetic_frame_id(jpeg_keep)})

    assert result == {synthetic_frame_id(jpeg_keep): (2, True)}


def test_published_labels_for_sample_100k_excludes_empty_image_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "eval_100k.parquet"
    _write_labelled_parquet(path, [("_", b"", 2, "yes")], with_frame_id=False)
    _patch_hf_hub_download(monkeypatch, path)

    result = published_labels_for_sample("E100k-ego")

    assert result == {}


# --- _parse_active_labor (docs/DECISIONS.md D067): a real bug, found only after a full real
# run against the actual 100K-eval parquet -- its `active_labor` column encodes "true"/"false",
# not "yes"/"no" like the 10K-eval schema. The first real run silently treated `"true" == "yes"`
# as always False, collapsing `active_labor_agreement_rate` to ~8% (chance-level agreement with
# an always-False label, not a real measurement). These tests use the REAL vendor encoding, not
# the "yes"/"no" shape the original (buggy) test fixtures used -- exactly the gap that let the
# bug through unit tests in the first place.


def test_parse_active_labor_accepts_yes_no() -> None:
    assert _parse_active_labor("yes") is True
    assert _parse_active_labor("no") is False


def test_parse_active_labor_accepts_true_false() -> None:
    assert _parse_active_labor("true") is True
    assert _parse_active_labor("false") is False


def test_parse_active_labor_rejects_unrecognized_value() -> None:
    with pytest.raises(ValueError, match="unrecognized active_labor value"):
        _parse_active_labor("Yes")  # case matters -- a real, closed mapping, not case-folded


def test_published_labels_for_sample_100k_parses_the_real_true_false_encoding(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression guard for the real D067 bug, using the REAL 100K-eval encoding
    ("true"/"false"), not the "yes"/"no" shape that let the original bug through."""
    jpeg_true = _real_jpeg_bytes(8, 8)
    jpeg_false = _real_jpeg_bytes(4, 4)
    path = tmp_path / "eval_100k.parquet"
    _write_labelled_parquet(
        path, [("_", jpeg_true, 2, "true"), ("_", jpeg_false, 0, "false")], with_frame_id=False
    )
    _patch_hf_hub_download(monkeypatch, path)

    result = published_labels_for_sample("E100k-ego")

    assert result == {
        synthetic_frame_id(jpeg_true): (2, True),
        synthetic_frame_id(jpeg_false): (0, False),
    }
