// View 5b: the operational side of HTC — job states, cost per stage, failures.
import { useParams } from "react-router-dom";
import { jobFileUrl, useJobsSummary } from "../api/client";
import { Histogram } from "../components/charts/Histogram";
import { duration, pretty } from "../lib/format";

const STATUS_ORDER = ["done", "dissociated", "failed", "running", "pending"];

export function JobsView() {
  const { campaign = "baseline" } = useParams();
  const summary = useJobsSummary(campaign);
  const s = summary.data;
  const total = s ? Object.values(s.counts).reduce((a, b) => a + b, 0) : 0;
  const cpu = s ? s.stages.reduce((a, x) => a + x.cpu_hours, 0) : 0;

  return (
    <div className="stack">
      <div>
        <h1>Campaign dashboard</h1>
        <p className="lede">Every job of the campaign: where the compute went, what was retried, what failed and why.</p>
      </div>
      {summary.isError && <p className="error">{String(summary.error)}</p>}
      {summary.isPending && <p className="loading">Loading…</p>}
      {s && (
        <>
          <div className="card row" style={{ gap: 32 }}>
            <div className="stat"><span className="label">Jobs</span><span className="value">{total.toLocaleString()}</span></div>
            {STATUS_ORDER.filter((k) => s.counts[k]).map((k) => (
              <div className="stat" key={k}><span className="label">{k}</span><span className="value">{s.counts[k].toLocaleString()}</span></div>
            ))}
            <div className="stat"><span className="label">ORCA CPU time</span><span className="value">{cpu.toFixed(0)} h</span></div>
          </div>

          <div className="card table-wrap">
            <h2 style={{ marginBottom: 8 }}>Stages</h2>
            <table>
              <thead>
                <tr><th>Stage</th><th>Level</th>{STATUS_ORDER.map((k) => <th key={k} className="num">{k}</th>)}<th className="num">retried</th><th className="num">median run</th><th className="num">CPU h</th></tr>
              </thead>
              <tbody>
                {s.stages.map((st) => (
                  <tr key={st.stage}>
                    <td><code>{st.stage}</code></td><td>{st.level}</td>
                    {STATUS_ORDER.map((k) => <td key={k} className="num">{st.counts[k] ?? ""}</td>)}
                    <td className="num">{st.retried}</td>
                    <td className="num">{duration(st.wall_median_s)}</td>
                    <td className="num">{st.cpu_hours.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div>
            <h2 style={{ marginBottom: 8 }}>Run times per stage</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 280px), 1fr))", gap: 16 }}>
              {s.stages.map((st) => (
                <div className="card" key={st.stage} style={{ padding: 12 }}>
                  <h3 style={{ marginBottom: 4, textTransform: "none", letterSpacing: 0 }}><code>{st.stage}</code> · {st.level}</h3>
                  <Histogram edges={st.histogram_edges_s} counts={st.histogram_counts} label={`Run times of stage ${st.stage}`} />
                </div>
              ))}
            </div>
          </div>

          <div className="card table-wrap">
            <h2 style={{ marginBottom: 8 }}>Failures ({s.failures.length})</h2>
            {s.failures.length === 0 ? <p className="muted">None.</p> : (
              <table>
                <thead><tr><th>Job</th><th>State</th><th>Stage</th><th>Kind</th><th className="num">Attempts</th><th>Error</th><th>Files</th></tr></thead>
                <tbody>
                  {s.failures.map((f) => (
                    <tr key={f.job_id}>
                      <td className="num">{f.job_id}</td>
                      <td>{pretty(f.label)}</td>
                      <td><code>{f.stage}</code></td>
                      <td>{f.error_kind ?? "–"}</td>
                      <td className="num">{f.attempts}</td>
                      <td className="secondary">{f.error}</td>
                      <td><a href={jobFileUrl(f.job_id, "job.out")} target="_blank" rel="noreferrer">output</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
