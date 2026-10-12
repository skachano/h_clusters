// Translated names of the app's fixed vocabularies (verdicts, charges, spin states, shapes).
import type { Rung } from "../lib/scales";
import { en, type Key } from "./en";
import type { T } from "./index";

const has = (key: string): key is Key => key in en;

export const verdictLabel = (t: T, v: Rung) => t(`verdict.${v}` as Key);
export const verdictShort = (t: T, v: Rung) => t(`verdictShort.${v}` as Key);
export const chargeLabel = (t: T, charge: number) => t(`charge.${charge}` as Key);
export const multName = (t: T, mult: number) => {
  const key = `mult.${mult}`;
  return has(key) ? t(key) : t("mult.other", { n: mult });
};
/** Shape classes and job statuses come from the API; unknown values pass through. */
export const shapeName = (t: T, shape: string | null | undefined) => {
  if (!shape) return "–";
  const key = `shape.${shape}`;
  return has(key) ? t(key) : shape;
};
export const statusName = (t: T, status: string) => {
  const key = `status.${status}`;
  return has(key) ? t(key) : status;
};
