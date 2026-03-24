export interface Memory {
  id: string;
  content: string;
  type: MemoryTypeValue;
  project: string | null;
  tags: string[];
  token_count: number;
  source: string | null;
  source_session: string | null;
  created_at: string;
  last_accessed: string | null;
  access_count: number;
  elaboration_date: string | null;
  elaboration_count: number;
  decay_score: number;
  is_deprecated: boolean;
  deprecated_by: string | null;
  file_path: string | null;
  code_signature: string | null;
}

export type MemoryTypeValue = "semantic" | "episodic" | "procedural";

export interface ConnectedMemory {
  id: string;
  content: string;
  type: MemoryTypeValue;
  project: string | null;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  from_id?: string;
  to_id?: string;
  weight: number;
  type: string;
  created_at?: string;
  last_reinforced?: string | null;
  reinforce_count?: number;
  connected_memory?: ConnectedMemory;
}

export interface Session {
  id: string;
  project: string | null;
  run_type: string | null;
  run_name: string | null;
  started_at: string;
  extracted_at: string | null;
  memories_extracted: number;
  raw_token_count: number | null;
  notes: string | null;
}

export interface ElaborationLog {
  id: string;
  started_at: string;
  completed_at: string | null;
  seed_count: number | null;
  working_set: number | null;
  new_memories: number;
  updated_memories: number;
  deprecated_memories: number;
  new_edges: number;
  updated_edges: number;
  summary: string | null;
  status: string;
}

export interface OperationLog {
  id: string;
  tool: string;
  project: string | null;
  params: string | null;
  result: string | null;
  status: string;
  duration_ms: number | null;
  started_at: string;
  completed_at: string | null;
}

export interface Stats {
  total_memories: number;
  total_deprecated: number;
  by_type: Record<string, number>;
  by_project: Record<string, number>;
  total_edges: number;
  edge_by_type: Record<string, number>;
  avg_connections_per_memory: number;
  memories_never_accessed: number;
  memories_never_elaborated: number;
  oldest_unelaborated: string | null;
  last_extraction: string | null;
  last_elaboration: string | null;
  health_score: number;
  alerts: HealthAlert[];
}

export interface HealthAlert {
  severity: "warning" | "info" | "error";
  message: string;
  action: string;
}

export interface GraphNode {
  id: string;
  label: string;
  type: MemoryTypeValue;
  project: string | null;
  access_count: number;
  decay_score: number;
  token_count: number;
  is_deprecated: boolean;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  weight: number;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Project {
  name: string;
  count: number;
}

export interface AdvancedStats {
  total_memories: number;
  total_edges: number;
  graph: {
    avg_degree: number;
    median_degree: number;
    degree_histogram: Record<string, number>;
    under_connected_0_1: number;
    hubs_10_plus: number;
    connected_components: number;
    largest_component: number;
    largest_component_pct: number;
    isolated_nodes: number;
    edge_types: Record<string, number>;
    typed_edge_ratio: number;
    has_contradicts: boolean;
    has_supersedes: boolean;
  };
  access: {
    gini_coefficient: number;
    never_accessed: number;
    never_accessed_pct: number;
    total_accesses: number;
    top_10_access_counts: number[];
  };
  elaboration: {
    avg_count: number;
    distribution: Record<string, number>;
  };
  memory_quality: {
    type_distribution: Record<string, number>;
    avg_tokens: number;
    min_tokens: number;
    max_tokens: number;
    decay_distribution: Record<string, number>;
  };
  health_score: number;
  health_breakdown: {
    graph_connectivity: number;
    edge_diversity: number;
    elaboration_depth: number;
    access_balance: number;
    component_unity: number;
  };
  growth_timeline: { date: string; total: number; new: number; total_edges: number }[];
}

export interface Prescription {
  metric: string;
  current: number;
  target: (number | null)[];
  severity: "warning" | "optimize" | "info";
  diagnosis: string;
  why_it_matters?: string;
  action: string;
  focus: string | null;
  expected_improvement: string;
  rounds: number;
}

export interface DiagnoseResponse {
  health_score: number;
  maturity: string;
  total_memories: number;
  total_edges: number;
  prescriptions: Prescription[];
  metrics: Record<string, number | boolean>;
}

// ── Setup Progress ────────────────────────────────────────────────────

export type SetupStepStatus = "pending" | "in_progress" | "completed" | "skipped" | "failed";

export interface SetupStep {
  phase: string;
  step: string;
  order_index: number;
  title: string;
  description: string;
  status: SetupStepStatus;
  prompt_file: string | null;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
}

export interface SetupSummary {
  project: string;
  initialized: boolean;
  total_steps: number;
  completed: number;
  skipped: number;
  progress_pct: number;
  is_ready: boolean;
  current_step: {
    phase: string;
    step: string;
    title: string;
    description: string;
    status: string;
    prompt_file: string | null;
  } | null;
  steps?: SetupStep[];
}

export interface ProjectSetup {
  project: string;
  initialized: boolean;
  total_steps?: number;
  completed?: number;
  progress_pct?: number;
  is_ready?: boolean;
}
