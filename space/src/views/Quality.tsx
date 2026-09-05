import { useMemo } from "react";
import type { CalibrationBin, Frame, Stats } from "../data/types";
import { fixed, int, pct } from "../lib/format";
import { update, type Answer, type SliceState } from "../state/url";
import { repoFile } from "../data/types";

type Props = { stats: Stats; state: SliceState; onFilter: () => void
  frames: Frame[];
};

const HANDS: Answer[] = ["0", "1", "2"];
const YESNO: Answer[] = ["no", "yes"];

export function Quality({ stats, frames, state, onFilter }: Props): JSX.Element {
  const h4 = stats.agreement.h4;
  const intra = stats.agreement.intra_rater;
  const tr = stats.test_retest;
  const effort = useMemo(() => {
    const seconds = frames.filter((f) => f.r).map((f) => (f.r as NonNullable<Frame["r"]>).s).sort((a, b) => a - b);
    const mid = Math.floor(seconds.length / 2);
    return {
      n: seconds.length,
      minutes: seconds.reduce((a, b) => a + b, 0) / 60,
      median: seconds.length % 2 ? (seconds[mid] ?? 0) : ((seconds[mid - 1] ?? 0) + (seconds[mid] ?? 0)) / 2,
    };
  }, [frames]);
  const isHands = state.task !== "manipulation";
  const matrix = isHands ? stats.confusion.hands : stats.confusion.manipulation;
  const axis = isHands ? HANDS : YESNO;
  const stat = isHands ? h4.hand_count : h4.manipulation;
  const cal = isHands ? stats.calibration.hand_count : stats.calibration.manipulation;

  const cell = (judge: Answer, rater: Answer): void => {
    update(state, {
      corpus: "all",
      judge,
      rater,
      agree: null,
      conf: null,
      f: null,
      view: null,
    });
    onFilter();
  };

  return (
    <section className="section" id="quality" aria-labelledby="quality-title">
      <h2 className="section-title" id="quality-title">
        Quality
      </h2>
      <p className="section-lede">
        The {int(stats.confusion.n)} frames one rater labelled against the written rubric, set beside what the
        judge said about the same frames. Every count opens the frames behind it.
      </p>

      <div className="panels">
        <div className="panel">
          <h3 className="panel-title">Judge against rater — {isHands ? "hand count" : "manipulation"}</h3>
          <table className="table">
            <thead>
              <tr>
                <th className="table-th-left">judge ↓ / rater →</th>
                {axis.map((a) => (
                  <th className="table-th" key={a} scope="col">
                    {a}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {axis.map((j, ji) => (
                <tr key={j}>
                  <th className="table-th-left" scope="row">
                    {j}
                  </th>
                  {axis.map((r, ri) => {
                    const n = matrix[ji]?.[ri] ?? 0;
                    const off = ji !== ri;
                    if (n === 0) {
                      return (
                        <td className="table-td" key={r}>
                          <span className="cell-zero">0</span>
                        </td>
                      );
                    }
                    return (
                      <td className="table-td" key={r}>
                        <button
                          type="button"
                          className={off ? "cell-button cell-off" : "cell-button"}
                          onClick={() => cell(j, r)}
                        >
                          {n}
                        </button>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
          <p className="panel-note">
            AC1 {fixed(stat.ac1, 3)} (95% {stat.ci_method} CI {fixed(stat.lo, 3)}–{fixed(stat.hi, 3)}), κ{" "}
            {fixed(stat.kappa, 3)}, raw {pct(stat.raw)}%, n {int(stat.n)}. Intra-rater on the blind re-label: AC1{" "}
            {fixed(isHands ? intra.hand_count.ac1 : intra.manipulation.ac1, 3)} over{" "}
            {int(isHands ? intra.hand_count.n_pairs : intra.manipulation.n_pairs)} pairs — the rubric is decidable.
            The rater is the ground truth here; the judge is what is being measured.
          </p>
        </div>

        <div className="panel">
          <h3 className="panel-title">Judge confidence against being right</h3>
          <Reliability bins={cal.bins} />
          <p className="panel-note">
            ECE {fixed(cal.ece, 3)} over n {int(cal.n)}, {cal.confidence_kind} confidence. Greedy decoding
            (temperature 0) puts almost every frame in the top bin, so this is a weak curve by construction, not a
            limitation of the estimator. Empty bins are drawn empty, never merged away.{" "}
            <a className="footer-link" href={repoFile("docs/DECISIONS.md")}>
              {stats.provenance.calibration?.decision}
            </a>
          </p>
        </div>
      </div>

      <dl className="verdicts">
        <div className="verdict">
          <dt>repeatability, judge</dt>
          <dd>
            <strong>{fixed(tr.manipulation_self_agreement_rate, 3)}</strong>
            <span className="verdict-detail">
              {int(tr.n_frames)} frames × {tr.repeats_per_frame}, sampling unpinned
            </span>
          </dd>
        </div>
        <div className="verdict">
          <dt>repeatability, human</dt>
          <dd>
            <strong>{fixed(intra.manipulation.ac1, 3)}</strong>
            <span className="verdict-detail">AC1 over {int(intra.manipulation.n_pairs)} blind re-label pairs</span>
          </dd>
        </div>
        <div className="verdict">
          <dt>rater effort</dt>
          <dd>
            <strong>{int(Math.round(effort.minutes))} min</strong>
            <span className="verdict-detail">{int(effort.n)} labels, median {effort.median}s each</span>
          </dd>
        </div>
      </dl>

      <p className="panel-note">
        The judge repeats itself perfectly and is still wrong on{" "}
        {stats.confusion.manipulation[1]?.[0] ?? 0} frames. The human does not repeat herself perfectly and is still
        the ground truth. Repeatability is not accuracy — that distinction is why the{" "}
        {int(stats.generated_from.n_rater_labels)} labels exist.
      </p>

      <p className="panel-note">
        Domain bias, the experiment this project was built for: judge error on manipulation is{" "}
        {pct(stats.agreement.h5["egocentric-10k"].error_rate)}% on Egocentric-10K (n{" "}
        {int(stats.agreement.h5["egocentric-10k"].n)}) and {pct(stats.agreement.h5["epic-kitchens-100"].error_rate)}%
        on EPIC-KITCHENS-100 (n {int(stats.agreement.h5["epic-kitchens-100"].n)}) — reversed from the pre-registered
        prediction and underpowered at this size. Reported, not concluded.
      </p>
    </section>
  );
}

const W = 420;
const H = 200;
const PAD_L = 34;
const PAD_B = 28;

function Reliability({ bins }: { bins: CalibrationBin[] }): JSX.Element {
  const plotW = W - PAD_L - 8;
  const plotH = H - PAD_B - 8;
  const bw = plotW / bins.length;
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Reliability diagram">
      <line className="chart-axis" x1={PAD_L} x2={PAD_L} y1={8} y2={H - PAD_B} />
      <line className="chart-axis" x1={PAD_L} x2={W - 8} y1={H - PAD_B} y2={H - PAD_B} />
      <line className="chart-diag" x1={PAD_L} x2={W - 8} y1={H - PAD_B} y2={8} />
      {[0, 0.5, 1].map((v) => (
        <text className="chart-label" key={v} x={PAD_L - 6} y={H - PAD_B - v * plotH + 4} textAnchor="end">
          {v.toFixed(1)}
        </text>
      ))}
      {bins.map((b, i) => {
        const x = PAD_L + i * bw;
        if (b.n === 0 || b.accuracy === null) {
          return <rect className="bar-empty" key={b.lo} x={x + 1} y={H - PAD_B - 6} width={bw - 2} height={6} />;
        }
        const h = b.accuracy * plotH;
        return (
          <g key={b.lo}>
            <rect className="bar-signal" x={x + 1} y={H - PAD_B - h} width={bw - 2} height={h} />
            <text className="chart-value" x={x + bw / 2} y={H - PAD_B - h - 4} textAnchor="middle">
              {b.n}
            </text>
          </g>
        );
      })}
      <text className="chart-label" x={PAD_L} y={H - 8}>
        confidence 0
      </text>
      <text className="chart-label" x={W - 8} y={H - 8} textAnchor="end">
        1
      </text>
    </svg>
  );
}
