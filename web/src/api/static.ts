// Static snapshot (GitHub Pages build, VITE_STATIC=1): every API request is answered by a
// JSON file exported by api/src/hclust_api/export.py. The URL -> file rule mirrors its
// `static_path`; temperature and pressure snap to the exported conditions grid.

export const STATIC = import.meta.env.VITE_STATIC === "1";

export interface Manifest {
  generated_at: string;
  commit: string | null;
  conditions: { temperatures: number[]; pressures: number[]; default: [number, number] };
  campaigns: string[];
  files: number;
  bytes: number;
  outputs: { file: string; files: number; jobs: number; bytes: number } | null;
}

/** Root of the exported data, under the site's base path (vite `base`). */
export const dataRoot = () => `${import.meta.env.BASE_URL}data/`;

let manifest: Promise<Manifest> | null = null;
export function loadManifest(): Promise<Manifest> {
  manifest ??= fetch(`${dataRoot()}manifest.json`).then((r) => {
    if (!r.ok) throw new Error(`no manifest (HTTP ${r.status})`);
    return r.json() as Promise<Manifest>;
  });
  return manifest;
}

/** Index of the grid value nearest to v, on a log scale. */
export function nearestIndex(values: number[], v: number): number {
  let best = 0;
  for (let i = 1; i < values.length; i++)
    if (Math.abs(Math.log(values[i] / v)) < Math.abs(Math.log(values[best] / v))) best = i;
  return best;
}

/** The exported file answering `url` (an /api/... URL), relative to the data root. */
export function staticPath(url: URL, grid: Manifest["conditions"]): string {
  if (!url.pathname.startsWith("/api/")) throw new Error(`not an API path: ${url.pathname}`);
  const rel = url.pathname.slice("/api/".length);
  const params = new URLSearchParams(url.search);
  const segment: string[] = [];
  const t = params.get("temperature"), p = params.get("pressure");
  if (t !== null && p !== null) {
    segment.push(`c${nearestIndex(grid.temperatures, Number(t))}-${nearestIndex(grid.pressures, Number(p))}`);
    params.delete("temperature");
    params.delete("pressure");
  }
  for (const k of [...params.keys()].sort()) segment.push(`${k}-${params.get(k)}`);
  const hasExtension = rel.slice(rel.lastIndexOf("/") + 1).includes(".");
  return rel + (segment.length ? `/${segment.join(",")}` : "") + (hasExtension ? "" : ".json");
}

/** fetch() for API requests in the static build. A missing file is a 404, as from the API. */
export async function staticFetch(request: Request): Promise<Response> {
  const { conditions } = await loadManifest();
  const file = staticPath(new URL(request.url), conditions);
  return globalThis.fetch(`${dataRoot()}${file}`);
}
