export const fmt = (x: number | null | undefined, digits = 3, unit = "") =>
  x == null || !Number.isFinite(x) ? "–" : `${x.toFixed(digits)}${unit ? ` ${unit}` : ""}`;

export const signed = (x: number | null | undefined, digits = 3, unit = "") =>
  x == null || !Number.isFinite(x) ? "–" : `${x >= 0 ? "+" : "−"}${Math.abs(x).toFixed(digits)}${unit ? ` ${unit}` : ""}`;

const SUB = "₀₁₂₃₄₅₆₇₈₉";
const SUP: Record<string, string> = { "+": "⁺", "-": "⁻" };

/** 'H10-' → 'H₁₀⁻', 'H3+ (1)' → 'H₃⁺ (1)', 'H2(3) + e-' → 'H₂(3) + e⁻'. */
export function pretty(label: string): string {
  return label.replace(/H(\d*)([+-]?)/g, (_, digits: string, sign: string) =>
    `H${[...digits].map((d) => SUB[Number(d)]).join("")}${sign ? SUP[sign] : ""}`,
  ).replace(/e-/g, "e⁻");
}

export const species = (m: number, charge: number) =>
  pretty(`H${m > 1 ? m : ""}${charge > 0 ? "+" : charge < 0 ? "-" : ""}`);


export const duration = (s: number | null | undefined) =>
  s == null ? "–" : s < 60 ? `${s.toFixed(0)} s` : s < 3600 ? `${(s / 60).toFixed(1)} min` : `${(s / 3600).toFixed(1)} h`;
