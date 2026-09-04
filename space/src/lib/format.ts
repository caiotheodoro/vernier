// Number formatting only. Values always arrive from stats.json / frames.json.
export function pct(x: number, digits = 1): string {
  return (x * 100).toFixed(digits);
}

export function pctSpan(lo: number, hi: number, digits = 1): string {
  return `${pct(lo, digits)}–${pct(hi, digits)}`;
}

export function fixed(x: number, digits = 2): string {
  return x.toFixed(digits);
}

/** Confidence the way the spec writes it: `.9999`. */
export function conf(x: number | null): string {
  if (x === null) return "—";
  return x >= 1 ? "1.0000" : x.toFixed(4).replace(/^0/, "");
}

export function int(n: number): string {
  return n.toLocaleString("en-US");
}

export function usd(x: number): string {
  return `$${x.toFixed(2)}`;
}

export function hours(h: number): string {
  return `${h.toFixed(1)} h`;
}

export function seconds(ms: number): string {
  return `${(ms / 1000).toFixed(1)} s`;
}

export function plural(n: number, one: string, many = `${one}s`): string {
  return n === 1 ? one : many;
}
