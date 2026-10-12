// View 1: the periodic grid. Rows are charge, columns m; each cell is a species' ground state.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGrid, type Conditions, type GridCell, type Quantity, type StateBrief } from "../api/client";
import { ConditionsBar } from "../components/ConditionsBar";
import { Thumbnail } from "../components/Thumbnail";
import { WikiLink } from "../components/WikiLink";
import { focusPoint, useTooltip } from "../components/Tooltip";
import { QUANTITIES, formatP, formatT, useConditions, type ColorBy } from "../lib/conditions";
import { fmt, pretty, signed, species } from "../lib/format";
import { VALUE_BINS, VERDICT_FILL, VERDICT_INK, entropyLimited, rung, rungs, valueStep, type Rung } from "../lib/scales";
import { useT, type Key, type T } from "../i18n";
import { chargeLabel, multName, verdictLabel, verdictShort } from "../i18n/terms";

const CHARGES = [-1, 0, 1];
const MS = Array.from({ length: 10 }, (_, i) => i + 1);

export function GridView() {
  const { campaign = "baseline" } = useParams();
  const { conditions, quantity, colorBy, update, search } = useConditions();
  const grid = useGrid(campaign, conditions, quantity);
  const [asTable, setAsTable] = useState(false);
  const tip = useTooltip();
  const t = useT();
  const qLabel = QUANTITIES.find((q) => q.value === quantity)?.label ?? quantity;

  const cells = new Map<string, GridCell>();
  for (const c of grid.data?.cells ?? []) cells.set(`${c.m},${c.charge}`, c);

  return (
    <div className="stack">
      <div>
        <h1>{t("grid.title")}</h1>
        <p className="lede">
          {t("grid.ledeBefore")}H<sub>m</sub><sup>n</sup>{t("grid.ledeAfter")}
        </p>
      </div>
      <ConditionsBar conditions={conditions} quantity={quantity} colorBy={colorBy} update={update}>
        <div className="control">
          <span className="label">{t("view.label")}</span>
          <div className="segmented" role="group" aria-label={t("view.label")}>
            <button type="button" aria-pressed={!asTable} onClick={() => setAsTable(false)}>{t("view.grid")}</button>
            <button type="button" aria-pressed={asTable} onClick={() => setAsTable(true)}>{t("view.table")}</button>
          </div>
        </div>
      </ConditionsBar>
      <ScaleLegend colorBy={colorBy} quantity={quantity} quantityLabel={qLabel} conditions={conditions}
        entropy={quantity === "d_h" && (grid.data?.cells ?? []).some((c) => c.ground && entropyLimited(c.ground, quantity))} />

      {grid.isError && <p className="error">{t("grid.error", { error: String(grid.error) })}</p>}
      {grid.isPending && <p className="loading">{t("common.loading")}</p>}
      {grid.data && !asTable && (
        <div className={`card ${grid.isPlaceholderData ? "stale" : ""}`} style={{ overflowX: "auto", padding: 12 }}>
          <div className="periodic" role="grid" aria-label={t("grid.aria")}>
            <div role="row" className="periodic-row">
              <div className="periodic-corner" />
              {MS.map((m) => <div key={m} role="columnheader" className="periodic-head num">m = {m}</div>)}
            </div>
            {CHARGES.map((charge) => (
              <div role="row" className="periodic-row" key={charge}>
                <div role="rowheader" className="periodic-rowhead">{chargeLabel(t, charge)}</div>
                {MS.map((m) => (
                  <Cell key={m} m={m} charge={charge} cell={cells.get(`${m},${charge}`)} colorBy={colorBy}
                    quantity={quantity} quantityLabel={qLabel} campaign={campaign} search={search} tip={tip} t={t} />
                ))}
              </div>
            ))}
          </div>
        </div>
      )}
      {grid.data && asTable && (
        <GridTable cells={grid.data.cells} quantity={quantity} colorBy={colorBy} campaign={campaign} search={search}
          select={(q) => update({ q })} stale={grid.isPlaceholderData} />
      )}
      {tip.node}
    </div>
  );
}

function Cell({ m, charge, cell, colorBy, quantity, quantityLabel, campaign, search, tip, t }: {
  m: number; charge: number; cell?: GridCell; colorBy: ColorBy; quantity: Quantity; quantityLabel: string;
  campaign: string; search: string; tip: ReturnType<typeof useTooltip>; t: T;
}) {
  if (!cell || !cell.ground) {
    const proton = m === 1 && charge === 1;
    return (
      <div role="gridcell" className="periodic-cell empty" style={{ background: "var(--none)" }}>
        <div className="cell-name">{species(m, charge)}</div>
        <div className="cell-verdict">{proton ? t("grid.bareProton") : t("grid.notComputed")}</div>
      </div>
    );
  }
  const g = cell.ground;
  const r = rung(g, quantity);
  const entropy = entropyLimited(g, quantity);
  const step = valueStep(cell.value);
  const fill = colorBy === "verdict" ? VERDICT_FILL[r] : step.fill;
  const ink = colorBy === "verdict" ? VERDICT_INK[r] : step.ink;
  const channel = channelFor(g, quantity);
  const details = (
    <div>
      <div className="tt-value">{pretty(g.label)} · {verdictLabel(t, r)}</div>
      <div className="tt-label">{quantityLabel} {signed(cell.value, 3, "eV")}{channel ? ` → ${pretty(channel)}` : ""}</div>
      {entropy && <div className="tt-label">{t("grid.entropy")}</div>}
      {g.units && <div className="tt-label">{t("grid.units", { units: pretty(g.units) })}{g.point_group ? ` · ${g.point_group}` : ""}</div>}
      {cell.states.length > 1 && (
        <div className="tt-label" style={{ marginTop: 4 }}>
          {cell.states.map((s) => `${multName(t, s.mult)}: ${shortRung(t, s, quantity)}`).join(" · ")}
        </div>
      )}
    </div>
  );
  return (
    <Link
      role="gridcell"
      to={`/c/${campaign}/s/${m}/${charge}/${g.mult}${search ? `?${search}` : ""}`}
      className="periodic-cell"
      style={{ background: fill, color: ink }}
      aria-label={`${g.label}: ${verdictLabel(t, r)}${entropy ? ` (${t("grid.entropy")})` : ""}, ${quantityLabel} ${fmt(cell.value, 3, "eV")}`}
      onPointerMove={(e) => tip.show(e.clientX, e.clientY, details)}
      onPointerLeave={tip.hide}
      onFocus={(e) => tip.show(...focusPoint(e), details)}
      onBlur={tip.hide}
    >
      <div className="cell-top">
        <span className="cell-name">{species(m, charge)}</span>
        <span className="cell-mult num" title={t("grid.multTitle")}>{g.mult}</span>
      </div>
      <div className="cell-thumb">{cell.xyz ? <Thumbnail xyz={cell.xyz} bonds={cell.bonds} size={52} ink={ink} /> : <span className="cell-none">—</span>}</div>
      <div className="cell-verdict">{shortRung(t, g, quantity)}</div>
      <div className="cell-value num">{cell.value == null ? " " : signed(cell.value, cell.value !== 0 && Math.abs(cell.value) < 0.1 ? 3 : 2)}</div>
    </Link>
  );
}

/** The weakest channel behind the selected D: the API gives the one for D_e and the one for D_G. */
function channelFor(s: StateBrief, q: Quantity) {
  return q === "d_g" ? s.channel_g ?? s.channel : s.channel;
}

/** The short verdict on the selected ladder, starred when D_H holds it but D_G does not. */
function shortRung(t: T, s: StateBrief, q: Quantity) {
  return verdictShort(t, rung(s, q)) + (entropyLimited(s, q) ? " *" : "");
}

const RUNG_LEGEND: Partial<Record<Rung, Key>> = {
  metastable: "legend.metastable", bound_e: "legend.boundE", bound: "legend.bound",
  bound_with_zpe: "legend.boundZpe", holds: "legend.holds",
};

function ScaleLegend({ colorBy, quantity, quantityLabel, conditions, entropy }: {
  colorBy: ColorBy; quantity: Quantity; quantityLabel: string; conditions: Conditions; entropy: boolean;
}) {
  const t = useT();
  const note = entropy ? <span>{t("legend.entropy")}</span> : null;
  if (colorBy === "verdict") {
    return (
      <div className="legend" aria-label={t("legend.aria")}>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--none)", border: "1px solid var(--border)" }} />{t("legend.none")}</span>
        {rungs(quantity).map((r) => (
          <span className="legend-item" key={r}>
            <span className="swatch" style={{ background: VERDICT_FILL[r] }} />
            {t(RUNG_LEGEND[r]!, { T: formatT(conditions.temperature), p: formatP(conditions.pressure) })}
          </span>
        ))}
        <WikiLink page="techniques/fragmentation" anchor="verdicts" />
        {note}
      </div>
    );
  }
  const bins = VALUE_BINS;
  const steps = [
    { fill: "var(--div-neg-4)", label: `< −${bins[3]}` },
    { fill: "var(--div-neg-3)", label: `−${bins[3]} … −${bins[2]}` },
    { fill: "var(--div-neg-2)", label: `−${bins[2]} … −${bins[1]}` },
    { fill: "var(--div-neg-1)", label: `−${bins[1]} … −${bins[0]}` },
    { fill: "var(--div-mid)", label: `|D| < ${bins[0]}` },
    { fill: "var(--div-pos-1)", label: `${bins[0]} … ${bins[1]}` },
    { fill: "var(--div-pos-2)", label: `${bins[1]} … ${bins[2]}` },
    { fill: "var(--div-pos-3)", label: `${bins[2]} … ${bins[3]}` },
    { fill: "var(--div-pos-4)", label: `> ${bins[3]}` },
  ];
  return (
    <div className="legend" aria-label={t("legend.aria")}>
      <span>{t("legend.fallsApart", { q: quantityLabel })}</span>
      {steps.map((s) => (
        <span className="legend-item" key={s.label}><span className="swatch" style={{ background: s.fill }} />{s.label}</span>
      ))}
      <span>{t("legend.boundEnd")}</span>
      {note}
    </div>
  );
}

function GridTable({ cells, quantity, colorBy, campaign, search, select, stale }: {
  cells: GridCell[]; quantity: Quantity; colorBy: ColorBy; campaign: string; search: string;
  select: (q: Quantity) => void; stale: boolean;
}) {
  const t = useT();
  const qLabel = QUANTITIES.find((q) => q.value === quantity)?.label ?? quantity;
  return (
    <div className={`card table-wrap ${stale ? "stale" : ""}`}>
      <table style={{ whiteSpace: "nowrap" }}>
        <thead>
          <tr>
            <th>{t("th.species")}</th>
            <th><WikiLink page="foundations/spin-and-multiplicity">{t("grid.thGround")}</WikiLink></th>
            <th><WikiLink page="techniques/fragmentation" anchor="verdicts">{t("th.verdict")}</WikiLink></th>
            {QUANTITIES.map((q) => (
              <th key={q.value} className="num">
                <button type="button" className="column-pick" aria-pressed={q.value === quantity}
                  title={t(`q.${q.value}` as Key)} onClick={() => select(q.value)}>{q.label}</button>
              </th>
            ))}
            <th><WikiLink page="techniques/fragmentation">{t("grid.thChannel", { q: quantity === "d_g" ? "D_G" : "D_e" })}</WikiLink></th>
            <th><WikiLink page="foundations/units-language-or-physics">{t("th.units")}</WikiLink></th>
            <th><WikiLink page="techniques/point-groups">{t("th.pointGroup")}</WikiLink></th><th>{t("grid.thOther")}</th>
          </tr>
        </thead>
        <tbody>
          {cells.map((c) => {
            const g = c.ground;
            if (!g) return null;
            const r = rung(g, quantity);
            const channel = channelFor(g, quantity);
            return (
              <tr key={`${c.m},${c.charge}`}>
                <td>{species(c.m, c.charge)}</td>
                <td><Link to={`/c/${campaign}/s/${c.m}/${c.charge}/${g.mult}${search ? `?${search}` : ""}`}>{pretty(g.label)}</Link></td>
                <td>
                  <span className="verdict-cell">
                    {colorBy === "verdict" && <span className="swatch" style={{ background: VERDICT_FILL[r], border: "1px solid var(--border)" }} />}
                    {verdictLabel(t, r)}{entropyLimited(g, quantity) ? " *" : ""}
                  </span>
                </td>
                {QUANTITIES.map((q) => {
                  const v = g[q.value];
                  const picked = q.value === quantity;
                  const step = valueStep(v);
                  return (
                    <td key={q.value} className={`num${picked ? " picked" : ""}`}
                      aria-label={picked ? `${qLabel} ${fmt(v, 3, "eV")}` : undefined}
                      style={picked && colorBy === "value" ? { background: step.fill, color: step.ink } : undefined}>
                      {signed(v, 3)}
                    </td>
                  );
                })}
                <td>{channel ? pretty(channel) : "–"}</td>
                <td>{g.units ? pretty(g.units) : "–"}</td>
                <td>{g.point_group ?? "–"}</td>
                <td className="secondary">{c.states.filter((s) => s.mult !== g.mult).map((s) => `${s.mult}: ${shortRung(t, s, quantity)}`).join(", ")}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <p className="hint" style={{ position: "sticky", left: 0, margin: "8px 0 0" }}>{t("grid.tableCaption")}</p>
    </div>
  );
}
