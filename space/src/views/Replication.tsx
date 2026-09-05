// H1 and H2, side by side in argument if not in layout.
//
// Three independent measurements single out the same figure. Build AI's 2-hands number misses
// the pre-registered tolerance on the 10K release and again on the 100K one, and it carries the
// largest design effect on both H2 arms. The card records that convergence in words and calls it
// "recorded, not explained"; this is where it is drawn.
import { Bars } from "../charts/Bars";
import { ChartFrame } from "../charts/Chart";
import { Forest, type ForestRow } from "../charts/Forest";
import { JUDGE, PUBLISHED } from "../charts/theme";
import type { Stats, Task } from "../data/types";
import { CORPUS_LABEL, TASK_LABEL, repoFile } from "../data/types";
import { fixed, int } from "../lib/format";

const H2_TASK_LABEL: Record<string, string> = {
  hand_ge1: TASK_LABEL.hand_count,
  hand_eq2: TASK_LABEL.hand_eq2,
  active_manipulation: TASK_LABEL.manipulation,
};

export function Replication({ stats }: { stats: Stats }): JSX.Element {
  const h1 = stats.h1["egocentric-10k"];
  const h1b = stats.h1["egocentric-100k"];
  const h2 = stats.h2;
  const arm = h2.arms["S10k-S"] ?? Object.values(h2.arms)[0];

  const worst = h1
    ? (Object.entries(h1.tasks) as [Task, (typeof h1.tasks)[Task]][])
        .filter(([, v]) => !v.within_tolerance)
        .map(([t]) => t)
    : [];

  const bars = h1
    ? (Object.keys(h1.tasks) as Task[]).map((task) => ({
        label: TASK_LABEL[task],
        published: h1.tasks[task].published,
        observed: h1.tasks[task].observed,
      }))
    : [];

  const forest: ForestRow[] = arm
    ? Object.entries(arm.tasks).reverse().flatMap(([task, v]) => [
        {
          label: `${H2_TASK_LABEL[task] ?? task} · iid`,
          point: v.point_estimate,
          ci: [v.iid.lo, v.iid.hi] as [number, number],
          colour: PUBLISHED,
          note: "the interval this project reported before H2",
        },
        {
          label: `${H2_TASK_LABEL[task] ?? task} · cluster`,
          point: v.point_estimate,
          ci: [v.cluster.lo, v.cluster.hi] as [number, number],
          colour: JUDGE,
          note: `design effect ${fixed(v.design_effect, 2)}`,
        },
      ])
    : [];

  return (
    <>
      <section className="section" id="replication" aria-labelledby="replication-title" data-fade data-delay="1">
        <span className="watermark" aria-hidden="true">
          H1
        </span>
        <h2 className="section-title" id="replication-title">
          Does the published number reproduce?
        </h2>
        <p className="section-lede">
          The same protocol Build AI describes, run against {int(h1?.n ?? 0)} frames with an open judge, set beside
          what they published. The tolerance was fixed in the pre-registration before any frame was fetched:{" "}
          ±{fixed(h1?.tolerance_pp ?? 2, 0)} pp, and all three had to hold.
        </p>

        {h1 ? (
          <ChartFrame
            caption={
              <>
                {CORPUS_LABEL["egocentric-10k"]}, P0a, n {int(h1.n)} ·{" "}
                <a className="footer-link" href={repoFile(stats.provenance["h1"]?.claim_ref ?? "")}>
                  {stats.provenance["h1"]?.decision}
                </a>
                . These 10,000 frames are aggregates: they are not in the grid above, so nothing here opens.
              </>
            }
          >
            <Bars
              data={bars}
              series={[
                { key: "published", label: "Build AI published", colour: PUBLISHED },
                { key: "observed", label: "qwen3-vl, 10,000 frames", colour: JUDGE },
              ]}
              domain={[0.7, 1]}
            />
          </ChartFrame>
        ) : null}

        <dl className="verdicts">
          {h1
            ? (Object.keys(h1.tasks) as Task[]).map((task) => {
                const a = h1.tasks[task];
                const b = h1b?.tasks[task];
                return (
                  <div className="verdict" key={task}>
                    <dt>{TASK_LABEL[task]}</dt>
                    <dd>
                      <strong>{a.within_tolerance ? "within" : "outside"} tolerance</strong>
                      <span className="verdict-detail">
                        10K {fixed(a.diff_pp, 2)} pp
                        {b ? ` · 100K ${fixed(b.diff_pp, 2)} pp` : ""}
                      </span>
                    </dd>
                  </div>
                );
              })
            : null}
        </dl>

        <p className="panel-note">
          {worst.length === 1 && worst[0] ? (
            <>
              One figure misses, and the pre-registered rule was that all three had to hold — so H1 does not hold.
              It is <strong>{TASK_LABEL[worst[0]]}</strong>, it misses on the superseded release and again on the
              current one, and the section below shows it is also the figure clustering hurts most. Three
              measurements, one dimension. The measurement card records that convergence and does not explain it.
            </>
          ) : (
            "Reported against the pre-registered tolerance, not rescoped to fit the result."
          )}
        </p>
      </section>

      <section className="section" id="interval-width" aria-labelledby="width-title" data-fade data-delay="1">
        <span className="watermark" aria-hidden="true">
          H2
        </span>
        <h2 className="section-title" id="width-title">
          How wide should the interval be?
        </h2>
        <p className="section-lede">
          Frames from one worker are not independent observations. Every interval on this page is iid, because Build
          AI&apos;s evaluation frames ship no worker id at all — so this was measured on vernier&apos;s own draws from
          the same corpus, where the ids exist.
        </p>

        {arm ? (
          <ChartFrame
            caption={
              <>
                {int(arm.clusters.n_clusters)} worker clusters over {int(arm.clusters.n_observations)} observations,
                mean {fixed(arm.clusters.mean_cluster_size, 2)}, max {int(arm.clusters.max_cluster_size)}. B ={" "}
                {int(h2.B)}, seed {h2.seed} ·{" "}
                <a className="footer-link" href={repoFile(stats.provenance["h2"]?.claim_ref ?? "")}>
                  {stats.provenance["h2"]?.decision}
                </a>
              </>
            }
          >
            {/* The rail shows interval width, not the point: both rows of a pair share the
              point, and this section is about how far apart the jaws sit. */}
          <Forest
            rows={forest}
            labelWidth={190}
            railValue={(row) => (row.ci ? `${fixed((row.ci[1] - row.ci[0]) * 100, 2)} pp` : "")}
            railWidth={62}
          />
          </ChartFrame>
        ) : null}

        <p className="panel-note">
          H2 was pre-registered as a design effect of at least {fixed(h2.threshold, 0)}. Measured:{" "}
          {fixed(h2.design_effect_min, 2)} to {fixed(h2.design_effect_max, 2)} across two arms and three tasks, so{" "}
          <strong>H2 does not hold</strong>. What is nonetheless true is that every figure exceeds 1: an iid interval
          on this corpus is genuinely too narrow, by{" "}
          {fixed(h2.iid_width_understatement_pct.lo, 0)}–{fixed(h2.iid_width_understatement_pct.hi, 0)}% in width,
          equivalently the cluster-aware interval is{" "}
          {fixed(h2.cluster_width_excess_pct.lo, 0)}–{fixed(h2.cluster_width_excess_pct.hi, 0)}% wider, rather than
          the ≥41% H2 asserted. No interval above has been widened by that factor — rescaling a published interval
          would be an estimator nobody pre-registered. The number is reported; the correction is not applied.
        </p>
      </section>
    </>
  );
}
