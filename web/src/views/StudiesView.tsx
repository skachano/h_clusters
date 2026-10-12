// Phase 8: extra calculations on the best structures, one table per study.
import { useParams } from "react-router-dom";
import { useStudies, useStudy } from "../api/client";
import { pretty } from "../lib/format";
import { type WikiPage } from "../lib/wiki";
import { WikiLink } from "../components/WikiLink";
import { en } from "../i18n/en";
import { useT, type Key, type T } from "../i18n";
import { verdictLabel } from "../i18n/terms";
import type { Verdict } from "../api/client";

/**
 * Columns in display order: an i18n key (`col.*`), or a symbol shown as is in every language.
 * Titles and descriptions are the keys `st.<name>` and `st.<name>.about`.
 */
const COLUMNS: Record<string, Record<string, Key | { symbol: string }>> = {
  vertical: { state: "col.state", kind: "col.kind", vertical_ev: "col.vertical_ev", adiabatic_ev: "col.adiabatic_ev", to_mult: "col.to_mult", verdict: "col.verdict" },
  counterpoise: { state: "col.state", channel: "col.channel", d_e_ev: "col.d_e_ev", bsse_ev: "col.bsse_ev", d_e_cp_ev: "col.d_e_cp_ev", d_0_cp_ev: "col.d_0_cp_ev", bound_after_cp: "col.bound_after_cp" },
  anharmonic: { species: "col.species", harmonic_cm: "col.harmonic_cm", vpt2_cm: "col.vpt2_cm", correction_cm: "col.correction_cm", g0_cm: "col.g0_cm", rotation_cm: "col.rotation_cm", frequencies_cm: "col.frequencies_cm", harmonic_ev: "col.harmonic_ev", vpt2_ev: "col.vpt2_ev" },
  solvent: { state: "col.state", channel: "col.channel", gas: "col.gas", eps2: { symbol: "ε = 2" }, eps10: { symbol: "ε = 10" }, eps80: { symbol: "ε = 80" } },
  field: { state: "col.state", channel: "col.channel", F0: { symbol: "F = 0" }, "F0.005": { symbol: "0.005" }, "F0.01": { symbol: "0.01" }, "F0.02": { symbol: "0.02" }, alpha_au: { symbol: "α_zz (a.u.)" } },
  bonds: { state: "col.state", structure_id: "col.structure_id", units: "col.units", weakest_in_unit: "col.weakest_in_unit", strongest_in_unit: "col.strongest_in_unit", strongest_link: "col.strongest_link" },
  dmc: { state: "col.state", channel: "col.channel", d_e_ccsdt_mev: "col.d_e_ccsdt_mev", d_e_model_mev: "col.d_e_model_mev", d0_harmonic_mev: "col.d0_harmonic_mev", d0_dmc_mev: "col.d0_dmc_mev", d0_dmc_err_mev: "col.d0_dmc_err_mev", d0_shallow_mev: "col.d0_shallow_mev", dmc_verdict: "col.dmc_verdict", method: "col.method", dmc_check_mev: "col.dmc_check_mev", spread_angstrom: "col.spread_angstrom", size_growth: "col.size_growth", exact_r_angstrom: "col.exact_r_angstrom" },
  dmc_anions: { state: "col.state", channel: "col.channel", d_e_ccsdt_mev: "col.d_e_ccsdt_mev", d_e_model_mev: "col.d_e_model_mev", total_model_mev: "col.total_model_mev", total_ccsdt_mev: "col.total_ccsdt_mev", three_body_mev: "col.three_body_mev", d0_harmonic_mev: "col.d0_harmonic_mev", d0_isotropic_mev: "col.d0_isotropic_mev", d0_pairs_only_mev: "col.d0_pairs_only_mev", d0_dmc_mev: "col.d0_dmc_mev", d0_dmc_err_mev: "col.d0_dmc_err_mev", d0_shallow_mev: "col.d0_shallow_mev", dmc_verdict: "col.dmc_verdict", method: "col.method", dmc_check_mev: "col.dmc_check_mev", spread_angstrom: "col.spread_angstrom", size_growth: "col.size_growth", exact_r_angstrom: "col.exact_r_angstrom" },
  barriers: { state: "col.state", channel: "col.channel", atoms: "col.atoms", d_e_ev: "col.d_e_ev", barrier_verdict: "col.barrier_verdict", threshold_ev: "col.threshold_ev", barrier_ev: "col.barrier_ev", barrier_0_ev: "col.barrier_0_ev", above_products_ev: "col.above_products_ev", ts_imag_cm: "col.ts_imag_cm", max_mp2_ev: "col.max_mp2_ev", end_mp2_ev: "col.end_mp2_ev", max_ccsdt_ev: "col.max_ccsdt_ev", end_ccsdt_ev: "col.end_ccsdt_ev", neb_converged: "col.neb_converged" },
  basis: { item: "col.item", channel: "col.channelGeometry", avtz: "col.avtz", cbs: "col.cbs", change: "col.change", unit: "col.unit" },
};

const ORDER = ["vertical", "counterpoise", "anharmonic", "dmc", "dmc_anions", "barriers", "basis", "bonds", "solvent", "field"];

export function StudiesView() {
  const { campaign = "baseline" } = useParams();
  const names = useStudies(campaign);
  const available = new Set(names.data ?? []);
  const t = useT();
  return (
    <div className="stack">
      <div>
        <h1>{t("st.title")}</h1>
        <p className="lede">{t("st.lede")}</p>
      </div>
      {names.isError && <p className="error">{String(names.error)}</p>}
      {ORDER.filter((n) => available.has(n)).map((n) => <StudyCard key={n} campaign={campaign} name={n} />)}
      {[...available].filter((n) => !ORDER.includes(n)).map((n) => <StudyCard key={n} campaign={campaign} name={n} />)}
      {names.data && names.data.length === 0 && (
        <p className="muted">{t("st.none")}<code>python -m hclust study &lt;name&gt;</code></p>
      )}
    </div>
  );
}

function cell(value: unknown, t: T): string {
  if (value == null) return "–";
  if (typeof value === "boolean") return value ? t("common.yes") : t("common.no");
  // at most 4 decimals (1 from 100 up), without padding: reports round their values already
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(Math.abs(value) >= 100 ? 1 : 4)));
  if (Array.isArray(value)) return value.map((v) => cell(v, t)).join(", ");
  return pretty(String(value));
}

// The wiki page that explains what each study computes.
const STUDY_WIKI: Record<string, WikiPage> = {
  vertical: "techniques/ionization-and-electron-affinity",
  counterpoise: "methods/basis-sets",
  anharmonic: "techniques/zero-point-energy",
  bonds: "foundations/chemical-and-van-der-waals-bonds",
  basis: "methods/basis-sets",
  dmc: "methods/diffusion-monte-carlo",
  dmc_anions: "methods/diffusion-monte-carlo",
  barriers: "techniques/transition-states",
};

function StudyCard({ campaign, name }: { campaign: string; name: string }) {
  const study = useStudy(campaign, name);
  const t = useT();
  const known = `st.${name}` in en;
  const title = known ? t(`st.${name}` as Key) : name;
  const about = known ? t(`st.${name}.about` as Key) : "";
  const spec = COLUMNS[name] ?? {};
  const header = (c: string) => {
    const col = spec[c];
    return col === undefined ? c : typeof col === "string" ? t(col) : col.symbol;
  };
  const rows = study.data?.rows ?? [];
  const keys = [...new Set(rows.flatMap((r) => Object.keys(r)))];
  const columns = [...Object.keys(spec).filter((k) => keys.includes(k)), ...keys.filter((k) => !(k in spec))];
  return (
    <section className="card stack" style={{ gap: 8 }} aria-labelledby={`study-${name}`}>
      <h2 id={`study-${name}`}>{title}{STUDY_WIKI[name] && <WikiLink page={STUDY_WIKI[name]} />}</h2>
      {about && <p className="hint" style={{ maxWidth: "80ch" }}>{about}</p>}
      {study.isError && <p className="error">{String(study.error)}</p>}
      {rows.length > 0 && (
        <div className="table-wrap">
          <table className="study-table">
            <thead>
              <tr>{columns.map((c) => <th key={c} className={typeof rows[0][c] === "number" ? "num" : undefined}>{header(c)}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  {columns.map((c) => <td key={c} className={typeof r[c] === "number" ? "num" : undefined}>{c === "verdict" && typeof r[c] === "string" && `verdict.${r[c]}` in en ? verdictLabel(t, r[c] as Verdict)
                    : c === "dmc_verdict" && `dmcv.${r[c]}` in en ? t(`dmcv.${r[c]}` as Key)
                    : c === "method" && `dmcm.${r[c]}` in en ? t(`dmcm.${r[c]}` as Key)
                    : c === "barrier_verdict" && `bv.${r[c]}` in en ? t(`bv.${r[c]}` as Key) : cell(r[c], t)}</td>)}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
