// One claim, three ways of knowing it.
//
// The caliper this replaces animated a confidence interval closing, which implies the interval
// is arriving rather than being a fixed property of a finished computation, and it gave the
// published figure a visual class of its own. Here the vendor's number sits on the same axis as
// everything else and simply has no whisker.
import { useMemo } from "react";
import { Forest, type ForestRow } from "../charts/Forest";
import { ChartFrame } from "../charts/Chart";
import { JUDGE, MEASURED, PUBLISHED } from "../charts/theme";
import type { Corpus, Frame, Stats, Task } from "../data/types";
import { CORPUS_LABEL, TASKS, TASK_LABEL, repoFile } from "../data/types";
import { fixed, int, pct, pctSpan } from "../lib/format";
import { reasonCounts } from "../state/slice";
import { update, type SliceState } from "../state/url";

type Props = { stats: Stats; frames: Frame[]; state: SliceState; onReason: () => void };

export function heroCorpus(state: SliceState): Corpus {
  return state.corpus === "all" ? "egocentric-10k" : state.corpus;
}

export function Hero({ stats, frames, state, onReason }: Props): JSX.Element {
  const corpus = heroCorpus(state);
  const task = state.task;
  const published = stats.published[corpus]?.[task];
  const alone = stats.judge_alone[corpus];
  const naive = alone ? alone[task] : undefined;
  const ppi = stats.ppi[corpus]?.[task];
  // The replication: same protocol, 10,000 frames, no human correction. It is the best-powered
  // comparison on the page, so it is the one the headline makes -- not the PPI estimate, which
  // rests on 33 human labels and carries a 21-point interval.
  const rep = stats.h1[corpus]?.tasks[task];
  const tol = stats.h1[corpus]?.tolerance_pp;
  const repN = stats.h1[corpus]?.n;
  const counts = useMemo(() => reasonCounts(frames, state), [frames, state]);

  const setTask = (next: Task): void =>
    update(state, { task: next, judge: null, rater: null, agree: null, f: null });
  const setCorpus = (next: Corpus): void => update(state, { corpus: next, f: null });
  const reason = (patch: Partial<SliceState>): void => {
    update(state, { judge: null, rater: null, agree: null, conf: null, f: null, ...patch });
    onReason();
  };

  const rows: ForestRow[] = [];
  if (typeof published === "number") {
    rows.push({
      label: "Build AI published",
      point: published,
      colour: PUBLISHED,
      // The one mark on this page you cannot open. That is the whole argument, as an affordance.
      note: "no sample: this figure ships without one",
    });
  }
  if (rep) {
    rows.push({
      label: `Reproduced, n ${int(repN ?? 0)}`,
      point: rep.observed,
      colour: JUDGE,
      note: `same protocol, no human correction · ${fixed(rep.diff_pp, 2)} pp from published`,
    });
  }
  if (naive) {
    rows.push({
      label: `Judge alone, n ${int(naive.n)}`,
      point: naive.rate,
      colour: JUDGE,
      note: alone ? `${alone.judge} ${alone.prompt_variant} on ${alone.sample}` : undefined,
      onSelect: () => reason({ corpus, judge: "yes" }),
    });
  }
  if (ppi) {
    rows.push({
      label: `Human-anchored, ${ppi.method}`,
      point: ppi.value,
      ci: [ppi.lo, ppi.hi],
      colour: MEASURED,
      note: `n gold ${int(ppi.n_gold)}, n judged ${int(ppi.n_judged)}`,
      onSelect: () => reason({ corpus, rater: "labelled" }),
    });
  }

  return (
    <section className="hero" aria-labelledby="hero-title" data-fade data-delay="1">
      <p className="eyebrow">vernier · an independent measurement</p>
      <h1 className="hero-title" id="hero-title">
        {typeof published === "number" ? `Published ${pct(published)}%.` : "Published, unmeasured."}{" "}
        {rep
          ? `Reproduced ${pct(rep.observed)}%.`
          : naive
            ? `Independently ${pct(naive.rate)}%.`
            : "No independent run here."}
      </h1>
      <p className="hero-deck">
        Build AI&apos;s {TASK_LABEL[task]} figure for {CORPUS_LABEL[corpus]}, re-run with an open
        judge on{" "}
        {rep && repN ? `${int(repN)} frames` : naive ? `${int(naive.n)} frames` : "the gold sets"}
        {rep && typeof tol === "number" ? (
          rep.within_tolerance ? (
            <>
              {" "}
              — a {fixed(rep.diff_pp, 2)} pp difference, inside the ±{fixed(tol, 0)} pp tolerance
              fixed before any frame was fetched.
            </>
          ) : (
            <>
              {" "}
              — a {fixed(rep.diff_pp, 2)} pp difference, outside the ±{fixed(tol, 0)} pp tolerance
              fixed before any frame was fetched, and the same gap appears on the other release.
            </>
          )
        ) : (
          "."
        )}{" "}
        Below, what {int(stats.generated_from.n_rater_labels)} human labels do to it, and the
        interval that was never published.
      </p>

      <ChartFrame
        caption={
          ppi ? (
            <>
              95% CI {pctSpan(ppi.lo, ppi.hi)} · n gold {int(ppi.n_gold)} · n judged{" "}
              {int(ppi.n_judged)} · n unlabelled {int(ppi.n_unlabelled)} · {ppi.method} ·{" "}
              <a className="footer-link" href={repoFile(stats.provenance["ppi"]?.claim_ref ?? "")}>
                {stats.provenance["ppi"]?.decision}
              </a>
              . The published figure has no whisker because it was never given one.
            </>
          ) : (
            <>
              No human gold on this slice, so there is no corrected estimate and no interval —
              only what the vendor published and what an open judge says about the same frames.
              {task === "hand_eq2"
                ? " The 2-hands figure has no PPI estimate on any corpus, which is worth knowing: it is the one figure that misses tolerance on both releases."
                : ""}
            </>
          )
        }
      >
        <div className="chart-controls">
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
            <select
              className="select"
              value={corpus}
              onChange={(e) => setCorpus(e.target.value as Corpus)}
            >
              {stats.corpora.map((c) => (
                <option key={c} value={c}>
                  {CORPUS_LABEL[c]}
                </option>
              ))}
            </select>
          </label>
        </div>
        <Forest rows={rows} labelWidth={150} />
      </ChartFrame>

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
