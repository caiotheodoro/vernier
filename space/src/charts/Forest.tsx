// A point estimate and its interval, one row per way of knowing the number.
//
// This replaces the caliper the Space opened with. A forest plot *is* a caliper -- a point with
// jaws on a horizontal scale -- but it puts the vendor's figure on the same axis as the
// measurement instead of in a class of its own above it, and then that row has no whisker. A
// bare dot in a column of intervals is the strongest single frame this page can draw.
import { CartesianGrid, Cell, ComposedChart, ErrorBar, Scatter, XAxis, YAxis } from "recharts";
import { ChartBox, ChartTooltip, TooltipBody, axisProps, gridProps } from "./Chart";
import { T, fmt } from "./theme";

export type ForestRow = {
  label: string;
  point: number;
  ci?: [number, number] | undefined;
  colour: string;
  note?: string | undefined;
  /** Rows with no frames behind them on this page are not clickable, and say why. */
  onSelect?: (() => void) | undefined;
};

type Props = {
  rows: ForestRow[];
  /** Left axis width; widen for two-part labels like "hand >= 1 - cluster". */
  labelWidth?: number;
  domain?: [number, number];
  /**
   * What the right-hand value rail shows. Defaults to the point estimate. Where two rows share
   * a point and differ only in their interval, showing the point twice reads as a rendering
   * fault -- pass the interval width instead, which is what such a chart is about.
   */
  railValue?: (row: ForestRow) => string;
  /** Widen when the rail carries a unit, not just a number. */
  railWidth?: number;
};

export function Forest({ rows, labelWidth = 132, domain, railValue, railWidth = 46 }: Props): JSX.Element {
  const data = rows.map((r) => ({
    label: r.label,
    point: r.point,
    // Recharts' ErrorBar takes offsets from the point, not absolute bounds.
    err: r.ci ? [r.point - r.ci[0], r.ci[1] - r.point] : [0, 0],
    lo: r.ci?.[0],
    hi: r.ci?.[1],
    fill: r.colour,
    note: r.note,
  }));
  const values = data.flatMap((d) => [d.lo ?? d.point, d.hi ?? d.point]);
  const pad = (Math.max(...values) - Math.min(...values) || 0.1) * 0.18;
  const span: [number, number] = domain ?? [
    Math.max(0, Math.min(...values) - pad),
    Math.min(1, Math.max(...values) + pad),
  ];
  const valueByLabel = Object.fromEntries(
    rows.map((r) => [r.label, railValue ? railValue(r) : fmt(r.point)]),
  );

  return (
    <ChartBox height={46 * data.length + 72}>
      <ComposedChart data={data} layout="vertical" margin={{ top: 14, right: 16, bottom: 18, left: 4 }}>
        <CartesianGrid yAxisId="rows" {...gridProps} horizontal={false} />
        <XAxis type="number" domain={span} tickMargin={8} {...axisProps} tickFormatter={fmt} />
        <YAxis
          yAxisId="rows"
          type="category"
          dataKey="label"
          width={labelWidth}
          interval={0}
          tickMargin={4}
          {...axisProps}
          axisLine={false}
        />
        {/* The same categorical axis mirrored right, its ticks showing the estimate: a value
            column, not a second scale. Every mark is directly labelled. */}
        <YAxis
          yAxisId="values"
          orientation="right"
          type="category"
          dataKey="label"
          width={railWidth}
          interval={0}
          tickMargin={2}
          {...axisProps}
          axisLine={false}
          tick={{ fill: T.ink, fontSize: 11, fontFamily: T.font, fontWeight: 600 }}
          tickFormatter={(l: string) => valueByLabel[l] ?? ""}
        />
        <ChartTooltip
          cursor={{ fill: T.bgSubtle }}
          content={
            <TooltipBody
              format={fmt}
              extra={(d) =>
                d["lo"] != null ? (
                  <div className="chart-tooltip-extra">
                    95% CI [{fmt(d["lo"] as number)}, {fmt(d["hi"] as number)}]
                    {d["note"] ? ` · ${String(d["note"])}` : ""}
                  </div>
                ) : d["note"] ? (
                  <div className="chart-tooltip-extra">{String(d["note"])}</div>
                ) : null
              }
            />
          }
        />
        <Scatter yAxisId="rows" dataKey="point" name="share of frames" isAnimationActive={false}>
          {data.map((d, i) => (
            <Cell
              key={i}
              fill={d.fill}
              stroke={T.bg}
              strokeWidth={2}
              cursor={rows[i]?.onSelect ? "pointer" : "default"}
              onClick={rows[i]?.onSelect}
            />
          ))}
          <ErrorBar dataKey="err" direction="x" width={5} strokeWidth={2} stroke={T.muted} />
        </Scatter>
      </ComposedChart>
    </ChartBox>
  );
}
