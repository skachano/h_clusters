// Typed API client: paths and payloads come from api/openapi.json (npm run gen:api).
import createClient from "openapi-fetch";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { components, paths } from "./schema";
import { loadManifest, STATIC, staticFetch } from "./static";

export type Schemas = components["schemas"];
export type GridOut = Schemas["GridOut"];
export type GridCell = Schemas["GridCell"];
export type StateBrief = Schemas["StateBrief"];
export type StateDetail = Schemas["StateDetail"];
export type TrendsOut = Schemas["TrendsOut"];
export type BenchmarkOut = Schemas["BenchmarkOut"];
export type JobsSummaryOut = Schemas["JobsSummaryOut"];
export type ModesOut = Schemas["ModesOut"];
export type BondsOut = Schemas["BondsOut"];
export type BondOrder = Schemas["BondOrder"];
export type Quantity = GridOut["quantity"];
export type TrendQuantity = TrendsOut["quantity"];
export type Verdict = StateBrief["verdict"];

// Same origin: the dev server (Vite) and nginx both proxy /api to the API service; the
// static build (GitHub Pages) answers from exported files instead (static.ts).
// fetch is looked up per request (not captured once), so tests can replace it.
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  fetch: (request) => (STATIC ? staticFetch(request) : globalThis.fetch(request)),
});

/** fetch() for API paths outside the typed client (e.g. the .xyz text). */
export const fetchApi = (path: string) => {
  const request = new Request(new URL(path, globalThis.location?.origin ?? "http://localhost"));
  return STATIC ? staticFetch(request) : globalThis.fetch(request);
};

/** The static build's manifest (conditions grid, export date); null in the live app. */
export const useManifest = () =>
  useQuery({ queryKey: ["manifest"], enabled: STATIC, staleTime: Infinity, queryFn: loadManifest });

async function unwrap<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  const { data, error, response } = await request;
  if (data === undefined) {
    const detail = (error as { detail?: unknown } | undefined)?.detail;
    throw new Error(typeof detail === "string" ? detail : `HTTP ${response.status}`);
  }
  return data;
}

export interface Conditions {
  temperature: number;
  pressure: number;
}

export const useCampaigns = () =>
  useQuery({ queryKey: ["campaigns"], queryFn: () => unwrap(api.GET("/api/campaigns")) });

export const useGrid = (campaign: string, c: Conditions, quantity: Quantity) =>
  useQuery({
    queryKey: ["grid", campaign, c.temperature, c.pressure, quantity],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/grid", {
        params: { path: { campaign }, query: { ...c, quantity } },
      })),
    placeholderData: keepPreviousData, // refetch keeps the frame
  });

export const useStateDetail = (campaign: string, m: number, charge: number, mult: number, c: Conditions) =>
  useQuery({
    queryKey: ["state", campaign, m, charge, mult, c.temperature, c.pressure],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/states/{m}/{charge}/{mult}", {
        params: { path: { campaign, m, charge, mult }, query: c },
      })),
    placeholderData: keepPreviousData,
  });

export const useTrends = (campaign: string, quantity: TrendQuantity, c: Conditions) =>
  useQuery({
    queryKey: ["trends", campaign, quantity, c.temperature, c.pressure],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/trends", {
        params: { path: { campaign }, query: { quantity, ...c } },
      })),
    placeholderData: keepPreviousData,
  });

export const useBenchmark = (campaign: string, test: string) =>
  useQuery({
    queryKey: ["benchmark", campaign, test],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/benchmark", {
        params: { path: { campaign }, query: { test } },
      })),
  });

export const useJobsSummary = (campaign: string) =>
  useQuery({
    queryKey: ["jobs", campaign],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/jobs/summary", { params: { path: { campaign } } })),
  });

export const useModes = (structureId: number | null | undefined) =>
  useQuery({
    queryKey: ["modes", structureId],
    enabled: structureId != null,
    retry: false,
    queryFn: () =>
      unwrap(api.GET("/api/structures/{structure_id}/modes", {
        params: { path: { structure_id: structureId as number } },
      })),
  });

export const useBonds = (structureId: number | null | undefined) =>
  useQuery({
    queryKey: ["bonds", structureId],
    enabled: structureId != null,
    retry: false,
    queryFn: () =>
      unwrap(api.GET("/api/structures/{structure_id}/bonds", {
        params: { path: { structure_id: structureId as number } },
      })),
  });

export const useStudies = (campaign: string) =>
  useQuery({
    queryKey: ["studies", campaign],
    queryFn: () => unwrap(api.GET("/api/campaigns/{campaign}/studies", { params: { path: { campaign } } })),
  });

export const useStudy = (campaign: string, name: string) =>
  useQuery({
    queryKey: ["study", campaign, name],
    queryFn: () =>
      unwrap(api.GET("/api/campaigns/{campaign}/studies/{name}", { params: { path: { campaign, name } } })),
  });

/**
 * Link to a raw ORCA file. The static site has no per-file links: they all point to the
 * release archive (null when the build was not given one), see rawFilePath.
 */
export const jobFileUrl = (jobId: number, name: string): string | null =>
  STATIC ? (import.meta.env.VITE_OUTPUTS_URL || null) : `/api/jobs/${jobId}/files/${name}`;

/** Where a raw file sits inside the static site's archive. */
export const rawFilePath = (jobId: number, name: string) => `outputs/${jobId}/${name}`;
