import { useState } from "react";
import { useProject } from "../context/ProjectContext.tsx";
import { useAdvancedStats, useElaborations, useOperations, useDiagnose } from "../hooks/useApi.ts";
import type { Prescription, OperationLog } from "../types/index.ts";
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis,
  PieChart, Pie, Cell,
} from "recharts";
import { CheckCircle, Info, TrendingUp, GitFork, Eye, Layers, Shield, Activity } from "lucide-react";

const COLORS = {
  purple: "#8b5cf6",
  blue: "#3b82f6",
  green: "#22c55e",
  red: "#ef4444",
  orange: "#f97316",
  yellow: "#eab308",
  cyan: "#06b6d4",
  slate: "#64748b",
  pink: "#ec4899",
};

const EDGE_COLORS: Record<string, string> = {
  relates_to: COLORS.slate,
  depends_on: COLORS.blue,
  caused_by: COLORS.red,
  co_occurs: COLORS.purple,
  contradicts: COLORS.yellow,
  supersedes: COLORS.cyan,
};

const tooltipStyle = { background: "#1e293b", border: "1px solid #334155", borderRadius: "8px" };

function ScoreCircle({ score, size = 120 }: { score: number; size?: number }) {
  const r = (size - 12) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score);
  const color = score > 0.7 ? COLORS.green : score > 0.4 ? COLORS.yellow : COLORS.red;

  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e293b" strokeWidth="8" />
      <circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth="8" strokeLinecap="round"
        strokeDasharray={circumference} strokeDashoffset={offset}
        className="transition-all duration-1000"
      />
      <text
        x={size / 2} y={size / 2}
        textAnchor="middle" dominantBaseline="central"
        className="transform rotate-90 origin-center"
        fill={color} fontSize={size * 0.22} fontWeight="bold"
        style={{ transformOrigin: `${size / 2}px ${size / 2}px` }}
      >
        {Math.round(score * 100)}%
      </text>
    </svg>
  );
}

function HealthBar({ label, value, icon }: { label: string; value: number; icon: React.ReactNode }) {
  const color = value > 0.7 ? COLORS.green : value > 0.4 ? COLORS.yellow : COLORS.red;
  return (
    <div className="flex items-center gap-3">
      <div className="text-slate-400 w-5 shrink-0">{icon}</div>
      <div className="flex-1">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-slate-300">{label}</span>
          <span style={{ color }} className="font-mono">{Math.round(value * 100)}%</span>
        </div>
        <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${value * 100}%`, backgroundColor: color }}
          />
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value, sub, color = "text-white" }: { label: string; value: string | number; sub?: string; color?: string }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={`text-xl font-bold ${color}`}>{value}</p>
      {sub && <p className="text-xs text-slate-500 mt-1">{sub}</p>}
    </div>
  );
}

export default function Monitoring() {
  const { project } = useProject();
  const { data: adv, loading } = useAdvancedStats(project || undefined);
  const { data: diag } = useDiagnose(project || undefined);
  const { data: elabData } = useElaborations();
  const [opsToolFilter, setOpsToolFilter] = useState<string>("");
  const { data: opsData } = useOperations(project || undefined, opsToolFilter || undefined);

  if (loading || !adv) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-24 bg-slate-800/50 rounded-xl animate-pulse" />)}
        </div>
        <div className="grid grid-cols-2 gap-4">
          {[...Array(4)].map((_, i) => <div key={i} className="h-64 bg-slate-800/50 rounded-xl animate-pulse" />)}
        </div>
      </div>
    );
  }

  const hb = adv.health_breakdown ?? { graph_connectivity: 0, edge_diversity: 0, elaboration_depth: 0, access_balance: 0, component_unity: 0 };
  const gr = adv.graph ?? { degree_histogram: {}, edge_types: {}, avg_degree: 0, median_degree: 0, typed_edge_ratio: 0, connected_components: 0, largest_component_pct: 0, has_contradicts: false, has_supersedes: false, hubs_10_plus: 0, under_connected_0_1: 0 };
  const acc = adv.access ?? { gini_coefficient: 0, never_accessed: 0, never_accessed_pct: 0, total_accesses: 0, top_10_access_counts: [] };
  const elab = adv.elaboration ?? { avg_count: 0, distribution: {} };
  const mq = adv.memory_quality ?? { type_distribution: {}, decay_distribution: {}, avg_tokens: 0, min_tokens: 0, max_tokens: 0 };

  // Radar data for health breakdown
  const radarData = [
    { metric: "Graph", value: (hb.graph_connectivity ?? 0) * 100, fullMark: 100 },
    { metric: "Edge Types", value: (hb.edge_diversity ?? 0) * 100, fullMark: 100 },
    { metric: "Elaboration", value: (hb.elaboration_depth ?? 0) * 100, fullMark: 100 },
    { metric: "Access Balance", value: (hb.access_balance ?? 0) * 100, fullMark: 100 },
    { metric: "Unity", value: (hb.component_unity ?? 0) * 100, fullMark: 100 },
  ];

  // Degree histogram
  const degreeData = Object.entries(gr.degree_histogram ?? {}).map(([k, v]) => ({
    edges: k, count: v,
  }));

  // Edge type pie
  const edgeTypeData = Object.entries(gr.edge_types ?? {}).map(([k, v]) => ({
    name: k, value: v,
  }));

  // Elaboration depth distribution
  const elabDepthData = Object.entries(elab.distribution ?? {})
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([k, v]) => ({ depth: k, count: v }));

  // Decay distribution
  const decayData = Object.entries(mq.decay_distribution ?? {}).map(([k, v]) => ({
    name: k, value: v,
  }));

  // Growth timeline
  const growth = adv.growth_timeline ?? [];

  // Elaboration history
  const elabs = elabData?.items ?? [];
  const elabChartData = [...elabs].reverse().slice(-20).map((e) => ({
    date: e.started_at ? new Date(e.started_at).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit" }) : "?",
    new: e.new_memories,
    updated: e.updated_memories,
    deprecated: e.deprecated_memories,
    edges: e.new_edges,
  }));

  // Gini
  const gini = acc.gini_coefficient ?? 0;

  // Issues from health breakdown
  const issues: { severity: string; message: string; icon: React.ReactNode }[] = [];
  if ((hb.access_balance ?? 0) < 0.3)
    issues.push({ severity: "warning", message: `Access Gini ${gini.toFixed(2)} — retrieval heavily biased toward few memories`, icon: <Eye className="w-4 h-4" /> });
  if ((hb.edge_diversity ?? 0) < 0.3)
    issues.push({ severity: "warning", message: `Only ${Math.round((gr.typed_edge_ratio ?? 0) * 100)}% typed edges — graph too generic (relates_to dominant)`, icon: <GitFork className="w-4 h-4" /> });
  if (!gr.has_contradicts)
    issues.push({ severity: "info", message: "No contradicts edges — elaboration should identify conflicting memories", icon: <Info className="w-4 h-4" /> });
  if (!gr.has_supersedes)
    issues.push({ severity: "info", message: "No supersedes edges — older memories may shadow newer ones", icon: <Info className="w-4 h-4" /> });
  if ((gr.hubs_10_plus ?? 0) > 0)
    issues.push({ severity: "info", message: `${gr.hubs_10_plus} hub memories (10+ edges) — potential noise floor sources`, icon: <Layers className="w-4 h-4" /> });
  if ((acc.never_accessed_pct ?? 0) > 40)
    issues.push({ severity: "warning", message: `${acc.never_accessed} memories (${acc.never_accessed_pct}%) never accessed`, icon: <Eye className="w-4 h-4" /> });

  return (
    <div className="space-y-6">
      {/* ─── Row 1: Health Score + Breakdown ─── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Health Score */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 flex flex-col items-center justify-center">
          <ScoreCircle score={adv.health_score} size={140} />
          <p className="text-sm text-slate-400 mt-3">Health Score</p>
          <p className="text-xs text-slate-500">{adv.total_memories} memories · {adv.total_edges} edges</p>
        </div>

        {/* Health Breakdown Bars */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 space-y-3">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Health Breakdown</h3>
          <HealthBar label="Graph Connectivity" value={hb.graph_connectivity} icon={<GitFork className="w-4 h-4" />} />
          <HealthBar label="Edge Diversity" value={hb.edge_diversity} icon={<Layers className="w-4 h-4" />} />
          <HealthBar label="Elaboration Depth" value={hb.elaboration_depth} icon={<TrendingUp className="w-4 h-4" />} />
          <HealthBar label="Access Balance" value={hb.access_balance} icon={<Eye className="w-4 h-4" />} />
          <HealthBar label="Component Unity" value={hb.component_unity} icon={<Shield className="w-4 h-4" />} />
        </div>

        {/* Radar Chart */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Quality Radar</h3>
          <ResponsiveContainer width="100%" height={220}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Radar dataKey="value" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.25} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ─── Row 2: Key Metrics ─── */}
      <div className="grid grid-cols-6 gap-3">
        <StatCard label="Avg Degree" value={gr.avg_degree} sub={`median: ${gr.median_degree}`} />
        <StatCard label="Typed Edges" value={`${Math.round(gr.typed_edge_ratio * 100)}%`} sub={`${adv.total_edges - (gr.edge_types.relates_to ?? 0)} / ${adv.total_edges}`} color={gr.typed_edge_ratio > 0.3 ? "text-green-400" : "text-yellow-400"} />
        <StatCard label="Gini Index" value={gini.toFixed(3)} sub={gini < 0.5 ? "balanced" : gini < 0.7 ? "moderate bias" : "high bias"} color={gini < 0.5 ? "text-green-400" : gini < 0.7 ? "text-yellow-400" : "text-red-400"} />
        <StatCard label="Components" value={gr.connected_components} sub={`largest: ${gr.largest_component_pct}%`} color={gr.connected_components <= 2 ? "text-green-400" : "text-yellow-400"} />
        <StatCard label="Avg Tokens" value={mq.avg_tokens} sub={`${mq.min_tokens}–${mq.max_tokens}`} />
        <StatCard label="Avg Elaboration" value={`${elab.avg_count}×`} sub={`${Object.keys(elab.distribution).length} levels`} />
      </div>

      {/* ─── Row 3: Growth + Elaboration History ─── */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Memory & Edge Growth</h3>
          {growth.length === 0 ? (
            <p className="text-slate-500 text-sm">No data yet</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={growth}>
                <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} />
                <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Area type="monotone" dataKey="total" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.15} strokeWidth={2} name="Memories" />
                <Area type="monotone" dataKey="total_edges" stroke={COLORS.blue} fill={COLORS.blue} fillOpacity={0.1} strokeWidth={2} name="Edges" />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Elaboration Activity</h3>
          {elabChartData.length === 0 ? (
            <p className="text-slate-500 text-sm">No elaboration data</p>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={elabChartData}>
                <XAxis dataKey="date" stroke="#475569" tick={{ fontSize: 10 }} />
                <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
                <Tooltip contentStyle={tooltipStyle} />
                <Bar dataKey="new" fill={COLORS.green} stackId="a" name="New" />
                <Bar dataKey="updated" fill={COLORS.blue} stackId="a" name="Updated" />
                <Bar dataKey="deprecated" fill={COLORS.red} stackId="a" name="Deprecated" />
                <Bar dataKey="edges" fill={COLORS.cyan} name="New Edges" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ─── Row 4: Graph Analysis ─── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Degree Distribution */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Degree Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">Edges per memory — target: 3-6</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={degreeData}>
              <XAxis dataKey="edges" stroke="#475569" tick={{ fontSize: 11 }} />
              <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" fill={COLORS.purple}>
                {degreeData.map((entry, i) => {
                  const key = entry.edges;
                  const isTarget = ["3", "4", "5"].includes(key);
                  const isLow = ["0", "1"].includes(key);
                  return <Cell key={i} fill={isLow ? COLORS.red : isTarget ? COLORS.green : COLORS.purple} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Edge Type Diversity */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Edge Type Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">{Math.round(gr.typed_edge_ratio * 100)}% typed (non-relates_to)</p>
          <ResponsiveContainer width="100%" height={180}>
            <PieChart>
              <Pie data={edgeTypeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label={({ name, percent }: { name?: string; percent?: number }) => `${name ?? ""} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                {edgeTypeData.map((entry, i) => (
                  <Cell key={i} fill={EDGE_COLORS[entry.name] || COLORS.slate} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle} />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Elaboration Depth */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Elaboration Depth</h3>
          <p className="text-xs text-slate-500 mb-3">avg {elab.avg_count}× per memory</p>
          <ResponsiveContainer width="100%" height={180}>
            <BarChart data={elabDepthData}>
              <XAxis dataKey="depth" stroke="#475569" tick={{ fontSize: 11 }} />
              <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count" fill={COLORS.cyan}>
                {elabDepthData.map((entry, i) => {
                  const depth = parseInt(entry.depth);
                  return <Cell key={i} fill={depth >= 3 ? COLORS.green : depth >= 2 ? COLORS.blue : COLORS.yellow} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ─── Row 5: Access + Memory Quality ─── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Access Distribution */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Access Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">
            Gini {gini.toFixed(3)} — {gini < 0.5 ? "healthy" : gini < 0.7 ? "moderate bias" : "strong bias toward few memories"}
          </p>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Never accessed</span>
              <span className="text-red-400 font-mono">{acc.never_accessed} ({acc.never_accessed_pct}%)</span>
            </div>
            <div className="h-3 bg-slate-700 rounded-full overflow-hidden flex">
              <div className="h-full bg-red-500/60" style={{ width: `${acc.never_accessed_pct}%` }} title="Never accessed" />
              <div className="h-full bg-green-500/60" style={{ width: `${100 - acc.never_accessed_pct}%` }} title="Accessed" />
            </div>
            <p className="text-xs text-slate-500 mt-2">Top 10 access counts:</p>
            <div className="flex gap-1 flex-wrap">
              {acc.top_10_access_counts.map((c, i) => (
                <span key={i} className="text-xs px-1.5 py-0.5 bg-purple-500/20 text-purple-300 rounded font-mono">{c}</span>
              ))}
            </div>
            <p className="text-xs text-slate-500">Total: {acc.total_accesses} accesses across {adv.total_memories} memories</p>
          </div>
        </div>

        {/* Decay Distribution */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Decay Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">Memory freshness over time</p>
          <div className="space-y-3 mt-4">
            {decayData.map(({ name, value }) => {
              const pct = adv.total_memories > 0 ? (value / adv.total_memories * 100) : 0;
              const color = name.includes("fresh") ? COLORS.green : name.includes("healthy") ? COLORS.blue : name.includes("fading") ? COLORS.yellow : COLORS.red;
              return (
                <div key={name}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-300">{name}</span>
                    <span className="text-slate-400 font-mono">{value} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Memory Type Balance */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Memory Types</h3>
          <p className="text-xs text-slate-500 mb-3">Balance across knowledge types</p>
          <div className="space-y-3 mt-4">
            {Object.entries(mq.type_distribution).map(([type, count]) => {
              const pct = adv.total_memories > 0 ? (count / adv.total_memories * 100) : 0;
              const color = type === "semantic" ? COLORS.blue : type === "episodic" ? COLORS.green : COLORS.orange;
              return (
                <div key={type}>
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-300 capitalize">{type}</span>
                    <span className="text-slate-400 font-mono">{count} ({pct.toFixed(0)}%)</span>
                  </div>
                  <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                    <div className="h-full rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="mt-4 pt-3 border-t border-slate-700/50 text-xs text-slate-500">
            Avg tokens/memory: <span className="text-slate-300 font-mono">{mq.avg_tokens}</span>
            <span className="text-slate-600 ml-1">({mq.min_tokens}–{mq.max_tokens})</span>
          </div>
        </div>
      </div>

      {/* ─── Row 6: Prescriptions ─── */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-medium text-slate-400">Prescriptions</h3>
          {diag && (
            <span className="text-xs px-2 py-0.5 rounded bg-slate-700 text-slate-300">
              maturity: <span className="text-purple-300 font-medium">{diag.maturity}</span>
            </span>
          )}
        </div>
        {!diag || diag.prescriptions.length === 0 ? (
          <div className="flex items-center gap-2 text-green-400 text-sm py-2">
            <CheckCircle className="w-4 h-4" /> All metrics within optimal range
          </div>
        ) : (
          <div className="space-y-3">
            {diag.prescriptions.map((rx, i) => (
              <PrescriptionCard key={i} rx={rx} index={i} />
            ))}
          </div>
        )}
      </div>

      {/* ─── Row 7: Elaboration Log ─── */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-400 mb-3">Elaboration Log</h3>
        {elabs.length === 0 ? (
          <p className="text-slate-500 text-sm">No elaborations recorded</p>
        ) : (
          <div className="overflow-auto max-h-64">
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-slate-800">
                <tr className="text-slate-400 border-b border-slate-700">
                  <th className="text-left py-2 px-3 font-medium">Date</th>
                  <th className="text-right py-2 px-3 font-medium">Seeds</th>
                  <th className="text-right py-2 px-3 font-medium">Working Set</th>
                  <th className="text-right py-2 px-3 font-medium">New</th>
                  <th className="text-right py-2 px-3 font-medium">Updated</th>
                  <th className="text-right py-2 px-3 font-medium">Deprecated</th>
                  <th className="text-right py-2 px-3 font-medium">Edges</th>
                  <th className="text-left py-2 px-3 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {elabs.map((e) => (
                  <tr key={e.id} className="border-b border-slate-800 hover:bg-slate-700/20">
                    <td className="py-2 px-3 text-slate-300 text-xs">
                      {e.started_at ? new Date(e.started_at).toLocaleString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"}
                    </td>
                    <td className="py-2 px-3 text-right text-slate-300">{e.seed_count ?? "—"}</td>
                    <td className="py-2 px-3 text-right text-slate-300">{e.working_set ?? "—"}</td>
                    <td className="py-2 px-3 text-right text-green-400">{e.new_memories}</td>
                    <td className="py-2 px-3 text-right text-blue-400">{e.updated_memories}</td>
                    <td className="py-2 px-3 text-right text-red-400">{e.deprecated_memories}</td>
                    <td className="py-2 px-3 text-right text-cyan-400">{e.new_edges}</td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${e.status === "completed" ? "bg-green-500/20 text-green-300" : "bg-yellow-500/20 text-yellow-300"}`}>
                        {e.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ─── Row 8: Operation Log ─── */}
      <OperationLogSection ops={opsData?.items ?? []} toolFilter={opsToolFilter} onToolFilterChange={setOpsToolFilter} />
    </div>
  );
}

const TOOL_COLORS: Record<string, string> = {
  remember: "bg-blue-500/20 text-blue-300",
  memorize: "bg-green-500/20 text-green-300",
  elaborate: "bg-purple-500/20 text-purple-300",
  update_memory: "bg-cyan-500/20 text-cyan-300",
  sync_codebase: "bg-orange-500/20 text-orange-300",
  decay: "bg-yellow-500/20 text-yellow-300",
  reinforce: "bg-pink-500/20 text-pink-300",
};

const TOOL_OPTIONS = ["", "remember", "memorize", "elaborate", "update_memory", "sync_codebase", "decay", "reinforce"];

function OperationLogSection({ ops, toolFilter, onToolFilterChange }: {
  ops: OperationLog[];
  toolFilter: string;
  onToolFilterChange: (v: string) => void;
}) {
  const parseJson = (s: string | null): Record<string, unknown> | null => {
    if (!s) return null;
    try { return JSON.parse(s); } catch { return null; }
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-slate-400" />
          <h3 className="text-sm font-medium text-slate-400">Operation Log</h3>
          <span className="text-xs text-slate-500">{ops.length} entries</span>
        </div>
        <select
          value={toolFilter}
          onChange={(e) => onToolFilterChange(e.target.value)}
          className="text-xs bg-slate-700 text-slate-300 border border-slate-600 rounded px-2 py-1"
        >
          <option value="">All tools</option>
          {TOOL_OPTIONS.filter(Boolean).map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
      </div>
      {ops.length === 0 ? (
        <p className="text-slate-500 text-sm">No operations logged yet</p>
      ) : (
        <div className="overflow-auto max-h-80">
          <table className="w-full text-sm">
            <thead className="sticky top-0 bg-slate-800">
              <tr className="text-slate-400 border-b border-slate-700">
                <th className="text-left py-2 px-3 font-medium">Time</th>
                <th className="text-left py-2 px-3 font-medium">Tool</th>
                <th className="text-left py-2 px-3 font-medium">Params</th>
                <th className="text-left py-2 px-3 font-medium">Result</th>
                <th className="text-right py-2 px-3 font-medium">Duration</th>
                <th className="text-left py-2 px-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {ops.map((op) => {
                const params = parseJson(op.params);
                const result = parseJson(op.result);
                const toolClass = TOOL_COLORS[op.tool] ?? "bg-slate-500/20 text-slate-300";
                return (
                  <tr key={op.id} className="border-b border-slate-800 hover:bg-slate-700/20">
                    <td className="py-2 px-3 text-slate-300 text-xs whitespace-nowrap">
                      {op.started_at ? new Date(op.started_at).toLocaleString("it-IT", {
                        day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit",
                      }) : "—"}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${toolClass}`}>{op.tool}</span>
                    </td>
                    <td className="py-2 px-3 text-xs text-slate-400 max-w-48 truncate" title={op.params ?? ""}>
                      {params ? Object.entries(params).map(([k, v]) => (
                        <span key={k} className="mr-2">
                          <span className="text-slate-500">{k}:</span>{" "}
                          <span className="text-slate-300">{typeof v === "string" ? (v.length > 30 ? v.slice(0, 30) + "..." : v) : JSON.stringify(v)}</span>
                        </span>
                      )) : "—"}
                    </td>
                    <td className="py-2 px-3 text-xs text-slate-400 max-w-40 truncate" title={op.result ?? ""}>
                      {result ? Object.entries(result).map(([k, v]) => (
                        <span key={k} className="mr-2">
                          <span className="text-slate-500">{k}:</span>{" "}
                          <span className="text-slate-300">{String(v)}</span>
                        </span>
                      )) : "—"}
                    </td>
                    <td className="py-2 px-3 text-right text-xs text-slate-400 font-mono">
                      {op.duration_ms != null ? (op.duration_ms > 1000 ? `${(op.duration_ms / 1000).toFixed(1)}s` : `${op.duration_ms}ms`) : "—"}
                    </td>
                    <td className="py-2 px-3">
                      <span className={`px-2 py-0.5 rounded text-xs ${op.status === "ok" ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"}`}>
                        {op.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

const ACTION_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  elaborate: { bg: "bg-purple-500/15 border-purple-500/30", text: "text-purple-300", label: "Elaborate" },
  decay_and_investigate: { bg: "bg-yellow-500/15 border-yellow-500/30", text: "text-yellow-300", label: "Decay + Investigate" },
  improve_graph_and_queries: { bg: "bg-orange-500/15 border-orange-500/30", text: "text-orange-300", label: "Improve Graph + Queries" },
  investigate: { bg: "bg-blue-500/15 border-blue-500/30", text: "text-blue-300", label: "Investigate" },
};

const FOCUS_LABELS: Record<string, string> = {
  typed_edges: "Focus: typed edges",
  contradicts: "Focus: contradictions",
  supersedes: "Focus: superseded pairs",
  connectivity: "Focus: connectivity",
  quality: "Focus: content quality",
  general: "General",
};

function PrescriptionCard({ rx, index }: { rx: Prescription; index: number }) {
  const style = ACTION_STYLES[rx.action] ?? ACTION_STYLES.investigate;
  const isRatio = typeof rx.current === "number" && rx.current <= 1 && rx.metric !== "hubs";
  const targetStr = rx.target[1] !== null
    ? isRatio ? `${Math.round((rx.target[0] ?? 0) * 100)}–${Math.round((rx.target[1] as number) * 100)}%` : `${rx.target[0]}–${rx.target[1]}`
    : isRatio ? `>${Math.round((rx.target[0] ?? 0) * 100)}%` : `>${rx.target[0]}`;
  const currentStr = isRatio ? `${Math.round(rx.current * 100)}%` : String(rx.current);

  return (
    <div className={`p-4 rounded-xl border ${style.bg}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-xs font-bold w-5 h-5 rounded flex items-center justify-center ${
              rx.severity === "warning" ? "bg-yellow-500/20 text-yellow-300" :
              rx.severity === "optimize" ? "bg-purple-500/20 text-purple-300" :
              "bg-blue-500/20 text-blue-300"
            }`}>
              {index + 1}
            </span>
            <span className="text-sm font-medium text-white">{rx.metric.replace(/_/g, " ")}</span>
            <span className="text-xs text-slate-500 font-mono">{currentStr} → {targetStr}</span>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed">{rx.diagnosis}</p>
        </div>
        <div className="text-right shrink-0">
          <span className={`text-xs font-medium px-2 py-1 rounded-lg border ${style.bg} ${style.text}`}>
            {style.label}
          </span>
          {rx.focus && (
            <p className="text-[11px] text-slate-500 mt-1">{FOCUS_LABELS[rx.focus] ?? rx.focus}</p>
          )}
          {rx.rounds > 0 && (
            <p className="text-[11px] text-slate-500">{rx.rounds} round{rx.rounds > 1 ? "s" : ""}</p>
          )}
        </div>
      </div>
      {rx.why_it_matters && (
        <div className="mt-2 pt-2 border-t border-slate-700/30">
          <p className="text-xs text-slate-400 italic leading-relaxed">{rx.why_it_matters}</p>
        </div>
      )}
      <div className={`${rx.why_it_matters ? "mt-1.5" : "mt-2 pt-2 border-t border-slate-700/30"}`}>
        <span className="text-xs text-slate-500">Expected: {rx.expected_improvement}</span>
      </div>
    </div>
  );
}
