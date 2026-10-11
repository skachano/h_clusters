// Typed API client: paths and payloads come from api/openapi.json (npm run gen:api).
import createClient from "openapi-fetch";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];
export type GridOut = Schemas["GridOut"];
export type GridCell = Schemas["GridCell"];
export type StateBrief = Schemas["StateBrief"];
export type StateDetail = Schemas["StateDetail"];
export type TrendsOut = Schemas["TrendsOut"];
export type BenchmarkOut = Schemas["BenchmarkOut"];
export type JobsSummaryOut = Schemas["JobsSummaryOut"];
export type ModesOut = Schemas["ModesOut"];
export type Quantity = GridOut["quantity"];
export type TrendQuantity = TrendsOut["quantity"];
export type Verdict = StateBrief["verdict"];

// Same origin: the dev server (Vite) and nginx both proxy /api to the API service.
// fetch is looked up per request (not captured once), so tests can replace it.
export const api = createClient<paths>({
  baseUrl: globalThis.location?.origin ?? "",
  fetch: (request) => globalThis.fetch(request),
});

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

export const jobFileUrl = (jobId: number, name: string) => `/api/jobs/${jobId}/files/${name}`;
