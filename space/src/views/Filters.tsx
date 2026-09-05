import { useEffect, useRef, useState } from "react";
import type { Stats } from "../data/types";
import { CORPUS_LABEL } from "../data/types";
import { int } from "../lib/format";
import {
  update,
  type Agreement,
  type ConfBand,
  type CorpusFilter,
  type JudgeFilter,
  type JudgeSource,
  type RaterFilter,
  type SliceState,
} from "../state/url";

type Props = { stats: Stats; state: SliceState; shown: number; total: number };

type Option<T extends string> = { value: T | ""; label: string };

function answerOptions(task: SliceState["task"]): Option<JudgeFilter>[] {
  if (task === "manipulation") {
    return [
      { value: "", label: "any" },
      { value: "yes", label: "yes" },
      { value: "no", label: "no" },
    ];
  }
  const binary =
    task === "hand_eq2"
      ? [
          { value: "yes" as const, label: "both hands" },
          { value: "no" as const, label: "fewer than two" },
        ]
      : [
          { value: "yes" as const, label: "at least one hand" },
          { value: "no" as const, label: "no hands" },
        ];
  return [
    { value: "", label: "any" },
    { value: "0", label: "0 hands" },
    { value: "1", label: "1 hand" },
    { value: "2", label: "2 hands" },
    ...binary,
  ];
}

export function Filters({ stats, state, shown, total }: Props): JSX.Element {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);
  useEffect(() => () => {
    if (timer.current !== null) window.clearTimeout(timer.current);
  }, []);

  const copy = async (): Promise<void> => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 1500);
    } catch {
      window.prompt("Copy this link", window.location.href);
    }
  };

  const judgeOptions = answerOptions(state.task);
  const raterOptions: Option<RaterFilter>[] = [
    ...answerOptions(state.task).map((o) => ({ value: o.value as RaterFilter | "", label: o.label })),
    { value: "labelled", label: "any human label" },
    { value: "unlabelled", label: "unlabelled" },
  ];

  return (
    <div className="filters" id="filters">
      <label className="filter">
        <span className="filter-label">corpus</span>
        <select
          className="filter-select"
          data-first-filter="true"
          value={state.corpus}
          onChange={(e) => update(state, { corpus: e.target.value as CorpusFilter, f: null })}
        >
          <option value="all">all</option>
          {stats.corpora.map((c) => (
            <option key={c} value={c}>
              {CORPUS_LABEL[c]}
            </option>
          ))}
        </select>
      </label>
      <label className="filter">
        <span className="filter-label">judge answer</span>
        <select
          className="filter-select"
          value={state.judge ?? ""}
          onChange={(e) => update(state, { judge: (e.target.value || null) as JudgeFilter | null, f: null })}
        >
          {judgeOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
          <option value="unparsed">could not parse</option>
        </select>
      </label>
      <label className="filter">
        <span className="filter-label">rater answer</span>
        <select
          className="filter-select"
          value={state.rater ?? ""}
          onChange={(e) => update(state, { rater: (e.target.value || null) as RaterFilter | null, f: null })}
        >
          {raterOptions.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </label>
      <label className="filter">
        <span className="filter-label">agreement</span>
        <select
          className="filter-select"
          value={state.agree ?? ""}
          onChange={(e) => update(state, { agree: (e.target.value || null) as Agreement | null, f: null })}
        >
          <option value="">any</option>
          <option value="agrees">agrees with rater</option>
          <option value="disagrees">disagrees with rater</option>
          <option value="none">no rater</option>
        </select>
      </label>
      <label className="filter">
        <span className="filter-label">confidence</span>
        <select
          className="filter-select"
          value={state.conf ?? ""}
          onChange={(e) => update(state, { conf: (e.target.value || null) as ConfBand | null, f: null })}
        >
          <option value="">any</option>
          <option value="ge99">≥ .99</option>
          <option value="90to99">.90 – .99</option>
          <option value="lt90">&lt; .90</option>
        </select>
      </label>
      <label className="filter">
        <span className="filter-label">judge</span>
        <select
          className="filter-select"
          value={state.src}
          onChange={(e) => update(state, { src: e.target.value as JudgeSource, f: null })}
        >
          <option value="qwen">{stats.generated_from.judge} {stats.generated_from.prompt_variant}</option>
          <option value="gemini">gemini stored</option>
        </select>
      </label>
      <button type="button" className="button" onClick={() => void copy()} aria-live="polite">
        {copied ? "copied" : "copy link"}
      </button>
      <span className="count" aria-live="polite">
        {int(shown)} of {int(total)} frames
      </span>
    </div>
  );
}
