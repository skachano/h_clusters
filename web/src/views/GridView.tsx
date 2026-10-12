// View 1: the periodic grid. Rows are charge, columns m; each cell is a species' ground state.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGrid, type GridCell, type Quantity } from "../api/client";
import { ConditionsBar } from "../components/ConditionsBar";
import { Thumbnail } from "../components/Thumbnail";
import { focusPoint, useTooltip } from "../components/Tooltip";
import { QUANTITIES, useConditions, type ColorBy } from "../lib/conditions";
import { fmt, pretty, signed, species } from "../lib/format";
import { VALUE_BINS, VERDICT_FILL, VERDICT_INK, valueStep } from "../lib/scales";
import { useT, type T } from "../i18n";
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
      <ScaleLegend colorBy={colorBy} quantityLabel={qLabel} />

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
      {grid.data && asTable && <GridTable cells={grid.data.cells} quantityLabel={qLabel} campaign={campaign} search={search} />}
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
  const step = valueStep(cell.value);
  const fill = colorBy === "verdict" ? VERDICT_FILL[g.verdict] : step.fill;
  const ink = colorBy === "verdict" ? VERDICT_INK[g.verdict] : step.ink;
  const details = (
    <div>
      <div className="tt-value">{pretty(g.label)} · {verdictLabel(t, g.verdict)}</div>
      <div className="tt-label">{quantityLabel} {signed(cell.value, 3, "eV")}{g.channel ? ` → ${pretty(quantity === "d_g" ? g.channel_g ?? g.channel : g.channel)}` : ""}</div>
      {g.units && <div className="tt-label">{t("grid.units", { units: pretty(g.units) })}{g.point_group ? ` · ${g.point_group}` : ""}</div>}
      {cell.states.length > 1 && (
        <div className="tt-label" style={{ marginTop: 4 }}>
          {cell.states.map((s) => `${multName(t, s.mult)}: ${verdictShort(t, s.verdict)}`).join(" · ")}
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
      aria-label={`${g.label}: ${verdictLabel(t, g.verdict)}, ${quantityLabel} ${fmt(cell.value, 3, "eV")}`}
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
      <div className="cell-verdict">{verdictShort(t, g.verdict)}</div>
      <div className="cell-value num">{cell.value == null ? " " : signed(cell.value, cell.value !== 0 && Math.abs(cell.value) < 0.1 ? 3 : 2)}</div>
    </Link>
  );
}

function ScaleLegend({ colorBy, quantityLabel }: { colorBy: ColorBy; quantityLabel: string }) {
  const t = useT();
  if (colorBy === "verdict") {
    return (
      <div className="legend" aria-label={t("legend.aria")}>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--none)", border: "1px solid var(--border)" }} />{t("legend.none")}</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-1)" }} />{t("legend.metastable")}</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-2)" }} />{t("legend.bound")}</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-3)" }} />{t("legend.boundZpe")}</span>
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
    </div>
  );
}

function GridTable({ cells, quantityLabel, campaign, search }: { cells: GridCell[]; quantityLabel: string; campaign: string; search: string }) {
  const t = useT();
  return (
    <div className="card table-wrap">
      <table>
        <thead>
          <tr><th>{t("th.species")}</th><th>{t("grid.thGround")}</th><th>{t("th.verdict")}</th><th className="num">{quantityLabel} (eV)</th><th>{t("grid.thWeakest")}</th><th>{t("th.units")}</th><th>{t("th.pointGroup")}</th><th>{t("grid.thOther")}</th></tr>
        </thead>
        <tbody>
          {cells.map((c) => c.ground && (
            <tr key={`${c.m},${c.charge}`}>
              <td>{species(c.m, c.charge)}</td>
              <td><Link to={`/c/${campaign}/s/${c.m}/${c.charge}/${c.ground.mult}${search ? `?${search}` : ""}`}>{pretty(c.ground.label)}</Link></td>
              <td>{verdictLabel(t, c.ground.verdict)}</td>
              <td className="num">{signed(c.value, 3)}</td>
              <td>{c.ground.channel ? pretty(c.ground.channel) : "–"}</td>
              <td>{c.ground.units ? pretty(c.ground.units) : "–"}</td>
              <td>{c.ground.point_group ?? "–"}</td>
              <td className="secondary">{c.states.filter((s) => s.mult !== c.ground!.mult).map((s) => `${s.mult}: ${verdictShort(t, s.verdict)}`).join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
