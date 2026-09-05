import type { Corpus, Stats, Task } from "../data/types";
import { CORPUS_LABEL } from "../data/types";
import { fixed, int, pct } from "../lib/format";
import type { SliceState } from "../state/url";

type Props = { stats: Stats; state: SliceState };

const W = 640;
const ROW_H = 46;
const PAD_L = 168;
const PAD_R = 16;

export function Coverage({ stats, state }: Props): JSX.Element {
  const task: Task = state.task;
  const corpora = stats.corpora.filter((c) => stats.coverage[c]);
  const H = corpora.length * ROW_H + 34;
  const barW = W - PAD_L - PAD_R;

  return (
    <section className="section" id="coverage" aria-labelledby="coverage-title">
      <h2 className="section-title" id="coverage-title">
        Coverage
      </h2>
      <p className="section-lede">
        What the judge said about every frame it saw, per corpus. The tick is the figure the vendor published;
        the span below it is what vernier measured once human gold corrected the judge, where gold exists. Bars are{" "}
        {task === "manipulation" ? "manipulation yes/no" : "hand count 0 / 1 / 2"}.
      </p>

      <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Per-corpus label distribution">
        {corpora.map((corpus, i) => {
          const cov = stats.coverage[corpus];
          if (!cov) return null;
          const y = 16 + i * ROW_H;
          const segments =
            task === "manipulation"
              ? [
                  { n: cov.manipulation[0], label: "no", cls: "bar-steel" },
                  { n: cov.manipulation[1], label: "yes", cls: "bar-signal" },
                ]
              : [
                  { n: cov.hands[0], label: "0", cls: "bar-steel" },
                  { n: cov.hands[1], label: "1", cls: "bar-ink" },
                  { n: cov.hands[2], label: "2", cls: "bar-signal" },
                ];
          const total = segments.reduce((a, s) => a + s.n, 0) || 1;
          let x = PAD_L;
          const published = stats.published[corpus]?.[task];
          const ppi = stats.ppi[corpus]?.[task];
          return (
            <g key={corpus}>
              <text className="chart-label" x={PAD_L - 8} y={y + 16} textAnchor="end">
                {CORPUS_LABEL[corpus]}
              </text>
              {segments.map((s) => {
                const w = (s.n / total) * barW;
                const rect = (
                  <g key={s.label}>
                    <rect className={s.cls} x={x} y={y} width={Math.max(0, w - 1)} height={22} />
                    {w > 42 ? (
                      <text className="bar-label" x={x + 6} y={y + 15}>
                        {s.label} {int(s.n)}
                      </text>
                    ) : null}
                  </g>
                );
                x += w;
                return rect;
              })}
              {typeof published === "number" ? (
                <line
                  className="chart-tick"
                  x1={PAD_L + published * barW}
                  x2={PAD_L + published * barW}
                  y1={y - 4}
                  y2={y + 26}
                />
              ) : null}
              {ppi ? (
                <g>
                  <line
                    className="scale-jaw-bar"
                    x1={PAD_L + ppi.lo * barW}
                    x2={PAD_L + ppi.hi * barW}
                    y1={y + 30}
                    y2={y + 30}
                  />
                  <circle className="scale-dot" cx={PAD_L + ppi.value * barW} cy={y + 30} r={3} />
                </g>
              ) : null}
            </g>
          );
        })}
      </svg>

      <table className="table">
        <thead>
          <tr>
            <th className="table-th-left">corpus</th>
            <th className="table-th">published</th>
            <th className="table-th">judge alone</th>
            <th className="table-th">measured (95% CI)</th>
            <th className="table-th">n judged</th>
          </tr>
        </thead>
        <tbody>
          {corpora.map((corpus: Corpus) => {
            const published = stats.published[corpus]?.[task];
            const alone = stats.judge_alone[corpus];
            const ppi = stats.ppi[corpus]?.[task];
            return (
              <tr key={corpus}>
                <td className="table-td-left">{CORPUS_LABEL[corpus]}</td>
                <td className="table-td">{typeof published === "number" ? `${pct(published)}%` : "—"}</td>
                <td className="table-td">{alone ? `${pct(alone[task].rate)}%` : "—"}</td>
                <td className="table-td">
                  {ppi ? `${pct(ppi.value)}% (${pct(ppi.lo)}–${pct(ppi.hi)})` : "no human gold"}
                </td>
                <td className="table-td">{alone ? int(alone[task].n) : "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <p className="panel-note">
        Build AI's evaluation frames ship no worker id ({stats.provenance.no_worker_ids?.decision}), so no interval
        here is clustered and each is a lower bound on its true width. How much of one is now measured rather than
        guessed: on vernier's own draws from the same corpus, clustering by worker widens an interval by{" "}
        {fixed(stats.h2.cluster_width_excess_pct.lo, 0)}–{fixed(stats.h2.cluster_width_excess_pct.hi, 0)}% (see
        below). Prompt sensitivity over{" "}
        {int(stats.prompt_sweep.n)} frames: hand count moves {fixed(stats.prompt_sweep.hand_count_spread_pp, 2)} pp
        across {Object.keys(stats.prompt_sweep.hand_count).length} prompt variants, manipulation{" "}
        {fixed(stats.prompt_sweep.manipulation_spread_pp, 2)} pp across{" "}
        {Object.keys(stats.prompt_sweep.manipulation).length}.
      </p>
    </section>
  );
}
