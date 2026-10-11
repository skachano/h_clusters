// View 5a: how well the geometry levels' own energies reproduce CCSD(T).
import { useParams } from "react-router-dom";
import { useBenchmark, type BenchmarkOut } from "../api/client";
import { ParityChart } from "../components/charts/ParityChart";
import { pretty, signed } from "../lib/format";
import { CHARGE_COLOR, CHARGE_LABEL } from "../lib/scales";

const LEVELS = [
  { test: "L1", name: "ωB97X-D4/def2-TZVPPD" },
  { test: "L1M", name: "RI-MP2/aug-cc-pVTZ" },
];

export function BenchmarkView() {
  const { campaign = "baseline" } = useParams();
  return (
    <div className="stack">
      <div>
        <h1>Method benchmark</h1>
        <p className="lede">
          D_e of every state computed with the geometry level's own energies, against CCSD(T)/aug-cc-pVTZ
          on the same structures. Points on the diagonal agree; the anions are where cheap methods fail.
        </p>
      </div>
      <div className="cols-2">
        {LEVELS.map((l) => <Panel key={l.test} campaign={campaign} test={l.test} name={l.name} />)}
      </div>
    </div>
  );
}

function Panel({ campaign, test, name }: { campaign: string; test: string; name: string }) {
  const b = useBenchmark(campaign, test);
  return (
    <div className="card stack" style={{ gap: 12 }}>
      <h2>{name}</h2>
      {b.isError && <p className="error">{String(b.error)}</p>}
      {b.isPending && <p className="loading">Loading…</p>}
      {b.data && <PanelBody b={b.data} name={name} />}
    </div>
  );
}

function PanelBody({ b, name }: { b: BenchmarkOut; name: string }) {
  const worst = [...b.points].sort((x, y) => Math.abs(y.test - y.reference) - Math.abs(x.test - x.reference)).slice(0, 6);
  return (
    <>
      <div className="row" style={{ gap: 24 }}>
        <div className="stat"><span className="label">States</span><span className="value">{b.n}</span></div>
        <div className="stat"><span className="label">Mean absolute error</span><span className="value">{b.mae?.toFixed(3) ?? "–"} eV</span></div>
        <div className="stat"><span className="label">Largest error</span><span className="value">{b.max_abs?.toFixed(2) ?? "–"} eV</span></div>
      </div>
      <ParityChart
        xLabel="D_e, CCSD(T)" yLabel={`D_e, ${name.split("/")[0]}`} unit="eV"
        groups={[-1, 0, 1].map((c) => ({ key: c, label: CHARGE_LABEL[c], color: CHARGE_COLOR[c] }))}
        points={b.points.map((p) => ({ key: p.label, label: pretty(p.label), x: p.reference, y: p.test, group: p.charge }))}
      />
      <div className="table-wrap">
        <table>
          <thead><tr><th>Largest errors</th><th className="num">CCSD(T)</th><th className="num">{name.split("/")[0]}</th><th className="num">error (eV)</th></tr></thead>
          <tbody>
            {worst.map((p) => (
              <tr key={p.label}>
                <td>{pretty(p.label)}</td>
                <td className="num">{signed(p.reference, 3)}</td>
                <td className="num">{signed(p.test, 3)}</td>
                <td className="num">{signed(p.test - p.reference, 3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
