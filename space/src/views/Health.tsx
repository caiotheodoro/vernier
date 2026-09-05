import type { Run, Stats } from "../data/types";
import { hours, int, seconds, usd } from "../lib/format";

type Props = { stats: Stats };

const W = 640;
const H = 96;
const PAD_L = 8;

export function Health({ stats }: Props): JSX.Element {
  const h = stats.health;
  // All 600 gold calls, and provably the array the percentiles below were computed from.
  // This used to be `runs.find(...)` -- the first run's 200 -- under a caption saying 600.
  const latencies = h.gold_calls.latency_ms;

  return (
    <section className="section" id="health" aria-labelledby="health-title">
      <h2 className="section-title" id="health-title">
        Pipeline health
      </h2>
      <p className="section-lede">
        Every live judge run behind the numbers above: what was asked for, what came back, what it cost. Judge time is
        summed per-call latency, not wall time — the runs were concurrent.
      </p>

      <p className="panel-note">
        {int(h.e2_frames)} frames, both prompt arms: {usd(h.e2_cost_both_arms_usd)},{" "}
        {hours(h.e2_judge_time_both_arms_h)} of judge time. That is the price of re-running this measurement on a
        batch you are about to buy.
      </p>

      <table className="table">
        <thead>
          <tr>
            <th className="table-th-left">run</th>
            <th className="table-th-left">sample</th>
            <th className="table-th">requested</th>
            <th className="table-th">ok</th>
            <th className="table-th">cost</th>
            <th className="table-th-left">non-ok</th>
          </tr>
        </thead>
        <tbody>
          {stats.runs.map((r: Run) => {
            const bad = Object.entries(r.status_counts ?? {}).filter(([k]) => k !== "ok");
            return (
              <tr key={r.id}>
                <td className="table-td-left">{r.id}</td>
                <td className="table-td-left">{r.sample}</td>
                <td className="table-td">{int(r.n_requested)}</td>
                <td className="table-td">{r.n_ok === null ? "—" : int(r.n_ok)}</td>
                <td className="table-td">{r.cost_usd === null ? "—" : usd(r.cost_usd)}</td>
                <td className="table-td-left">
                  {bad.length === 0 ? <span className="cell-zero">none</span> : bad.map(([k, v]) => `${v} ${k}`).join(", ")}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {latencies.length > 0 ? (
        <>
          <h3 className="panel-title">Latency, the {int(h.gold_calls.n)} gold-set calls</h3>
          <Strip values={latencies} max={h.gold_calls.max_ms} />
          <p className="panel-note">
            p50 {seconds(h.gold_calls.p50_ms)}, p95 {seconds(h.gold_calls.p95_ms)}, max{" "}
            {seconds(h.gold_calls.max_ms)}. The one call at the far right is a preemption on spot capacity, retried and
            answered — visible because per-call latency is recorded, not averaged away.
          </p>
        </>
      ) : null}
    </section>
  );
}

function Strip({ values, max }: { values: number[]; max: number }): JSX.Element {
  const plotW = W - PAD_L * 2;
  const scale = (v: number): number => PAD_L + (Math.log10(Math.max(1, v)) / Math.log10(Math.max(10, max))) * plotW;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Per-call latency, log scale">
      <line className="chart-axis" x1={PAD_L} x2={W - PAD_L} y1={H - 26} y2={H - 26} />
      {values.map((v, i) => (
        <circle
          className={v > 60_000 ? "dot-signal" : "dot-steel"}
          key={`${v}-${i}`}
          cx={scale(v)}
          cy={H - 26 - 8 - ((i * 37) % 34)}
          r={2}
        />
      ))}
      {[1_000, 10_000, 100_000].map((v) => (
        <g key={v}>
          <line className="chart-tick" x1={scale(v)} x2={scale(v)} y1={H - 30} y2={H - 22} />
          <text className="chart-label" x={scale(v)} y={H - 8} textAnchor="middle">
            {v / 1000} s
          </text>
        </g>
      ))}
    </svg>
  );
}
