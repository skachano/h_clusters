// Links to a job's raw ORCA files. The live app serves each file; the static site has one
// archive (a GitHub Release asset) and names each file's path inside it.
import { jobFileUrl, rawFilePath } from "../api/client";
import { STATIC } from "../api/static";

const LABEL: Record<string, string> = { "job.inp": "input", "job.out": "output" };

export function RawFiles({ jobId, names, record = false }: { jobId: number; names: string[]; record?: boolean }) {
  if (STATIC) {
    const archive = jobFileUrl(jobId, names[0]);
    const where = names.map((n) => rawFilePath(jobId, n)).join(", ");
    return archive ? (
      <span>
        <a href={archive}>outputs archive</a> <span className="secondary">({where})</span>
      </span>
    ) : (
      <span className="secondary">not included in this snapshot</span>
    );
  }
  return (
    <span>
      {names.map((n, i) => (
        <span key={n}>
          {i > 0 && " · "}
          <a href={jobFileUrl(jobId, n)!} target="_blank" rel="noreferrer">{LABEL[n] ?? n}</a>
        </span>
      ))}
      {record && (
        <> · <a href={`/api/jobs/${jobId}`} target="_blank" rel="noreferrer">job record</a></>
      )}
    </span>
  );
}
