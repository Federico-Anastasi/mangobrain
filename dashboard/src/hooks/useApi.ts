import { useState, useEffect, useCallback, useRef } from "react";
import type { Memory, Edge, Stats, GraphData, Session, OperationLog, Project, HealthAlert, AdvancedStats, DiagnoseResponse, SetupSummary, ProjectSetup } from "../types/index.ts";

const BASE_URL = "http://localhost:3101";

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

interface FetchState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

interface UseFetchOptions {
  /** Polling interval in ms. 0 = no polling. */
  pollInterval?: number;
}

function useFetch<T>(url: string, deps: unknown[] = [], options: UseFetchOptions = {}): FetchState<T> {
  const { pollInterval = 0 } = options;
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);
  const isPolling = useRef(false);

  const refetch = useCallback(() => setTrigger((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;

    const doFetch = () => {
      // Only show loading spinner on first fetch, not on poll refreshes
      if (!isPolling.current) setLoading(true);
      setError(null);

      fetch(`${BASE_URL}${url}`)
        .then((res) => {
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          return res.json();
        })
        .then((d: T) => {
          if (!cancelled) setData(d);
        })
        .catch((e: Error) => {
          if (!cancelled) setError(e.message);
        })
        .finally(() => {
          if (!cancelled) {
            setLoading(false);
            isPolling.current = true;
          }
        });
    };

    isPolling.current = false;
    doFetch();

    let intervalId: ReturnType<typeof setInterval> | undefined;
    if (pollInterval > 0) {
      intervalId = setInterval(doFetch, pollInterval);
    }

    return () => {
      cancelled = true;
      if (intervalId) clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, trigger, pollInterval, ...deps]);

  return { data, loading, error, refetch };
}

// ── Default poll interval ────────────────────────────────────────────────
const POLL_30S: UseFetchOptions = { pollInterval: 30_000 };

// ── Hooks ────────────────────────────────────────────────────────────────

export interface MemoryFilters {
  project?: string;
  type?: string;
  search?: string;
  tags?: string;
  sort?: string;
  deprecated?: boolean;
  limit?: number;
  offset?: number;
}

export function useMemories(filters: MemoryFilters = {}, poll = false) {
  const params = new URLSearchParams();
  if (filters.project) params.set("project", filters.project);
  if (filters.type) params.set("type", filters.type);
  if (filters.search) params.set("search", filters.search);
  if (filters.tags) params.set("tags", filters.tags);
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.deprecated) params.set("deprecated", "true");
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));

  return useFetch<PaginatedResponse<Memory>>(
    `/api/memories?${params.toString()}`,
    [filters.project, filters.type, filters.search, filters.tags, filters.sort, filters.deprecated, filters.limit, filters.offset],
    poll ? POLL_30S : {},
  );
}

export function useMemory(id: string | null) {
  return useFetch<{ memory: Memory; edges: Edge[] }>(
    id ? `/api/memories/${id}` : "/api/health", // fallback
    [id]
  );
}

export function useStats(project?: string, poll = false) {
  const url = project ? `/api/stats/${project}` : "/api/stats";
  return useFetch<Stats>(url, [project], poll ? POLL_30S : {});
}

export function useGraph(project?: string, minWeight = 0) {
  const params = new URLSearchParams();
  if (minWeight > 0) params.set("min_weight", String(minWeight));
  const base = project ? `/api/graph/${project}` : "/api/graph";
  return useFetch<GraphData>(`${base}?${params.toString()}`, [project, minWeight]);
}

export function useSessions(project?: string, poll = false) {
  const params = project ? `?project=${project}` : "";
  return useFetch<{ items: Session[] }>(`/api/sessions${params}`, [project], poll ? POLL_30S : {});
}

export function useOperations(project?: string, tool?: string, poll = false) {
  const params = new URLSearchParams();
  if (project) params.set("project", project);
  if (tool) params.set("tool", tool);
  params.set("limit", "100");
  return useFetch<{ items: OperationLog[] }>(`/api/operations?${params.toString()}`, [project, tool], poll ? POLL_30S : {});
}

export function useProjects(poll = false) {
  return useFetch<{ projects: Project[] }>("/api/projects", [], poll ? POLL_30S : {});
}

export function useDiagnose(project?: string, poll = false) {
  const url = project ? `/api/diagnose/${project}` : "/api/diagnose";
  return useFetch<DiagnoseResponse>(url, [project], poll ? POLL_30S : {});
}

export function useAdvancedStats(project?: string, poll = false) {
  const url = project ? `/api/stats/advanced/${project}` : "/api/stats/advanced";
  return useFetch<AdvancedStats>(url, [project], poll ? POLL_30S : {});
}

export function useHealth() {
  return useFetch<{
    status: string;
    service: string;
    health_score: number;
    total_memories: number;
    total_edges: number;
    alerts: HealthAlert[];
  }>("/api/health");
}

// ── Setup ─────────────────────────────────────────────────────────────

export function useSetupAll(poll = false) {
  return useFetch<ProjectSetup[]>("/api/setup", [], poll ? POLL_30S : {});
}

export function useSetup(project: string | null, poll = false) {
  return useFetch<SetupSummary>(
    project ? `/api/setup/${project}` : "/api/health",
    [project],
    poll ? POLL_30S : {},
  );
}
