// Wilson score interval for a proportion -- for the small-n counts the UI derives on the fly
// (a confusion cell, a reason link). Every headline interval comes from stats.json instead.
export type Interval = { lo: number; hi: number };

export function wilson(k: number, n: number, z = 1.959964): Interval {
  if (n <= 0) return { lo: 0, hi: 1 };
  const p = k / n;
  const z2 = z * z;
  const denom = 1 + z2 / n;
  const centre = (p + z2 / (2 * n)) / denom;
  const half = (z * Math.sqrt((p * (1 - p)) / n + z2 / (4 * n * n))) / denom;
  return { lo: Math.max(0, centre - half), hi: Math.min(1, centre + half) };
}
