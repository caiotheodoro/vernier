// Two series over shared categories. Every bar carries its value 6px past its end, drawn
// explicitly so a zero-width bar still reads as "0" rather than as missing data.
import { Bar, BarChart, CartesianGrid, LabelList, XAxis, YAxis } from "recharts";
import { ChartBox, ChartTooltip, TooltipBody, axisProps, gridProps } from "./Chart";
import { T, fmt } from "./theme";

export type BarSeries = { key: string; label: string; colour: string };

function ValueLabel(props: { x?: number; y?: number; width?: number; height?: number; value?: number }): JSX.Element | null {
  const { x = 0, y = 0, width = 0, height = 0, value } = props;
  if (typeof value !== "number") return null;
  return (
    <text
      x={x + width + 6}
      y={y + height / 2}
      dominantBaseline="central"
      style={{ fill: T.muted, fontSize: 11, fontFamily: T.font }}
    >
      {value === 0 ? "0" : fmt(value)}
    </text>
  );
}

export function Bars({
  data,
  series,
  domain,
  labelWidth = 140,
}: {
  data: Record<string, string | number>[];
  series: BarSeries[];
  domain?: [number, number];
  labelWidth?: number;
}): JSX.Element {
  return (
    <>
      <div className="chart-legend">
        {series.map((s) => (
          <span key={s.key}>
            <span className="chart-swatch" style={{ background: s.colour }} />
            {s.label}
          </span>
        ))}
      </div>
      <ChartBox height={54 * data.length + 68}>
        <BarChart data={data} layout="vertical" barGap={2} margin={{ top: 4, right: 44, bottom: 18, left: 4 }}>
          <CartesianGrid {...gridProps} horizontal={false} />
          <XAxis type="number" domain={domain ?? [0, 1]} tickMargin={8} {...axisProps} tickFormatter={fmt} />
          <YAxis
            type="category"
            dataKey="label"
            width={labelWidth}
            interval={0}
            tickMargin={4}
            {...axisProps}
            axisLine={false}
          />
          <ChartTooltip cursor={{ fill: T.bgSubtle }} content={<TooltipBody format={fmt} />} />
          {series.map((s) => (
            <Bar
              key={s.key}
              dataKey={s.key}
              name={s.label}
              fill={s.colour}
              radius={[0, 4, 4, 0]}
              minPointSize={2}
              isAnimationActive={false}
            >
              <LabelList dataKey={s.key} content={<ValueLabel />} />
            </Bar>
          ))}
        </BarChart>
      </ChartBox>
    </>
  );
}
