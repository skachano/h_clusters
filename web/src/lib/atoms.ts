// Per-atom summaries from the bonds study, for the 3D hover labels and the atom table.
import type { BondsOut } from "../api/client";
import { signed } from "./format";
import type { T } from "../i18n";

export interface AtomSummary {
  name: string; // H1..Hn, the numbering of the bond table
  charge: number;
  spin: number | null;
  bondSum: number; // sum of the atom's Löwdin bond orders
  freeValence: number | null;
}

export function atomSummaries(bonds: BondsOut): AtomSummary[] {
  const sums = bonds.atoms.map(() => 0);
  for (const b of bonds.loewdin) {
    sums[b.i] += b.order;
    sums[b.j] += b.order;
  }
  return bonds.atoms.map((a, i) => ({
    name: `H${i + 1}`, charge: a.charge, spin: a.spin ?? null, bondSum: sums[i], freeValence: a.free_valence ?? null,
  }));
}

/** One line for the 3D hover label. */
export function atomLabel(a: AtomSummary, t: T): string {
  const parts = [t("hover.atom", { name: a.name, charge: signed(a.charge, 2) })];
  if (a.spin != null) parts.push(t("hover.spin", { spin: signed(a.spin, 2) }));
  parts.push(t("hover.bondSum", { sum: a.bondSum.toFixed(2) }));
  if (a.freeValence != null && a.freeValence >= 0.05) parts.push(t("hover.freeValence", { fv: a.freeValence.toFixed(2) }));
  return parts.join(", ");
}
