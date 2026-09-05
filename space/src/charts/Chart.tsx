// Chart primitives, ported from the author's CV (src/components/ui/chart.tsx). One light
// theme, no legend machinery: every series here carries a direct label instead.
import type { ReactElement, ReactNode } from "react";
import { ResponsiveContainer, Tooltip } from "recharts";
import { T } from "./theme";

export function ChartFrame({
  title,
  caption,
  children,
}: {
  title?: string;
  caption?: ReactNode;
  children: ReactNode;
}): JSX.Element {
  return (
    <figure className="chart-frame">
      {title ? <div className="chart-frame-title">{title}</div> : null}
      {children}
      {caption ? <figcaption className="chart-frame-caption">{caption}</figcaption> : null}
    </figure>
  );
}

export function ChartBox({ height, children }: { height: number; children: ReactElement }): JSX.Element {
  return (
    <div style={{ width: "100%", height, fontFamily: T.font, fontSize: 12, color: T.ink }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

export const axisProps = {
  stroke: T.border,
  tick: { fill: T.muted, fontSize: 11, fontFamily: T.font },
  tickLine: false,
} as const;

export const gridProps = {
  stroke: T.border,
  strokeDasharray: "2 4",
} as const;

/** Recharts 3 reads these off context and no longer declares them on TooltipProps. */
type TooltipItem = { name?: string | undefined; value?: number | string | undefined; color?: string | undefined; payload?: Record<string, unknown> | undefined };

export function TooltipBody({
  active,
  payload,
  label,
  format = (v: number) => v.toFixed(3),
  extra,
}: {
  active?: boolean | undefined;
  payload?: TooltipItem[] | undefined;
  label?: string | number | undefined;
  format?: (v: number) => string;
  extra?: (datum: Record<string, unknown>) => ReactNode;
}): JSX.Element | null {
  if (!active || !payload?.length) return null;
  const datum = (payload[0]?.payload ?? {}) as Record<string, unknown>;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip-label">{String(datum["label"] ?? label ?? "")}</div>
      {payload.map((p, i) => (
        <div className="chart-tooltip-row" key={i}>
          <span className="chart-swatch" style={{ background: p.color ?? T.ink }} />
          <span>{p.name}</span>
          <strong>{typeof p.value === "number" ? format(p.value) : String(p.value ?? "")}</strong>
        </div>
      ))}
      {extra?.(datum)}
    </div>
  );
}

export { Tooltip as ChartTooltip };
