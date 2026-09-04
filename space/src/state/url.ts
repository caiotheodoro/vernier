// The URL hash is the store. Every control writes it; loading a hash restores every control.
import { useSyncExternalStore } from "react";
import type { Corpus, Task } from "../data/types";

export type Answer = "0" | "1" | "2" | "yes" | "no";
export type JudgeFilter = Answer | "unparsed";
export type RaterFilter = Answer | "unlabelled";
export type Agreement = "agrees" | "disagrees" | "none";
export type ConfBand = "ge99" | "90to99" | "lt90";
export type JudgeSource = "qwen" | "gemini";
export type CorpusFilter = Corpus | "all";
export type View = "quality" | "coverage" | "health";

export type SliceState = {
  task: Task;
  corpus: CorpusFilter;
  judge: JudgeFilter | null;
  rater: RaterFilter | null;
  agree: Agreement | null;
  conf: ConfBand | null;
  src: JudgeSource;
  f: string | null;
  view: View | null;
};

export const DEFAULT_STATE: SliceState = {
  task: "manipulation",
  corpus: "egocentric-10k",
  judge: null,
  rater: null,
  agree: null,
  conf: null,
  src: "qwen",
  f: null,
  view: null,
};

const TASKS = new Set<string>(["hand_count", "hand_eq2", "manipulation"]);
const CORPORA = new Set<string>(["egocentric-10k", "ego4d", "epic-kitchens-100", "egocentric-100k", "all"]);
const JUDGE = new Set<string>(["0", "1", "2", "yes", "no", "unparsed"]);
const RATER = new Set<string>(["0", "1", "2", "yes", "no", "unlabelled"]);
const AGREE = new Set<string>(["agrees", "disagrees", "none"]);
const CONF = new Set<string>(["ge99", "90to99", "lt90"]);
const SRC = new Set<string>(["qwen", "gemini"]);
const VIEW = new Set<string>(["quality", "coverage", "health"]);

function pick<T extends string>(params: URLSearchParams, key: string, allowed: Set<string>): T | null {
  const v = params.get(key);
  return v !== null && allowed.has(v) ? (v as T) : null;
}

export function parseHash(hash: string): SliceState {
  const params = new URLSearchParams(hash.replace(/^#/, ""));
  const f = params.get("f");
  return {
    task: pick<Task>(params, "task", TASKS) ?? DEFAULT_STATE.task,
    corpus: pick<CorpusFilter>(params, "corpus", CORPORA) ?? DEFAULT_STATE.corpus,
    judge: pick<JudgeFilter>(params, "judge", JUDGE),
    rater: pick<RaterFilter>(params, "rater", RATER),
    agree: pick<Agreement>(params, "agree", AGREE),
    conf: pick<ConfBand>(params, "conf", CONF),
    src: pick<JudgeSource>(params, "src", SRC) ?? DEFAULT_STATE.src,
    f: f && /^[0-9a-f-]{36}$/.test(f) ? f : null,
    view: pick<View>(params, "view", VIEW),
  };
}

export function serialize(state: SliceState): string {
  const params = new URLSearchParams();
  params.set("task", state.task);
  params.set("corpus", state.corpus);
  if (state.judge) params.set("judge", state.judge);
  if (state.rater) params.set("rater", state.rater);
  if (state.agree) params.set("agree", state.agree);
  if (state.conf) params.set("conf", state.conf);
  if (state.src !== DEFAULT_STATE.src) params.set("src", state.src);
  if (state.f) params.set("f", state.f);
  if (state.view) params.set("view", state.view);
  return `#${params.toString()}`;
}

const EVENT = "vernier:hash";

function subscribe(cb: () => void): () => void {
  window.addEventListener("hashchange", cb);
  window.addEventListener(EVENT, cb);
  return () => {
    window.removeEventListener("hashchange", cb);
    window.removeEventListener(EVENT, cb);
  };
}

function snapshot(): string {
  return window.location.hash;
}

export function useHash(): string {
  return useSyncExternalStore(subscribe, snapshot, () => "");
}

/** Write a new state to the hash without adding a history entry (arrow-key selection would
 *  otherwise flood the back button). */
export function setState(next: SliceState): void {
  const hash = serialize(next);
  if (hash === window.location.hash) return;
  history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
  window.dispatchEvent(new Event(EVENT));
}

export function update(current: SliceState, patch: Partial<SliceState>): void {
  setState({ ...current, ...patch });
}
