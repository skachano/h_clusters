// View 1: the periodic grid. Rows are charge, columns m; each cell is a species' ground state.
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useGrid, type GridCell, type Quantity } from "../api/client";
import { ConditionsBar } from "../components/ConditionsBar";
import { Thumbnail } from "../components/Thumbnail";
import { focusPoint, useTooltip } from "../components/Tooltip";
import { QUANTITIES, useConditions, type ColorBy } from "../lib/conditions";
import { fmt, pretty, signed, species } from "../lib/format";
import { VALUE_BINS, VERDICT_FILL, VERDICT_INK, VERDICT_LABEL, VERDICT_SHORT, valueStep } from "../lib/scales";

const CHARGES = [-1, 0, 1];
const MS = Array.from({ length: 10 }, (_, i) => i + 1);
const ROW_LABEL: Record<number, string> = { [-1]: "anions", 0: "neutral", 1: "cations" };

export function GridView() {
  const { campaign = "baseline" } = useParams();
  const { conditions, quantity, colorBy, update, search } = useConditions();
  const grid = useGrid(campaign, conditions, quantity);
  const [asTable, setAsTable] = useState(false);
  const tip = useTooltip();
  const qLabel = QUANTITIES.find((q) => q.value === quantity)?.label ?? quantity;

  const cells = new Map<string, GridCell>();
  for (const c of grid.data?.cells ?? []) cells.set(`${c.m},${c.charge}`, c);

  return (
    <div className="stack">
      <div>
        <h1>Which hydrogen clusters hold together?</h1>
        <p className="lede">
          Each cell is the lowest-energy spin state of H<sub>m</sub><sup>n</sup> at CCSD(T)/aug-cc-pVTZ.
          D is the energy needed to break it apart along its weakest spin-allowed channel:
          positive means bound. Move the temperature to see who survives.
        </p>
      </div>
      <ConditionsBar conditions={conditions} quantity={quantity} colorBy={colorBy} update={update}>
        <div className="control">
          <span className="label">View</span>
          <div className="segmented" role="group" aria-label="View">
            <button type="button" aria-pressed={!asTable} onClick={() => setAsTable(false)}>Grid</button>
            <button type="button" aria-pressed={asTable} onClick={() => setAsTable(true)}>Table</button>
          </div>
        </div>
      </ConditionsBar>
      <ScaleLegend colorBy={colorBy} quantityLabel={qLabel} />

      {grid.isError && <p className="error">Could not load the grid: {String(grid.error)}</p>}
      {grid.isPending && <p className="loading">Loading…</p>}
      {grid.data && !asTable && (
        <div className={`card ${grid.isPlaceholderData ? "stale" : ""}`} style={{ overflowX: "auto", padding: 12 }}>
          <div className="periodic" role="grid" aria-label="Species grid">
            <div role="row" className="periodic-row">
              <div className="periodic-corner" />
              {MS.map((m) => <div key={m} role="columnheader" className="periodic-head num">m = {m}</div>)}
            </div>
            {CHARGES.map((charge) => (
              <div role="row" className="periodic-row" key={charge}>
                <div role="rowheader" className="periodic-rowhead">{ROW_LABEL[charge]}</div>
                {MS.map((m) => (
                  <Cell key={m} m={m} charge={charge} cell={cells.get(`${m},${charge}`)} colorBy={colorBy}
                    quantity={quantity} quantityLabel={qLabel} campaign={campaign} search={search} tip={tip} />
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

function Cell({ m, charge, cell, colorBy, quantity, quantityLabel, campaign, search, tip }: {
  m: number; charge: number; cell?: GridCell; colorBy: ColorBy; quantity: Quantity; quantityLabel: string;
  campaign: string; search: string; tip: ReturnType<typeof useTooltip>;
}) {
  if (!cell || !cell.ground) {
    const proton = m === 1 && charge === 1;
    return (
      <div role="gridcell" className="periodic-cell empty" style={{ background: "var(--none)" }}>
        <div className="cell-name">{species(m, charge)}</div>
        <div className="cell-verdict">{proton ? "bare proton" : "not computed"}</div>
      </div>
    );
  }
  const g = cell.ground;
  const step = valueStep(cell.value);
  const fill = colorBy === "verdict" ? VERDICT_FILL[g.verdict] : step.fill;
  const ink = colorBy === "verdict" ? VERDICT_INK[g.verdict] : step.ink;
  const details = (
    <div>
      <div className="tt-value">{pretty(g.label)} · {VERDICT_LABEL[g.verdict]}</div>
      <div className="tt-label">{quantityLabel} {signed(cell.value, 3, "eV")}{g.channel ? ` → ${pretty(quantity === "d_g" ? g.channel_g ?? g.channel : g.channel)}` : ""}</div>
      {g.composition && <div className="tt-label">units {g.composition}{g.point_group ? ` · ${g.point_group}` : ""}</div>}
      {cell.states.length > 1 && (
        <div className="tt-label" style={{ marginTop: 4 }}>
          {cell.states.map((s) => `${s.mult === 1 ? "singlet" : `2S+1 = ${s.mult}`}: ${VERDICT_SHORT[s.verdict]}`).join(" · ")}
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
      aria-label={`${g.label}: ${VERDICT_LABEL[g.verdict]}, ${quantityLabel} ${fmt(cell.value, 3, "eV")}`}
      onPointerMove={(e) => tip.show(e.clientX, e.clientY, details)}
      onPointerLeave={tip.hide}
      onFocus={(e) => tip.show(...focusPoint(e), details)}
      onBlur={tip.hide}
    >
      <div className="cell-top">
        <span className="cell-name">{species(m, charge)}</span>
        <span className="cell-mult num" title="multiplicity 2S+1">{g.mult}</span>
      </div>
      <div className="cell-thumb">{cell.xyz ? <Thumbnail xyz={cell.xyz} bonds={cell.bonds} size={52} ink={ink} /> : <span className="cell-none">—</span>}</div>
      <div className="cell-verdict">{VERDICT_SHORT[g.verdict]}</div>
      <div className="cell-value num">{cell.value == null ? " " : signed(cell.value, cell.value !== 0 && Math.abs(cell.value) < 0.1 ? 3 : 2)}</div>
    </Link>
  );
}

function ScaleLegend({ colorBy, quantityLabel }: { colorBy: ColorBy; quantityLabel: string }) {
  if (colorBy === "verdict") {
    return (
      <div className="legend" aria-label="Colour key">
        <span className="legend-item"><span className="swatch" style={{ background: "var(--none)", border: "1px solid var(--border)" }} />no stable structure / atom</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-1)" }} />metastable (D_e &lt; 0)</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-2)" }} />bound, not once ZPE is included</span>
        <span className="legend-item"><span className="swatch" style={{ background: "var(--ord-3)" }} />bound with ZPE</span>
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
    <div className="legend" aria-label="Colour key">
      <span>{quantityLabel} (eV): falls apart</span>
      {steps.map((s) => (
        <span className="legend-item" key={s.label}><span className="swatch" style={{ background: s.fill }} />{s.label}</span>
      ))}
      <span>bound</span>
    </div>
  );
}

function GridTable({ cells, quantityLabel, campaign, search }: { cells: GridCell[]; quantityLabel: string; campaign: string; search: string }) {
  return (
    <div className="card table-wrap">
      <table>
        <thead>
          <tr><th>Species</th><th>Ground state</th><th>Verdict</th><th className="num">{quantityLabel} (eV)</th><th>Weakest channel</th><th>Units</th><th>Point group</th><th>Other states</th></tr>
        </thead>
        <tbody>
          {cells.map((c) => c.ground && (
            <tr key={`${c.m},${c.charge}`}>
              <td>{species(c.m, c.charge)}</td>
              <td><Link to={`/c/${campaign}/s/${c.m}/${c.charge}/${c.ground.mult}${search ? `?${search}` : ""}`}>{pretty(c.ground.label)}</Link></td>
              <td>{VERDICT_LABEL[c.ground.verdict]}</td>
              <td className="num">{signed(c.value, 3)}</td>
              <td>{c.ground.channel ? pretty(c.ground.channel) : "–"}</td>
              <td>{c.ground.composition ?? "–"}</td>
              <td>{c.ground.point_group ?? "–"}</td>
              <td className="secondary">{c.states.filter((s) => s.mult !== c.ground!.mult).map((s) => `${s.mult}: ${VERDICT_SHORT[s.verdict]}`).join(", ")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
