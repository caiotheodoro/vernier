"""The human annotation store.

Hard constraint, enforced here rather than by discipline: this store has no read path to
judge output -- the judges package is never imported, directly or transitively, anywhere in
this module. The `retest` pass additionally has no read path to the `primary` pass.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import TypeAdapter

from vernier.models import HumanLabel, PassType

_LABEL_LIST_ADAPTER = TypeAdapter(list[HumanLabel])


class DuplicateLabelError(ValueError):
    """Raised when a label for an already-labelled `(frame_id, rater, pass_)` is written again."""


class HumanLabelStore:
    """Persists `HumanLabel` records. Never imports, calls, or exposes judge output.

    On-disk layout: one JSON file per pass, `<path>/<pass_>.json`, holding a JSON array of
    `HumanLabel` records (each shaped per `HumanLabel.model_dump(mode="json", by_alias=True)`).
    One file per pass means the `retest` pass never touches -- and has no read path to -- the
    `primary` pass's file, mirroring `vernier.sampling.membership`'s one-file-per-key pattern.
    """

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.mkdir(parents=True, exist_ok=True)

    def _pass_path(self, pass_: PassType) -> Path:
        return self._path / f"{pass_}.json"

    def write(self, label: HumanLabel) -> None:
        """Append one label. Raises if a label for this `(frame_id, rater, pass_)` already exists --
        no frame is revisited within a pass."""
        existing = self.read_pass(label.pass_)
        for recorded in existing:
            if recorded.frame_id == label.frame_id and recorded.rater == label.rater:
                raise DuplicateLabelError(
                    f"label already exists for frame_id={label.frame_id!r}, "
                    f"rater={label.rater!r}, pass_={label.pass_!r}"
                )
        existing.append(label)
        self._pass_path(label.pass_).write_bytes(_LABEL_LIST_ADAPTER.dump_json(existing, by_alias=True))

    def read_pass(self, pass_: PassType) -> list[HumanLabel]:
        """Return every label written for `pass_`, in the order they were written."""
        pass_path = self._pass_path(pass_)
        if not pass_path.is_file():
            return []
        return _LABEL_LIST_ADAPTER.validate_json(pass_path.read_bytes())

    def has_label(self, frame_id: str, pass_: PassType) -> bool:
        """Whether a label already exists for `(frame_id, pass_)`, scoped to this store's own
        path -- i.e. among the labels this store instance has written so far, regardless of
        which rater's name is on the record. Callers keep one store per rater, per `__init__`."""
        return any(recorded.frame_id == frame_id for recorded in self.read_pass(pass_))
