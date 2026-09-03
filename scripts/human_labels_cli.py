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

**Reduced target, real deviation (`docs/DECISIONS.md` D057)**: Caio declined the pre-registered
600 primary + 100 retest as too much labelling time. Agreed real target: 90 primary (30 each,
balanced across `G200-ego`/`G200-ego4d`/`G200-epic` -- D023's own design already calls this a
*balanced* gold set, so a reduced set stays balanced too rather than falling out of a random
600-frame draw) + 30 retest. `next_frame` pools all three `G200-*` samples together with no
per-sample stop point, so hitting an even 30/30/30 split off the merged pool needs its own
scoping -- `--sample` runs one `G200-*` set in isolation (its own local pending-pool/RNG,
mirroring `labels/tool.py`'s own pattern rather than editing its frozen functions, D033's
established convention); `--stop-after N` stops cleanly after N real labels this run,
regardless of what remains in the pool. Recommended real usage for the reduced target:

    python3 scripts/human_labels_cli.py --rater caio --pass primary --sample G200-ego --stop-after 30
    python3 scripts/human_labels_cli.py --rater caio --pass primary --sample G200-ego4d --stop-after 30
    python3 scripts/human_labels_cli.py --rater caio --pass primary --sample G200-epic --stop-after 30
    python3 scripts/human_labels_cli.py --rater caio --pass retest --stop-after 30

Omitting `--sample` keeps the original merged-pool behaviour (still real, still useful for the
full pre-registered run if that ever changes back).

**Real correctness gap found and fixed (`docs/DECISIONS.md` D058)**: the reduced target above
broke intra-rater reliability. `R100`'s fixed 100-frame membership was drawn assuming the *full*
600-frame primary pass (under which `R100` -- itself a subset of the 600 -- is always fully
overlapped by whatever's already primary-labelled). At 93/600 primary, a `--pass retest` run
against `R100`'s real fixed pool landed on only ~4 frames also present in the primary labels
(matching the ~93/600 * 30 expected-by-chance overlap) -- nowhere near enough to say anything
about "does human gold disagree with itself," the pre-registration's own *first* falsification
check. Fixed with `--retest-from-primary`: draws its pool from whatever this rater has *already
primary-labelled* (real, on-disk, via `HumanLabelStore`), not `R100`'s fixed membership --
guaranteeing every retest label overlaps a real primary one. Real usage:

    python3 scripts/human_labels_cli.py --rater caio --pass retest --retest-from-primary --stop-after 30
"""

from __future__ import annotations

import argparse
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from vernier.labels.store import HumanLabelStore
from vernier.labels.tool import next_frame, record_label
from vernier.sampling.membership import load_membership
from vernier.models import EdgeCaseTag, FrameRef, PassType
from vernier.sampling.draw import SampleName, image_bytes_for

# Re-declared, not imported, matching `labels/tool.py`'s own `_LABEL_STORE_ROOT`/
# `_MEMBERSHIP_ROOT`/`_SEED` -- D033's no-shared-file-edits convention already established
# across this codebase for small constants like these.
_LABEL_STORE_ROOT = Path("data/labels")
_MEMBERSHIP_ROOT = Path("data/membership")
_SEED = 777

# D057's reduced-target samples -- the same three sets `labels/tool.py`'s merged "primary" pool
# draws from, exposed here individually so `--sample` can scope one at a time.
_PRIMARY_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")


def _scoped_pending_frames(sample: SampleName, pass_: PassType, rater: str) -> list[FrameRef]:
    """Real pending pool for one specific `G200-*` sample, mirroring `labels.tool._pending_frames`
    but scoped instead of merged -- needed for D057's balanced reduced target (30/arm), since
    the merged pool has no per-sample stop point."""
    store = HumanLabelStore(_LABEL_STORE_ROOT / rater)
    pool = load_membership(sample, _MEMBERSHIP_ROOT)
    return [f for f in pool if not store.has_label(f.frame_id, pass_)]


def _scoped_next_frame(sample: SampleName, pass_: PassType, rater: str) -> FrameRef | None:
    """Same contract as `labels.tool.next_frame`, scoped to one sample: deterministic per
    (rater, pass_, sample), returns the same frame on repeated calls until a label is recorded
    for it, `None` once that sample's pool is exhausted."""
    pending = _scoped_pending_frames(sample, pass_, rater)
    if not pending:
        return None
    return random.Random(f"{_SEED}:{rater}:{pass_}:{sample}").choice(pending)


def _primary_labelled_frame_ids(rater: str) -> set[str]:
    return {label.frame_id for label in HumanLabelStore(_LABEL_STORE_ROOT / rater).read_pass("primary")}


def _frames_by_id(frame_ids: set[str]) -> dict[str, FrameRef]:
    """Resolve `frame_ids` to their real `FrameRef`s by scanning the three `G200-*` membership
    pools -- the only place a primary-labelled frame's full record lives; `HumanLabel` itself
    stores only `frame_id` (D058)."""
    found: dict[str, FrameRef] = {}
    for sample in _PRIMARY_SAMPLES:
        for frame in load_membership(sample, _MEMBERSHIP_ROOT):
            if frame.frame_id in frame_ids:
                found[frame.frame_id] = frame
    return found


def _retest_from_primary_pending_frames(rater: str) -> list[FrameRef]:
    """D058: the real fix for broken intra-rater overlap at a reduced primary target -- this
    pool is whatever the rater has *already primary-labelled* (real, on-disk), not `R100`'s
    fixed membership, guaranteeing every retest label overlaps a real primary one."""
    store = HumanLabelStore(_LABEL_STORE_ROOT / rater)
    resolved = _frames_by_id(_primary_labelled_frame_ids(rater))
    return [f for fid, f in resolved.items() if not store.has_label(fid, "retest")]


def _retest_from_primary_next_frame(rater: str) -> FrameRef | None:
    pending = _retest_from_primary_pending_frames(rater)
    if not pending:
        return None
    return random.Random(f"{_SEED}:{rater}:retest-from-primary").choice(pending)


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


def _label_one_frame(
    rater: str,
    pass_: PassType,
    sample: SampleName | None = None,
    retest_from_primary: bool = False,
) -> bool:
    """Returns False when the pool in play is complete, True otherwise. `sample` is `None` by
    default -- the original merged-pool behaviour, unchanged -- and only meaningful for
    `pass_="primary"` (D057's per-arm scoping). `retest_from_primary` (D058) only meaningful for
    `pass_="retest"`: draws from this rater's own already-primary-labelled frames instead of
    `R100`'s fixed membership, so intra-rater agreement has real overlap to measure at a reduced
    primary target. `sample` and `retest_from_primary` are mutually exclusive with each other by
    construction (one only applies to primary, the other only to retest)."""
    if sample is not None:
        frame = _scoped_next_frame(sample, pass_, rater)
    elif retest_from_primary:
        frame = _retest_from_primary_next_frame(rater)
    else:
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
    parser.add_argument(
        "--sample",
        choices=list(_PRIMARY_SAMPLES),
        default=None,
        help="scope to one G200-* sample only, for a balanced reduced target (D057); "
        "primary only, invalid with --pass retest (R100 is already a single sample)",
    )
    parser.add_argument(
        "--stop-after",
        type=int,
        default=None,
        help="stop cleanly after N real labels this run, regardless of what remains pending",
    )
    parser.add_argument(
        "--retest-from-primary",
        action="store_true",
        help="D058: draw retest frames from this rater's own already-primary-labelled frames "
        "instead of R100's fixed membership -- fixes broken intra-rater overlap at a reduced "
        "primary target; retest only, invalid with --pass primary or with --sample",
    )
    args = parser.parse_args(argv)

    if args.sample is not None and args.pass_ != "primary":
        parser.error("--sample is only valid with --pass primary")
    if args.retest_from_primary and args.pass_ != "retest":
        parser.error("--retest-from-primary is only valid with --pass retest")
    if args.retest_from_primary and args.sample is not None:
        parser.error("--retest-from-primary and --sample are mutually exclusive")

    n_labelled = 0
    try:
        while args.stop_after is None or n_labelled < args.stop_after:
            if not _label_one_frame(args.rater, args.pass_, args.sample, args.retest_from_primary):
                break
            n_labelled += 1
    except KeyboardInterrupt:
        print(f"\nstopped -- {n_labelled} frame(s) labelled this run, resume any time")
        return 0

    print(f"\n{n_labelled} frame(s) labelled this run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
