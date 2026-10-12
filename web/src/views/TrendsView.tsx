// View 3: trends against m, one line per charge.
import { useState } from "react";
import { useParams, useSearchParams } from "react-router-dom";
import { useTrends, type TrendQuantity } from "../api/client";
import { ConditionsBar } from "../components/ConditionsBar";
import { LineChart } from "../components/charts/LineChart";
import { WikiLink } from "../components/WikiLink";
import { useConditions } from "../lib/conditions";
import type { WikiPage } from "../lib/wiki";
import { pretty, signed } from "../lib/format";
import { CHARGE_COLOR, CHARGE_MARKER } from "../lib/scales";
import { useT, type Key } from "../i18n";
import { chargeLabel } from "../i18n/terms";

const QUANTITIES: TrendQuantity[] = ["binding_per_atom", "d_e", "d_0", "d_g", "second_difference", "gap"];
// The wiki page behind each quantity, where there is one.
const QUANTITY_WIKI: Partial<Record<TrendQuantity, WikiPage>> = {
  d_e: "techniques/fragmentation",
  d_0: "techniques/zero-point-energy",
  d_g: "techniques/thermochemistry",
  gap: "methods/hartree-fock",
};

export function TrendsView() {
  const { campaign = "baseline" } = useParams();
  const { conditions, update } = useConditions();
  const [params, setParams] = useSearchParams();
  const quantity = QUANTITIES.find((q) => q === params.get("trend")) ?? "binding_per_atom";
  const trends = useTrends(campaign, quantity, conditions);
  const [asTable, setAsTable] = useState(false);
  const t = useT();
  const label = (q: TrendQuantity) => t(`trend.${q}` as Key);

  const series = (trends.data?.series ?? []).map((s) => ({
    key: String(s.charge),
    label: chargeLabel(t, s.charge),
    color: CHARGE_COLOR[s.charge],
    marker: CHARGE_MARKER[s.charge],
    points: s.points.map((p) => ({ x: p.m, y: p.value ?? null, note: p.label ? pretty(p.label) : null })),
  }));

  return (
    <div className="stack">
      <div>
        <h1>{t("trends.title")}</h1>
        <p className="lede">{t("trends.lede")}</p>
      </div>
      <ConditionsBar conditions={conditions} update={update}>
        <div className="control">
          <label htmlFor="trend">{t("trends.quantity")}</label>
          <select id="trend" value={quantity} onChange={(e) => setParams((p) => { const n = new URLSearchParams(p); n.set("trend", e.target.value); return n; }, { replace: true })}>
            {QUANTITIES.map((q) => <option key={q} value={q}>{label(q)}</option>)}
          </select>
        </div>
        <div className="control">
          <span className="label">{t("view.label")}</span>
          <div className="segmented" role="group" aria-label={t("view.label")}>
            <button type="button" aria-pressed={!asTable} onClick={() => setAsTable(false)}>{t("view.chart")}</button>
            <button type="button" aria-pressed={asTable} onClick={() => setAsTable(true)}>{t("view.table")}</button>
          </div>
        </div>
      </ConditionsBar>
      <div className={`card stack ${trends.isPlaceholderData ? "stale" : ""}`} style={{ gap: 8 }}>
        <h2>{label(quantity)}{QUANTITY_WIKI[quantity] && <WikiLink page={QUANTITY_WIKI[quantity]} />}</h2>
        <p className="hint">{t(`trend.${quantity}.about` as Key)}</p>
        {trends.isError && <p className="error">{String(trends.error)}</p>}
        {trends.data && !asTable && (
          <LineChart series={series} xLabel={t("trends.x")} yLabel={label(quantity)} unit={trends.data.unit}
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
