// Colour scales, all validated with the data-viz palette checks (doc/Plan.md, Phase 7).
// Every colour is a CSS custom property (styles.css), so light and dark swap in one place.
import type { Quantity, StateBrief, Verdict } from "../api/client";

/** Stability is ordinal: a ladder of nested tests, each rung passing every test below it.
 * The selected dissociation energy sets how far up the ladder goes: D_e stops at "bound",
 * D₀ (and D_H) add "bound with ZPE" (the stored verdict), D_G adds "holds at T and p". */
export type Rung = Verdict | "bound_e" | "holds";

const LADDER: Verdict[] = ["metastable", "bound", "bound_with_zpe"];
const positive = (d: number | null | undefined) => d != null && d > 0;

type Energies = Pick<StateBrief, "verdict" | "d_e" | "d_0" | "d_h" | "d_g">;

export function rung(s: Energies, q: Quantity): Rung {
  if (!LADDER.includes(s.verdict)) return s.verdict; // atoms, no structure: no ladder
  if (!positive(s.d_e)) return "metastable";
  if (q === "d_e") return "bound_e";
  if (!positive(s.d_0)) return "bound";
  return q === "d_g" && positive(s.d_g) ? "holds" : "bound_with_zpe";
}

/** The rungs of the ladder for a quantity, bottom up (the legend). */
export function rungs(q: Quantity): Rung[] {
  if (q === "d_e") return ["metastable", "bound_e"];
  return q === "d_g" ? ["metastable", "bound", "bound_with_zpe", "holds"] : ["metastable", "bound", "bound_with_zpe"];
}

/** D_H selected: energy holds it together at T, but entropy pulls it apart (D_H > 0, D_G <= 0). */
export const entropyLimited = (s: Energies, q: Quantity) =>
  q === "d_h" && LADDER.includes(s.verdict) && positive(s.d_h) && s.d_g != null && !positive(s.d_g);

export const VERDICT_FILL: Record<Rung, string> = {
  unbound_electron: "var(--none)",
  not_a_minimum: "var(--none)",
  dissociates: "var(--none)",
  metastable: "var(--ord-1)",
  bound_e: "var(--ord-2)",
  bound: "var(--ord-2)",
  bound_with_zpe: "var(--ord-3)",
  holds: "var(--ord-4)",
  atom: "var(--none)",
};

/** Text ink on each fill (white on the dark steps). */
export const VERDICT_INK: Record<Rung, string> = {
  unbound_electron: "var(--text-secondary)",
  not_a_minimum: "var(--text-secondary)",
  dissociates: "var(--text-secondary)",
  metastable: "var(--ink-on-ord-1)",
  bound_e: "var(--ink-on-ord-2)",
  bound: "var(--ink-on-ord-2)",
  bound_with_zpe: "var(--ink-on-ord-3)",
  holds: "var(--ink-on-ord-4)",
  atom: "var(--text-secondary)",
};

// Verdict, charge and spin-state names are translated: i18n/terms.ts.

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

/** Marker shape per charge: a second channel besides colour (anion and neutral points coincide). */
export const CHARGE_MARKER: Record<number, "ring" | "dot" | "square"> = { [-1]: "ring", 0: "dot", 1: "square" };
