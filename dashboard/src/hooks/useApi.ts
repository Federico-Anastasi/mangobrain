import { useState, useEffect, useCallback } from "react";
import type { Memory, Edge, Stats, GraphData, Session, ElaborationLog, Project, HealthAlert, AdvancedStats, DiagnoseResponse, SetupSummary, ProjectSetup } from "../types/index.ts";

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

function useFetch<T>(url: string, deps: unknown[] = []): FetchState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [trigger, setTrigger] = useState(0);

  const refetch = useCallback(() => setTrigger((t) => t + 1), []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
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
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, trigger, ...deps]);

  return { data, loading, error, refetch };
}

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

export function useMemories(filters: MemoryFilters = {}) {
  const params = new URLSearchParams();
  if (filters.project) params.set("project", filters.project);
  if (filters.type) params.set("type", filters.type);
  if (filters.search) params.set("search", filters.search);
  if (filters.tags) params.set("tags", filters.tags);
  if (filters.sort) params.set("sort", filters.sort);
  if (filters.deprecated) params.set("deprecated", "true");
  params.set("limit", String(filters.limit ?? 50));
  params.set("offset", String(filters.offset ?? 0));

  return useFetch<PaginatedResponse<Memory>>(`/api/memories?${params.toString()}`, [
    filters.project, filters.type, filters.search, filters.tags, filters.sort, filters.deprecated, filters.limit, filters.offset,
  ]);
}

export function useMemory(id: string | null) {
  return useFetch<{ memory: Memory; edges: Edge[] }>(
    id ? `/api/memories/${id}` : "/api/health", // fallback
    [id]
  );
}

export function useStats(project?: string) {
  const url = project ? `/api/stats/${project}` : "/api/stats";
  return useFetch<Stats>(url, [project]);
}

export function useGraph(project?: string, minWeight = 0) {
  const params = new URLSearchParams();
  if (minWeight > 0) params.set("min_weight", String(minWeight));
  const base = project ? `/api/graph/${project}` : "/api/graph";
  return useFetch<GraphData>(`${base}?${params.toString()}`, [project, minWeight]);
}

export function useSessions(project?: string) {
  const params = project ? `?project=${project}` : "";
  return useFetch<{ items: Session[] }>(`/api/sessions${params}`, [project]);
}

export function useElaborations() {
  return useFetch<{ items: ElaborationLog[] }>("/api/elaborations");
}

export function useProjects() {
  return useFetch<{ projects: Project[] }>("/api/projects");
}

export function useDiagnose(project?: string) {
  const url = project ? `/api/diagnose/${project}` : "/api/diagnose";
  return useFetch<DiagnoseResponse>(url, [project]);
}

export function useAdvancedStats(project?: string) {
  const url = project ? `/api/stats/advanced/${project}` : "/api/stats/advanced";
  return useFetch<AdvancedStats>(url, [project]);
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

export function useSetupAll() {
  return useFetch<ProjectSetup[]>("/api/setup");
}

export function useSetup(project: string | null) {
  return useFetch<SetupSummary>(
    project ? `/api/setup/${project}` : "/api/health",
    [project]
  );
}
