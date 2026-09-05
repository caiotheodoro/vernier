// Chart tokens, mirroring space/src/tokens.css. Recharts needs literal colours, not CSS
// variables, so these are duplicated here on purpose -- change one, change both.
export const T = {
  bg: "#ffffff",
  bgSubtle: "#f8f8f7",
  border: "#e8e8e4",
  ink: "#171717",
  muted: "#6b6b6b",
  faint: "#a3a3a3",
  font: '"Plus Jakarta Sans", system-ui, sans-serif',
} as const;

/**
 * Three values, fixed order, never cycled. Grey = nobody checked, blue = a machine checked,
 * rust = a human checked. The palette's worst colour-vision pair sits in the 6-8 ΔE band, so
 * every series also carries a direct value label -- identity is never colour alone.
 */
export const PUBLISHED = "#a3a3a3";
export const JUDGE = "#4361ee";
export const MEASURED = "#c93d1e";

/** Drops the leading zero below 1, matching the CV's convention. */
export const fmt = (v: number): string =>
  Math.abs(v) < 1 ? v.toFixed(3).replace(/^0/, "") : v.toFixed(2);

export const pp = (v: number): string => `${v >= 0 ? "+" : ""}${v.toFixed(2)} pp`;
