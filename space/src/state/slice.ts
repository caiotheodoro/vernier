// Filter semantics shared by the grid, the hero's reason links and the confusion tables.
// `python -m vernier slice` (src/vernier/cli.py) implements the same rules over the same
// frames.json; its tests pin parity with this file on fixed inputs.
import type { Frame, Hands, Task } from "../data/types";
import type { Agreement, Answer, ConfBand, JudgeSource, SliceState } from "./url";

export type Binary = boolean;

/** The task's yes/no reading of a hands count. */
export function handsToBinary(task: Task, h: Hands): Binary {
  return task === "hand_eq2" ? h === 2 : h >= 1;
}

export function judgeHands(frame: Frame, src: JudgeSource): Hands | null {
  return src === "gemini" ? (frame.g ? frame.g.h : null) : frame.q.h;
}

export function judgeManipulation(frame: Frame, src: JudgeSource): boolean | null {
  return src === "gemini" ? (frame.g ? frame.g.m : null) : frame.q.m;
}

/** The judge's answer for the active task as a yes/no, null when unparseable/absent. */
export function judgeBinary(frame: Frame, task: Task, src: JudgeSource): Binary | null {
  if (task === "manipulation") return judgeManipulation(frame, src);
  const h = judgeHands(frame, src);
  return h === null ? null : handsToBinary(task, h);
}

export function raterBinary(frame: Frame, task: Task): Binary | null {
  if (!frame.r) return null;
  return task === "manipulation" ? frame.r.m : handsToBinary(task, frame.r.h);
}

/** Agreement for the active task: exact 0/1/2 match for hand_count (the 3x3 table), the
 *  binary reading for hand_eq2, yes/no for manipulation. Null when either side is missing. */
export function agrees(frame: Frame, task: Task, src: JudgeSource): boolean | null {
  if (!frame.r) return null;
  if (task === "hand_count") {
    const h = judgeHands(frame, src);
    return h === null ? null : h === frame.r.h;
  }
  const j = judgeBinary(frame, task, src);
  const r = raterBinary(frame, task);
  return j === null || r === null ? null : j === r;
}

export function confBand(c: number | null): ConfBand | null {
  if (c === null) return null;
  if (c >= 0.99) return "ge99";
  if (c >= 0.9) return "90to99";
  return "lt90";
}

function matchesAnswer(task: Task, answer: Answer, hands: Hands | null, manip: boolean | null): boolean {
  if (task === "manipulation") {
    if (manip === null) return false;
    return answer === "yes" ? manip : answer === "no" ? !manip : false;
  }
  if (hands === null) return false;
  if (answer === "yes") return handsToBinary(task, hands);
  if (answer === "no") return !handsToBinary(task, hands);
  return String(hands) === answer;
}

export function matches(frame: Frame, state: SliceState): boolean {
  if (state.corpus !== "all" && frame.corpus !== state.corpus) return false;
  const jh = judgeHands(frame, state.src);
  const jm = judgeManipulation(frame, state.src);
  if (state.judge === "unparsed") {
    if (frame.q.s === "ok") return false;
  } else if (state.judge !== null) {
    if (!matchesAnswer(state.task, state.judge, jh, jm)) return false;
  }
  if (state.rater === "unlabelled") {
    if (frame.r !== null) return false;
  } else if (state.rater === "labelled") {
    // The 93 frames a human actually judged -- the set every PPI estimate rests on.
    if (frame.r === null) return false;
  } else if (state.rater !== null) {
    if (!frame.r) return false;
    if (!matchesAnswer(state.task, state.rater, frame.r.h, frame.r.m)) return false;
  }
  if (state.agree !== null) {
    const a = agrees(frame, state.task, state.src);
    const want: Record<Agreement, boolean | null> = { agrees: true, disagrees: false, none: null };
    if (a !== want[state.agree]) return false;
  }
  if (state.conf !== null && confBand(frame.q.c) !== state.conf) return false;
  return true;
}

export function applySlice(frames: readonly Frame[], state: SliceState): Frame[] {
  return frames.filter((f) => matches(f, state));
}

/** The hero's three reason links, counted over the task x corpus slice only. */
export function reasonCounts(frames: readonly Frame[], state: SliceState): {
  judgeYesRaterNo: number;
  judgeNoRaterYes: number;
  unparsed: number;
} {
  const base: SliceState = { ...state, judge: null, rater: null, agree: null, conf: null, f: null };
  return {
    judgeYesRaterNo: applySlice(frames, { ...base, judge: "yes", rater: "no" }).length,
    judgeNoRaterYes: applySlice(frames, { ...base, judge: "no", rater: "yes" }).length,
    unparsed: applySlice(frames, { ...base, judge: "unparsed" }).length,
  };
}
