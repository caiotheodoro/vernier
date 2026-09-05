"""Blind re-review of the frames where a rater and the judge disagree (`docs/RUBRIC.md` v1.2.0).

A targeted review is easy to do badly. Two things make the result worth having, and both are
enforced here rather than left to the rater's discipline:

**It is blind.** The rater never sees the judge's answer, and never sees their own original
label. Same guarantee `human_labels_cli.py` gives, by the same means: the labelling path in this
module imports nothing from `vernier.judges` and opens no judge file. Only `plan` reads judge
output, it runs as a separate command, and all it emits is a list of frame ids.

**It is salted.** A set containing only disagreements tells the rater, on every frame, that this
is one they may have got wrong -- which is a prompt to change the answer, not a re-read of the
frame. `plan` therefore mixes in control frames the rater and the judge already agreed on, and
does not reveal which arm a frame is in. `report` then compares the change rate on each arm. If
the rater revises disagreements far more often than controls, the review found something; if
both move about equally, the review is measuring the rater's day, not the frames.

Writes `pass="review"` -- a third pass, never an edit of `primary`. The primary labels back
published claims (H4's AC1, H5, every PPI estimate, the measurement card), so correcting them in
place would silently restate results that are already public. Nothing reads the `review` pass
until an analysis is changed to ask for it, which is a deliberate step with its own entry in
`docs/DECISIONS.md`.

Usage:

    python3 scripts/review_labels_cli.py plan   --rater caio
    python3 scripts/review_labels_cli.py label  --rater caio --stop-after 10
    python3 scripts/review_labels_cli.py report --rater caio

`plan` is idempotent and refuses to overwrite an existing set: re-planning mid-review would
change what the rater is being asked, halfway through asking it. `label` resumes where it left
off, and Ctrl-C at any prompt exits cleanly with everything already labelled kept.
"""

from __future__ import annotations

import argparse
import json
import random
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Literal

from vernier.labels.store import HumanLabelStore
from vernier.labels.tool import record_label
from vernier.models import EdgeCaseTag, FrameRef, HumanLabel, PassType
from vernier.sampling.draw import SampleName, image_bytes_for
from vernier.sampling.membership import load_membership

# Re-declared, not imported, matching `human_labels_cli.py`'s own convention (D033).
_LABEL_STORE_ROOT = Path("data/labels")
_MEMBERSHIP_ROOT = Path("data/membership")
_GOLD_JUDGED_ROOT = Path("data/gold_judged")
_SEED = 777
_RUBRIC_REV = "1.2.0"
_VARIANT = "P0b"
_PASS: PassType = "review"
_GOLD_SAMPLES: tuple[SampleName, ...] = ("G200-ego", "G200-ego4d", "G200-epic")

Arm = Literal["disagreement", "control"]

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


def _set_path(rater: str) -> Path:
    return _LABEL_STORE_ROOT / rater / "review_set.json"


def _primary(rater: str) -> dict[str, HumanLabel]:
    return {lab.frame_id: lab for lab in HumanLabelStore(_LABEL_STORE_ROOT / rater).read_pass("primary")}


def _frames_by_id() -> dict[str, FrameRef]:
    out: dict[str, FrameRef] = {}
    for sample in _GOLD_SAMPLES:
        for frame in load_membership(sample, _MEMBERSHIP_ROOT):
            out[frame.frame_id] = frame
    return out


def _interleave(rng: random.Random, disagreements: list[str], controls: list[str]) -> list[dict[str, str]]:
    """Shuffle within each arm, then merge so that every prefix stays close to the overall mix.

    A flat shuffle is unbiased over the whole set but clumpy over any prefix -- the first draw
    here put six controls before the first disagreement and then nine disagreements in a row.
    That matters because the rater works in sittings (`--stop-after`), and a sitting that is
    almost all one arm is exactly the tell the controls exist to remove.
    """
    pools = {"disagreement": list(disagreements), "control": list(controls)}
    for pool in pools.values():
        rng.shuffle(pool)
    total = {arm: len(pool) for arm, pool in pools.items()}
    taken = {arm: 0 for arm in pools}
    out: list[dict[str, str]] = []
    while any(pools.values()):
        # Whichever arm is furthest behind the share it should have by now goes next; ties, and
        # the first pick, broken at random rather than always the same way.
        candidates = [arm for arm, pool in pools.items() if pool]
        deficits = [(taken[arm] / total[arm], rng.random(), arm) for arm in candidates]
        _, _, arm = min(deficits)
        out.append({"frame_id": pools[arm].pop(), "arm": arm})
        taken[arm] += 1
    return out


# ── plan ────────────────────────────────────────────────────────────────────────────────────
# The only command that reads judge output. It writes frame ids and an arm label, nothing else:
# no judge answer, no original label, no reason. `label` cannot reconstruct any of it.


def _judge_answers() -> dict[str, tuple[int | None, bool | None]]:
    answers: dict[str, tuple[int | None, bool | None]] = {}
    for sample in _GOLD_SAMPLES:
        path = _GOLD_JUDGED_ROOT / f"{sample}.{_VARIANT}.json"
        if not path.exists():
            continue
        for record in json.loads(path.read_text()):
            if record.get("status") != "ok":
                continue
            answers[record["frame_id"]] = (record.get("hands_visible"), record.get("manipulation"))
    return answers


def plan(rater: str, controls_per_disagreement: float, force: bool) -> int:
    path = _set_path(rater)
    if path.exists() and not force:
        print(f"{path} already exists. Re-planning mid-review would change the question halfway", file=sys.stderr)
        print("through asking it. Delete it deliberately, or pass --force, if that is what you want.", file=sys.stderr)
        return 1

    primary = _primary(rater)
    if not primary:
        print(f"no primary labels for rater {rater!r}", file=sys.stderr)
        return 1
    judged = _judge_answers()

    disagreements: list[str] = []
    controls: list[str] = []
    for frame_id, label in primary.items():
        answer = judged.get(frame_id)
        if answer is None:
            continue
        hands, manip = answer
        differs = (hands is not None and hands != label.hands_visible) or (
            manip is not None and manip != label.manipulation
        )
        (disagreements if differs else controls).append(frame_id)

    rng = random.Random(f"{_SEED}:{rater}:{_PASS}")
    n_controls = min(len(controls), round(len(disagreements) * controls_per_disagreement))
    picked_controls = rng.sample(sorted(controls), n_controls)
    entries = _interleave(rng, sorted(disagreements), picked_controls)

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"rater": rater, "rubric_rev": _RUBRIC_REV, "seed": _SEED, "frames": entries}, indent=1) + "\n")
    print(f"wrote {path}: {len(entries)} frames ({len(disagreements)} disagreement, {n_controls} control)")
    print("The arm is recorded for the report and is never shown while labelling.")
    return 0


# ── label ───────────────────────────────────────────────────────────────────────────────────
# Reads the plan and nothing else. No judge file is opened on this path.


def _load_set(rater: str) -> list[dict[str, str]]:
    path = _set_path(rater)
    if not path.exists():
        raise SystemExit(f"no review set at {path} -- run `plan` first")
    payload: dict[str, Any] = json.loads(path.read_text())
    frames: list[dict[str, str]] = payload["frames"]
    return frames


def _show_frame(image_bytes: bytes) -> None:
    path = Path(tempfile.gettempdir()) / "vernier_review_frame.jpg"
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


def _prompt_difficulty(prompt: str) -> str:
    while True:
        raw = input(prompt).strip().lower()
        if not raw:
            return "medium"
        if raw in ("easy", "medium", "hard"):
            return raw
        print("  must be one of ('easy', 'medium', 'hard')")


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


def label(rater: str, stop_after: int | None) -> int:
    entries = _load_set(rater)
    store = HumanLabelStore(_LABEL_STORE_ROOT / rater)
    frames = _frames_by_id()
    pending = [e for e in entries if not store.has_label(e["frame_id"], _PASS)]
    if not pending:
        print(f"review pass complete for {rater}: {len(entries)} frames labelled")
        return 0

    print(f"{len(pending)} of {len(entries)} frames left. The judge's answer and your original")
    print("label are not shown, deliberately. Label what you see.\n")

    done = 0
    for entry in pending:
        if stop_after is not None and done >= stop_after:
            print(f"\nstopping after {done} this run; {len(pending) - done} left")
            return 0
        frame = frames.get(entry["frame_id"])
        if frame is None:
            print(f"  {entry['frame_id']}: not in any G200 membership, skipping", file=sys.stderr)
            continue

        _show_frame(image_bytes_for(frame))
        start = time.monotonic()
        print(f"\nframe_id: {frame.frame_id}  ({done + 1} of {min(len(pending), stop_after or len(pending))})")
        hands_visible = _prompt_int_choice("hands_visible (0/1/2): ", (0, 1, 2))
        manipulation = _prompt_yes_no("active manipulation (y/n): ")
        edge_case = _prompt_edge_case_tags()
        difficulty = _prompt_difficulty("difficulty (easy/medium/hard): ")
        note = input("note (optional): ").strip()

        seconds_spent = int(time.monotonic() - start)
        store.write(
            record_label(
                frame=frame,
                rater=rater,
                pass_=_PASS,
                rubric_rev=_RUBRIC_REV,
                hands_visible=hands_visible,
                manipulation=manipulation,
                edge_case=edge_case,
                difficulty=difficulty,
                note=note,
                seconds_spent=seconds_spent,
            )
        )
        print(f"  recorded ({seconds_spent}s)")
        done += 1

    print(f"\nreview pass complete: {len(entries)} frames")
    return 0


# ── report ──────────────────────────────────────────────────────────────────────────────────


def report(rater: str) -> int:
    entries = {e["frame_id"]: e["arm"] for e in _load_set(rater)}
    store = HumanLabelStore(_LABEL_STORE_ROOT / rater)
    primary = _primary(rater)
    reviewed = {lab.frame_id: lab for lab in store.read_pass(_PASS)}
    if not reviewed:
        print("nothing reviewed yet")
        return 0

    stats: dict[str, dict[str, int]] = {
        arm: {"n": 0, "hands_changed": 0, "manip_changed": 0, "either": 0} for arm in ("disagreement", "control")
    }
    changes: list[str] = []
    for frame_id, new in reviewed.items():
        arm = entries.get(frame_id)
        old = primary.get(frame_id)
        if arm is None or old is None:
            continue
        h = new.hands_visible != old.hands_visible
        m = new.manipulation != old.manipulation
        stats[arm]["n"] += 1
        stats[arm]["hands_changed"] += int(h)
        stats[arm]["manip_changed"] += int(m)
        stats[arm]["either"] += int(h or m)
        if h or m:
            parts = []
            if h:
                parts.append(f"hands {old.hands_visible}->{new.hands_visible}")
            if m:
                parts.append(f"manip {old.manipulation}->{new.manipulation}")
            changes.append(f"  {frame_id[:8]}  {arm:13s} {', '.join(parts)}")

    print(f"reviewed {sum(s['n'] for s in stats.values())} frames\n")
    print(f"{'arm':14s} {'n':>4s} {'hands':>7s} {'manip':>7s} {'either':>8s}")
    for arm, s in stats.items():
        if s["n"] == 0:
            continue
        rate = s["either"] / s["n"]
        print(f"{arm:14s} {s['n']:4d} {s['hands_changed']:7d} {s['manip_changed']:7d} {s['either']:5d} ({rate:.0%})")

    d, c = stats["disagreement"], stats["control"]
    if d["n"] and not c["n"]:
        print()
        print("No control arm in this set, so the revision rate above cannot be separated from")
        print("how often a re-read changes an answer at all. It is a description of what you did,")
        print("not evidence that the frames were mislabelled.")
    if d["n"] and c["n"]:
        print()
        dr, cr = d["either"] / d["n"], c["either"] / c["n"]
        if cr >= dr:
            print("The control arm moved at least as much as the disagreement arm. This review is")
            print("measuring re-labelling noise, not frames the judge caught -- do not use it to")
            print("revise anything.")
        else:
            print(f"Disagreements revised at {dr:.0%} against {cr:.0%} on controls. The gap is the")
            print("part attributable to the frames rather than to relabelling.")

    if changes:
        print("\nchanged:")
        print("\n".join(sorted(changes)))
    print("\nThe primary pass is untouched. Folding any of this into a published number is a")
    print("separate, deliberate step, and needs its own docs/DECISIONS.md entry.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)

    p_plan = sub.add_parser("plan", help="build the review set (the only command that reads judge output)")
    p_plan.add_argument("--rater", required=True)
    p_plan.add_argument(
        "--controls-per-disagreement",
        type=float,
        default=1.0,
        help="control frames per disagreement frame (default 1.0, i.e. a 50/50 set)",
    )
    p_plan.add_argument("--force", action="store_true", help="overwrite an existing review set")

    p_label = sub.add_parser("label", help="label the review set, blind")
    p_label.add_argument("--rater", required=True)
    p_label.add_argument("--stop-after", type=int, default=None, help="stop cleanly after N frames this run")

    p_report = sub.add_parser("report", help="compare the review pass against primary, by arm")
    p_report.add_argument("--rater", required=True)

    args = parser.parse_args(argv)
    if args.command == "plan":
        return plan(args.rater, args.controls_per_disagreement, args.force)
    if args.command == "label":
        return label(args.rater, args.stop_after)
    return report(args.rater)


if __name__ == "__main__":
    raise SystemExit(main())
