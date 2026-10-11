// Halos: a see-through sphere around each atom whose colour gives the sign of its charge
// (or spin) and whose size and opacity give the magnitude, on one fixed scale for every
// species, so the ±0.01 charges of a neutral cluster stay invisible next to an ion's ±0.3.
import type { AtomSummary } from "./atoms";

export type Highlight = "none" | "charge" | "spin";

/** |value| drawn at full strength: Löwdin charges stay within ±0.5 here, spins within ±1. */
export const HALO_FULL: Record<Exclude<Highlight, "none">, number> = { charge: 0.5, spin: 1 };
/** Colour tokens by sign: the diverging red/blue for charge, two categorical hues for spin. */
export const HALO_COLOR = {
  charge: { positive: "--div-pos-2", negative: "--div-neg-2" },
  spin: { positive: "--series-2", negative: "--series-3" },
} as const;

const MIN_FRACTION = 0.02; // below 2 % of full scale: no halo (|charge| < 0.01)
const MAX_OPACITY = 0.65;
// Exponential in |value| like the bond opacity, but gentler: half scale (charge 0.25, spin
// 0.5: half an electron) must stay visible, while neutral-cluster noise (|q| ~ 0.05) fades.
const GROWTH = 1.5;
const ATOM_RADIUS = 0.26; // Å, the drawn sphere (0.22 × van der Waals radius)

export interface Halo {
  i: number;
  radius: number; // Å
  opacity: number; // as it should look (the viewer compensates for 3Dmol)
  color: string; // CSS custom property
}

export function haloStyle(value: number, kind: Exclude<Highlight, "none">): Omit<Halo, "i"> | null {
  const f = Math.min(Math.abs(value) / HALO_FULL[kind], 1);
  if (f < MIN_FRACTION) return null;
  return {
    radius: ATOM_RADIUS + 0.06 + 0.4 * Math.sqrt(f),
    opacity: MAX_OPACITY * Math.expm1(GROWTH * f) / Math.expm1(GROWTH),
    color: HALO_COLOR[kind][value > 0 ? "positive" : "negative"],
  };
}

export function halos(atoms: AtomSummary[], kind: Highlight): Halo[] {
  if (kind === "none") return [];
  return atoms.flatMap((a, i) => {
    const value = kind === "charge" ? a.charge : a.spin;
    const style = value == null ? null : haloStyle(value, kind);
    return style ? [{ i, ...style }] : [];
  });
}
