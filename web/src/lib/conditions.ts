// T, p and the plotted quantity live in the URL, so every view and every link agrees.
import { useSearchParams } from "react-router-dom";
import { useManifest, type Conditions, type Quantity } from "../api/client";
import { nearestIndex, type Manifest } from "../api/static";

export const DEFAULT_T = 298.15;
export const DEFAULT_P = 1;
export const T_RANGE = [10, 3000] as const; // K (Plan §4: conditions slider)
export const P_RANGE = [1e-6, 1e3] as const; // atm

export type ColorBy = "verdict" | "value";

export const QUANTITIES: { value: Quantity; label: string; hint: string }[] = [
  { value: "d_e", label: "D_e", hint: "electronic energy" },
  { value: "d_0", label: "D₀", hint: "with zero-point energy" },
  { value: "d_h", label: "D_H", hint: "enthalpy at T" },
  { value: "d_g", label: "D_G", hint: "free energy at T and p" },
];

function number(params: URLSearchParams, key: string, fallback: number, [lo, hi]: readonly [number, number]) {
  const v = Number(params.get(key));
  return params.has(key) && Number.isFinite(v) ? Math.min(hi, Math.max(lo, v)) : fallback;
}

/** Static site: the nearest exported condition, so labels show what the data was computed at. */
export function snapConditions(c: Conditions, grid: Manifest["conditions"] | undefined): Conditions {
  if (!grid) return c;
  return {
    temperature: grid.temperatures[nearestIndex(grid.temperatures, c.temperature)],
    pressure: grid.pressures[nearestIndex(grid.pressures, c.pressure)],
  };
}

export function useConditions() {
  const [params, setParams] = useSearchParams();
  const grid = useManifest().data?.conditions;
  const conditions: Conditions = snapConditions({
    temperature: number(params, "T", DEFAULT_T, T_RANGE),
    pressure: number(params, "p", DEFAULT_P, P_RANGE),
  }, grid);
  const q = params.get("q");
  const quantity: Quantity = QUANTITIES.some((x) => x.value === q) ? (q as Quantity) : "d_e";
  const colorBy: ColorBy = params.get("color") === "value" ? "value" : "verdict";

  const update = (changes: Record<string, string | number | null>) =>
    setParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        for (const [k, v] of Object.entries(changes)) {
          if (v === null) next.delete(k);
          else next.set(k, String(v));
        }
        return next;
      },
      { replace: true },
    );
  return { conditions, quantity, colorBy, update, search: params.toString() };
}
