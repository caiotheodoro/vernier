"""Interactive CLI for Wave 3's 600 primary + 100 retest human labels (`docs/RUBRIC.md` v1.2.0).

Never automated, by design (`AGENTS.md`) -- this is the actual driver a human rater runs, one
frame at a time: shows the real frame image (opened in the OS's default viewer), prompts for
both tasks plus edge-case tags, difficulty, and a note, times the frame automatically (wall
clock between the image being shown and the label being submitted -- more honest than a
self-reported guess, per RUBRIC.md's "the honest input to any cost claim"), and writes the
result via the real `HumanLabelStore`.

Never displays judge output -- there is no code path here that could (this module never
imports `vernier.judges`, same guarantee as `labels/tool.py` itself).

Usage: `python3 scripts/human_labels_cli.py --rater caio --pass primary`
Ctrl-C at any prompt exits cleanly; whatever was already labelled stays labelled, and running
the command again resumes at the next pending frame (`next_frame`'s own pool-shrinking
behaviour -- nothing here tracks progress itself).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from vernier.labels.store import HumanLabelStore
from vernier.labels.tool import next_frame, record_label
from vernier.models import EdgeCaseTag, PassType
from vernier.sampling.draw import image_bytes_for

# Re-declared, not imported, matching `labels/tool.py`'s own `_LABEL_STORE_ROOT` -- D033's
# no-shared-file-edits convention already established across this codebase.
_LABEL_STORE_ROOT = Path("data/labels")

_EDGE_CASE_TAGS: tuple[EdgeCaseTag, ...] = (
    "partial",
    "glove",
    "tool-occlusion",
    "reflection",
    "blur",
    "edge",
    "undecidable",
    "idle-grip",
    "gesture",
    "self-contact",
    "between-actions",
    "dark",
    "other-person",
)

_RUBRIC_REV = "1.2.0"  # docs/RUBRIC.md, frozen alongside PRE-REGISTRATION.md.


def _show_frame(image_bytes: bytes) -> None:
    """Write the real frame image to a fixed scratch path and open it in the OS's default
    viewer. Falls back to just printing the path if no opener is found (`open` on macOS;
    `xdg-open` on Linux) -- the rater can open it manually either way."""
    path = Path(tempfile.gettempdir()) / "vernier_label_frame.jpg"
    path.write_bytes(image_bytes)
    opener = "open" if shutil.which("open") else "xdg-open" if shutil.which("xdg-open") else None
    if opener is None:
        print(f"(no OS image opener found -- open this file manually: {path})")
        return
    subprocess.run([opener, str(path)], check=False)


def _prompt_int_choice(prompt: str, choices: tuple[int, ...]) -> int:
    while True:
        raw = input(prompt).strip()
        try:
            value = int(raw)
        except ValueError:
            print(f"  not a number, try one of {choices}")
            continue
        if value not in choices:
            print(f"  must be one of {choices}")
            continue
        return value


def _prompt_yes_no(prompt: str) -> bool:
    while True:
        raw = input(prompt).strip().lower()
        if raw in ("y", "yes", "true"):
            return True
        if raw in ("n", "no", "false"):
            return False
        print("  answer y/n")


def _prompt_edge_case_tags() -> list[EdgeCaseTag]:
    print(f"  edge-case tags (comma-separated, blank for none): {', '.join(_EDGE_CASE_TAGS)}")
    while True:
        raw = input("  tags> ").strip()
        if not raw:
            return []
        tags = [t.strip() for t in raw.split(",") if t.strip()]
        bad = [t for t in tags if t not in _EDGE_CASE_TAGS]
        if bad:
            print(f"  not in the closed tag list: {bad} -- RUBRIC.md's list is closed, see above")
            continue
        return tags  # type: ignore[return-value]  # validated against _EDGE_CASE_TAGS above


def _label_one_frame(rater: str, pass_: PassType) -> bool:
    """Returns False when the pass is complete (nothing left to label), True otherwise."""
    frame = next_frame(pass_=pass_, rater=rater)
    if frame is None:
        return False

    image_bytes = image_bytes_for(frame)
    _show_frame(image_bytes)
    start = time.monotonic()

    print(f"\nframe_id: {frame.frame_id}  (sample={frame.sample}, pass={pass_})")
    hands_visible = _prompt_int_choice("hands_visible (0/1/2): ", (0, 1, 2))
    manipulation = _prompt_yes_no("active manipulation (y/n): ")
    edge_case = _prompt_edge_case_tags()
    difficulty = input("difficulty (easy/medium/hard): ").strip() or "medium"
    note = input("note (optional): ").strip()

    seconds_spent = int(time.monotonic() - start)
    label = record_label(
        frame=frame,
        rater=rater,
        pass_=pass_,
        rubric_rev=_RUBRIC_REV,
        hands_visible=hands_visible,
        manipulation=manipulation,
        edge_case=edge_case,
        difficulty=difficulty,
        note=note,
        seconds_spent=seconds_spent,
    )
    HumanLabelStore(_LABEL_STORE_ROOT / rater).write(label)
    print(f"  recorded ({seconds_spent}s)")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rater", required=True, help="your name/id, consistent across a pass")
    parser.add_argument("--pass", dest="pass_", required=True, choices=["primary", "retest"])
    args = parser.parse_args(argv)

    n_labelled = 0
    try:
        while _label_one_frame(args.rater, args.pass_):
            n_labelled += 1
    except KeyboardInterrupt:
        print(f"\nstopped -- {n_labelled} frame(s) labelled this run, resume any time")
        return 0

    print(f"\npass '{args.pass_}' complete -- {n_labelled} frame(s) labelled this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
