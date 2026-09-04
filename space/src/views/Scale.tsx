// The caliper hero: published figure in ink, judge-alone tick in steel, vernier's PPI++
// estimate as signal jaws that close onto the interval on load.
import { useMemo } from "react";
import type { Corpus, Frame, PpiEntry, Stats, Task } from "../data/types";
import { CORPUS_LABEL, TASKS, TASK_LABEL } from "../data/types";
import { int, pct, pctSpan } from "../lib/format";
import { useEaseIn, useWidth } from "../lib/hooks";
import { reasonCounts } from "../state/slice";
import { update, type SliceState } from "../state/url";

type Props = { stats: Stats; frames: Frame[]; state: SliceState; onReason: () => void };

const H = 168;
const AXIS_Y = 92;
const PAD = 28;

export function heroCorpus(state: SliceState): Corpus {
  return state.corpus === "all" ? "egocentric-10k" : state.corpus;
}

export function Scale({ stats, frames, state, onReason }: Props): JSX.Element {
  const [ref, width] = useWidth<HTMLDivElement>();
  const corpus = heroCorpus(state);
  const task = state.task;
  const published = stats.published[corpus]?.[task];
  const alone = stats.judge_alone[corpus];
  const naive = alone ? alone[task] : undefined;
  const ppi = stats.ppi[corpus]?.[task];
  const key = `${corpus}:${task}`;
  const t = useEaseIn(key, 600);
  const counts = useMemo(() => reasonCounts(frames, state), [frames, state]);

  const values = [published, naive?.rate, ppi?.lo, ppi?.hi, ppi?.value].filter(
    (v): v is number => typeof v === "number",
  );
  const lo = Math.max(0, Math.floor(Math.min(...values) * 100 - 5));
  const hi = Math.min(100, Math.ceil(Math.max(...values) * 100 + 5));
  const w = Math.max(320, width);
  const x = (v: number): number => PAD + ((v * 100 - lo) / (hi - lo)) * (w - 2 * PAD);
  const clampX = (px: number, half: number): number => Math.min(w - PAD - half, Math.max(PAD + half, px));

  const ticks: number[] = [];
  for (let v = lo; v <= hi; v += 1) ticks.push(v);
  const labelEvery = w < 560 ? 10 : 5;

  const jawLo = ppi ? x(lo / 100) + (x(ppi.lo) - x(lo / 100)) * t : 0;
  const jawHi = ppi ? x(hi / 100) + (x(ppi.hi) - x(hi / 100)) * t : 0;

  const setTask = (next: Task): void => update(state, { task: next, judge: null, rater: null, agree: null, f: null });
  const setCorpus = (next: Corpus): void => update(state, { corpus: next, f: null });
  const reason = (patch: Partial<SliceState>): void => {
    update(state, { judge: null, rater: null, agree: null, conf: null, f: null, ...patch });
    onReason();
  };

  return (
    <section className="hero" aria-labelledby="hero-title">
      <div className="hero-head">
        <h2 className="hero-title" id="hero-title">
          {capitalize(TASK_LABEL[task])}, {CORPUS_LABEL[corpus]}
        </h2>
        <div className="hero-controls">
          <label className="select-label">
            task
            <select className="select" value={task} onChange={(e) => setTask(e.target.value as Task)}>
              {TASKS.map((tk) => (
                <option key={tk} value={tk}>
                  {TASK_LABEL[tk]}
                </option>
              ))}
            </select>
          </label>
          <label className="select-label">
            corpus
            <select className="select" value={corpus} onChange={(e) => setCorpus(e.target.value as Corpus)}>
              {stats.corpora.map((c) => (
                <option key={c} value={c}>
                  {CORPUS_LABEL[c]}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="scale-wrap" ref={ref}>
        <svg
          className="scale-svg"
          width={w}
          height={H}
          viewBox={`0 0 ${w} ${H}`}
          role="img"
          aria-label={scaleAria(published, naive?.rate, ppi)}
        >
          <line className="scale-axis" x1={PAD} x2={w - PAD} y1={AXIS_Y} y2={AXIS_Y} />
          {ticks.map((v) => {
            const major = v % 5 === 0;
            const labelled = v % labelEvery === 0;
            return (
              <g key={v}>
                <line className="scale-tick" x1={x(v / 100)} x2={x(v / 100)} y1={AXIS_Y} y2={AXIS_Y + (major ? 8 : 4)} />
                {labelled ? (
                  <text className="scale-tick-label" x={x(v / 100)} y={AXIS_Y + 22} textAnchor="middle">
                    {v}
                  </text>
                ) : null}
              </g>
            );
          })}

          {typeof published === "number" ? (
            <g>
              <polygon
                className="scale-published"
                points={`${x(published) - 6},${AXIS_Y - 20} ${x(published) + 6},${AXIS_Y - 20} ${x(published)},${AXIS_Y - 8}`}
              />
              <text className="scale-label-ink" x={clampX(x(published), 44)} y={AXIS_Y - 28} textAnchor="middle">
                published {pct(published)}
              </text>
            </g>
          ) : null}

          {naive ? (
            <g>
              <line className="scale-naive" x1={x(naive.rate)} x2={x(naive.rate)} y1={AXIS_Y - 14} y2={AXIS_Y + 2} />
              <text className="scale-label-steel" x={clampX(x(naive.rate), 48)} y={AXIS_Y + 40} textAnchor="middle">
                judge alone {pct(naive.rate)}
              </text>
            </g>
          ) : null}

          {ppi ? (
            <g>
              <line className="scale-jaw-bar" x1={jawLo} x2={jawHi} y1={AXIS_Y} y2={AXIS_Y} />
              <line className="scale-jaw" x1={jawLo} x2={jawLo} y1={AXIS_Y - 12} y2={AXIS_Y + 12} />
              <line className="scale-jaw" x1={jawHi} x2={jawHi} y1={AXIS_Y - 12} y2={AXIS_Y + 12} />
              <circle className="scale-dot" cx={x(ppi.value)} cy={AXIS_Y} r={5} />
              <text className="scale-label-ink" x={clampX(x(ppi.value), 120)} y={AXIS_Y + 60} textAnchor="middle">
                measured {pct(ppi.value)}, {Math.round(ppi.level * 100)}% CI {pctSpan(ppi.lo, ppi.hi)}
              </text>
            </g>
          ) : null}
        </svg>
      </div>

      <p className="scale-sentence">
        {ppi ? (
          <>
            n gold {int(ppi.n_gold)}, n judged {int(ppi.n_judged)}, {ppi.method}, {ppi.judge} {ppi.prompt_variant}.
            {!ppi.clustered && ppi.why_not_clustered ? (
              <> Not clustered, so the interval is a lower bound on true width: {ppi.why_not_clustered}.</>
            ) : null}
          </>
        ) : (
          <>
            No human gold on this slice.
            {naive && alone ? ` Judge alone: ${alone.judge} ${alone.prompt_variant} on ${alone.sample}, n ${int(naive.n)}.` : ""}
            {typeof published !== "number" ? " No published figure for this task and corpus." : ""}
          </>
        )}
      </p>

      {corpus !== "egocentric-100k" ? (
        <ul className="reasons">
          <li className="reason">
            <ReasonLink
              n={counts.judgeYesRaterNo}
              text="where the judge said yes and the rater said no"
              onClick={() => reason({ judge: "yes", rater: "no" })}
            />
          </li>
          <li className="reason">
            <ReasonLink
              n={counts.judgeNoRaterYes}
              text="where the judge said no and the rater said yes"
              onClick={() => reason({ judge: "no", rater: "yes" })}
            />
          </li>
          <li className="reason">
            <ReasonLink n={counts.unparsed} text="the judge could not parse" onClick={() => reason({ judge: "unparsed" })} />
          </li>
        </ul>
      ) : null}
    </section>
  );
}

function ReasonLink({ n, text, onClick }: { n: number; text: string; onClick: () => void }): JSX.Element {
  const label = `${int(n)} ${n === 1 ? "frame" : "frames"} ${text}`;
  if (n === 0) return <span className="reason-none">{label}</span>;
  return (
    <button type="button" className="reason-link" onClick={onClick}>
      {label} <span aria-hidden="true">→</span>
    </button>
  );
}

function scaleAria(published: number | undefined, naive: number | undefined, ppi: PpiEntry | undefined): string {
  const parts: string[] = [];
  if (typeof published === "number") parts.push(`published ${pct(published)}`);
  if (typeof naive === "number") parts.push(`judge alone ${pct(naive)}`);
  if (ppi) parts.push(`measured ${pct(ppi.value)}, 95% CI ${pctSpan(ppi.lo, ppi.hi)}`);
  return parts.join("; ");
}

function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}
