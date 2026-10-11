// Colour scales, all validated with the data-viz palette checks (doc/Plan.md, Phase 7).
// Every colour is a CSS custom property (styles.css), so light and dark swap in one place.
import type { Verdict } from "../api/client";

/** Stability is ordinal: metastable < bound < bound with ZPE (one hue, light → dark). */
export const VERDICT_FILL: Record<Verdict, string> = {
  unbound_electron: "var(--none)",
  not_a_minimum: "var(--none)",
  dissociates: "var(--none)",
  metastable: "var(--ord-1)",
  bound: "var(--ord-2)",
  bound_with_zpe: "var(--ord-3)",
  atom: "var(--none)",
};

/** Text ink on each fill (white on the dark steps). */
export const VERDICT_INK: Record<Verdict, string> = {
  unbound_electron: "var(--text-secondary)",
  not_a_minimum: "var(--text-secondary)",
  dissociates: "var(--text-secondary)",
  metastable: "var(--ink-on-ord-1)",
  bound: "var(--ink-on-ord-2)",
  bound_with_zpe: "var(--ink-on-ord-3)",
  atom: "var(--text-secondary)",
};

export const VERDICT_LABEL: Record<Verdict, string> = {
  unbound_electron: "electron unbound",
  not_a_minimum: "no minimum found",
  dissociates: "falls apart",
  metastable: "metastable",
  bound: "bound (not with ZPE)",
  bound_with_zpe: "bound with ZPE",
  atom: "atom",
};

export const VERDICT_SHORT: Record<Verdict, string> = {
  unbound_electron: "e⁻ unbound",
  not_a_minimum: "no minimum",
  dissociates: "falls apart",
  metastable: "metastable",
  bound: "bound",
  bound_with_zpe: "bound + ZPE",
  atom: "atom",
};

/** Diverging bins for a dissociation energy (eV): blue = bound, red = falls apart. */
export const VALUE_BINS = [0.01, 0.05, 0.3, 1.5]; // |D| thresholds, eV

export function valueStep(d: number | null | undefined): { fill: string; ink: string; bin: number } {
  if (d == null) return { fill: "var(--none)", ink: "var(--text-secondary)", bin: 0 };
  const a = Math.abs(d);
  const bin = a < VALUE_BINS[0] ? 0 : a < VALUE_BINS[1] ? 1 : a < VALUE_BINS[2] ? 2 : a < VALUE_BINS[3] ? 3 : 4;
  if (bin === 0) return { fill: "var(--div-mid)", ink: "var(--text-primary)", bin };
  const arm = d > 0 ? "pos" : "neg";
  return { fill: `var(--div-${arm}-${bin})`, ink: `var(--ink-on-div-${bin})`, bin: d > 0 ? bin : -bin };
}

/** Charge is the one categorical dimension: three slots, safe in every pairing. */
export const CHARGE_COLOR: Record<number, string> = {
  [-1]: "var(--series-1)",
  0: "var(--series-2)",
  1: "var(--series-3)",
};
export const CHARGE_LABEL: Record<number, string> = { [-1]: "anions", 0: "neutral", 1: "cations" };

/** Marker shape per charge: a second channel besides colour (anion and neutral points coincide). */
export const CHARGE_MARKER: Record<number, "ring" | "dot" | "square"> = { [-1]: "ring", 0: "dot", 1: "square" };
