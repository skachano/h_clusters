// View 3: trends against m, one line per charge.
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useTrends, type TrendQuantity } from "../api/client";
import { ConditionsBar } from "../components/ConditionsBar";
import { LineChart } from "../components/charts/LineChart";
import { useConditions } from "../lib/conditions";
import { pretty, signed } from "../lib/format";
import { CHARGE_COLOR, CHARGE_LABEL, CHARGE_MARKER } from "../lib/scales";

const QUANTITIES: { value: TrendQuantity; label: string; about: string }[] = [
  { value: "binding_per_atom", label: "Binding energy per atom", about: "Energy to take the ground state apart into atoms (plus H⁺ or H⁻ for ions), per atom." },
  { value: "d_e", label: "D_e (weakest channel)", about: "Electronic energy of the weakest spin-allowed channel." },
  { value: "d_0", label: "D₀ (with ZPE)", about: "D_e corrected for zero-point energy: the light hydrogen nuclei make this decisive." },
  { value: "d_g", label: "D_G at T, p", about: "Free energy of the weakest channel at the chosen temperature and pressure." },
  { value: "second_difference", label: "Second difference Δ₂E", about: "E(m+1) + E(m−1) − 2E(m): peaks mark unusually stable sizes (“magic numbers”)." },
  { value: "gap", label: "HOMO–LUMO gap", about: "Hartree–Fock orbital gap of the reference wave function." },
];

export function TrendsView() {
  const { campaign = "baseline" } = useParams();
  const { conditions, update } = useConditions();
  const [params, setParams] = useSearchParams();
  const quantity = (QUANTITIES.find((q) => q.value === params.get("trend"))?.value ?? "binding_per_atom") as TrendQuantity;
  const trends = useTrends(campaign, quantity, conditions);
  const [asTable, setAsTable] = useState(false);
  const meta = QUANTITIES.find((q) => q.value === quantity)!;

  const series = (trends.data?.series ?? []).map((s) => ({
    key: String(s.charge),
    label: CHARGE_LABEL[s.charge],
    color: CHARGE_COLOR[s.charge],
    marker: CHARGE_MARKER[s.charge],
    points: s.points.map((p) => ({ x: p.m, y: p.value ?? null, note: p.label ? pretty(p.label) : null })),
  }));

  return (
    <div className="stack">
      <div>
        <h1>Trends with cluster size</h1>
        <p className="lede">
          One line per charge, from each species' lowest-energy state. Gaps are species without a stable
          structure (all even-m anions), so the anions are isolated rings.
        </p>
      </div>
      <ConditionsBar conditions={conditions} update={update}>
        <div className="control">
          <label htmlFor="trend">Quantity</label>
          <select id="trend" value={quantity} onChange={(e) => setParams((p) => { const n = new URLSearchParams(p); n.set("trend", e.target.value); return n; }, { replace: true })}>
            {QUANTITIES.map((q) => <option key={q.value} value={q.value}>{q.label}</option>)}
          </select>
        </div>
        <div className="control">
          <span className="label">View</span>
          <div className="segmented" role="group" aria-label="View">
            <button type="button" aria-pressed={!asTable} onClick={() => setAsTable(false)}>Chart</button>
            <button type="button" aria-pressed={asTable} onClick={() => setAsTable(true)}>Table</button>
          </div>
        </div>
      </ConditionsBar>
      <div className={`card stack ${trends.isPlaceholderData ? "stale" : ""}`} style={{ gap: 8 }}>
        <h2>{meta.label}</h2>
        <p className="hint">{meta.about}</p>
        {trends.isError && <p className="error">{String(trends.error)}</p>}
        {trends.data && !asTable && (
          <LineChart series={series} xLabel="m (number of H atoms)" yLabel={meta.label} unit={trends.data.unit}
            format={(v) => signed(v, 3, trends.data!.unit)} />
        )}
        {trends.data && asTable && (
          <div className="table-wrap">
            <table>
              <thead><tr><th>m</th>{series.map((s) => <th key={s.key} className="num">{s.label} ({trends.data!.unit})</th>)}</tr></thead>
              <tbody>
                {Array.from({ length: 10 }, (_, i) => i + 1).map((m) => (
                  <tr key={m}>
                    <td className="num">{m}</td>
                    {series.map((s) => {
                      const p = s.points.find((q) => q.x === m);
                      return <td key={s.key} className="num">{signed(p?.y ?? null, 3)} <span className="muted">{p?.note ?? ""}</span></td>;
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
