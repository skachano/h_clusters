// View 5b: the operational side of HTC — job states, cost per stage, failures.
import { useParams } from "react-router-dom";
import { useJobsSummary } from "../api/client";
import { RawFiles } from "../components/RawFiles";
import { Histogram } from "../components/charts/Histogram";
import { duration, pretty } from "../lib/format";
import { useT } from "../i18n";
import { statusName } from "../i18n/terms";

const STATUS_ORDER = ["done", "dissociated", "failed", "running", "pending"];

export function JobsView() {
  const { campaign = "baseline" } = useParams();
  const summary = useJobsSummary(campaign);
  const t = useT();
  const s = summary.data;
  const total = s ? Object.values(s.counts).reduce((a, b) => a + b, 0) : 0;
  const cpu = s ? s.stages.reduce((a, x) => a + x.cpu_hours, 0) : 0;

  return (
    <div className="stack">
      <div>
        <h1>{t("jobs.title")}</h1>
        <p className="lede">{t("jobs.lede")}</p>
      </div>
      {summary.isError && <p className="error">{String(summary.error)}</p>}
      {summary.isPending && <p className="loading">{t("common.loading")}</p>}
      {s && (
        <>
          <div className="card row" style={{ gap: 32 }}>
            <div className="stat"><span className="label">{t("jobs.jobs")}</span><span className="value">{total.toLocaleString()}</span></div>
            {STATUS_ORDER.filter((k) => s.counts[k]).map((k) => (
              <div className="stat" key={k}><span className="label">{statusName(t, k)}</span><span className="value">{s.counts[k].toLocaleString()}</span></div>
            ))}
            <div className="stat"><span className="label">{t("jobs.cpu")}</span><span className="value">{cpu.toFixed(0)} h</span></div>
          </div>

          <div className="card table-wrap">
            <h2 style={{ marginBottom: 8 }}>{t("jobs.stages")}</h2>
            <table>
              <thead>
                <tr><th>{t("jobs.stage")}</th><th>{t("jobs.level")}</th>{STATUS_ORDER.map((k) => <th key={k} className="num">{statusName(t, k)}</th>)}<th className="num">{t("jobs.retried")}</th><th className="num">{t("jobs.median")}</th><th className="num">{t("jobs.cpuH")}</th></tr>
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
            <h2 style={{ marginBottom: 8 }}>{t("jobs.runTimes")}</h2>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(min(100%, 280px), 1fr))", gap: 16 }}>
              {s.stages.map((st) => (
                <div className="card" key={st.stage} style={{ padding: 12 }}>
                  <h3 style={{ marginBottom: 4, textTransform: "none", letterSpacing: 0 }}><code>{st.stage}</code> · {st.level}</h3>
                  <Histogram edges={st.histogram_edges_s} counts={st.histogram_counts} label={t("jobs.runTimesOf", { stage: st.stage })} />
                </div>
              ))}
            </div>
          </div>

          <div className="card table-wrap">
            <h2 style={{ marginBottom: 8 }}>{t("jobs.failures", { n: s.failures.length })}</h2>
            {s.failures.length === 0 ? <p className="muted">{t("jobs.noFailures")}</p> : (
              <table>
                <thead><tr><th>{t("jobs.job")}</th><th>{t("th.state")}</th><th>{t("jobs.stage")}</th><th>{t("jobs.kind")}</th><th className="num">{t("jobs.attempts")}</th><th>{t("jobs.error")}</th><th>{t("jobs.files")}</th></tr></thead>
                <tbody>
                  {s.failures.map((f) => (
                    <tr key={f.job_id}>
                      <td className="num">{f.job_id}</td>
                      <td>{pretty(f.label)}</td>
                      <td><code>{f.stage}</code></td>
                      <td>{f.error_kind ?? "–"}</td>
                      <td className="num">{f.attempts}</td>
                      <td className="secondary">{f.error}</td>
                      <td><RawFiles jobId={f.job_id} names={["job.out"]} /></td>
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
