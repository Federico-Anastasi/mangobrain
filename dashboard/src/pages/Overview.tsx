import { useNavigate } from "react-router-dom";
import { useProject } from "../context/ProjectContext.tsx";
import { useAdvancedStats, useOperations, useSessions, useSetupAll } from "../hooks/useApi.ts";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  AreaChart, Area, XAxis, YAxis, BarChart, Bar,
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
} from "recharts";
import {
  Database, GitFork, Eye, Layers,
  Shield, Activity, Zap, Clock,
} from "lucide-react";

const COLORS = {
  purple: "#8b5cf6", blue: "#3b82f6", green: "#22c55e", red: "#ef4444",
  orange: "#f97316", yellow: "#eab308", cyan: "#06b6d4", slate: "#64748b", pink: "#ec4899",
};

const TYPE_COLORS: Record<string, string> = { semantic: COLORS.blue, episodic: COLORS.green, procedural: COLORS.orange };
const EDGE_COLORS: Record<string, string> = {
  relates_to: COLORS.slate, depends_on: COLORS.blue, caused_by: COLORS.red,
  co_occurs: COLORS.purple, contradicts: COLORS.yellow, supersedes: COLORS.cyan,
};
const tooltipStyle = { background: "#1e293b", border: "1px solid #334155", borderRadius: "8px" };

function ScoreRing({ score, size = 100 }: { score: number; size?: number }) {
  const r = (size - 10) / 2;
  const circumference = 2 * Math.PI * r;
  const offset = circumference * (1 - score);
  const color = score > 0.7 ? COLORS.green : score > 0.4 ? COLORS.yellow : COLORS.red;
  return (
    <svg width={size} height={size} className="transform -rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#1e293b" strokeWidth="6" />
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={color} strokeWidth="6"
        strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
        className="transition-all duration-1000" />
      <text x={size / 2} y={size / 2} textAnchor="middle" dominantBaseline="central" fill={color}
        fontSize={size * 0.24} fontWeight="bold" className="transform rotate-90"
        style={{ transformOrigin: `${size / 2}px ${size / 2}px` }}>
        {Math.round(score * 100)}
      </text>
    </svg>
  );
}

function SetupBanner() {
  const navigate = useNavigate();
  const { data: projects } = useSetupAll();
  if (!projects || projects.length === 0) return null;
  const inProgress = projects.filter(p => !p.is_ready && p.initialized);
  const ready = projects.filter(p => p.is_ready);
  if (inProgress.length === 0 && ready.length === 0) return null;

  return (
    <div className="space-y-2">
      {inProgress.map(p => (
        <button
          key={p.project}
          onClick={() => navigate("/setup")}
          className="w-full flex items-center gap-3 px-4 py-3 bg-purple-900/20 border border-purple-500/30 rounded-xl hover:bg-purple-900/30 transition-colors text-left"
        >
          <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
            <span className="text-sm font-bold text-purple-300">{p.progress_pct}%</span>
          </div>
          <div className="flex-1">
            <p className="text-sm font-medium text-purple-200">{p.project} — Setup in progress</p>
            <p className="text-xs text-purple-400">{p.completed}/{p.total_steps} steps completed. Click to continue.</p>
          </div>
          <Activity className="w-4 h-4 text-purple-400" />
        </button>
      ))}
      {ready.map(p => (
        <div key={p.project} className="flex items-center gap-3 px-4 py-2 bg-green-900/10 border border-green-800/30 rounded-xl">
          <Shield className="w-4 h-4 text-green-400" />
          <span className="text-sm text-green-300 font-medium">{p.project}</span>
          <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full font-medium">READY</span>
        </div>
      ))}
    </div>
  );
}

export default function Overview() {
  const { project } = useProject();
  const { data: adv, loading } = useAdvancedStats(project || undefined, true);
  const { data: elabOps } = useOperations(project || undefined, "elaborate", true);
  const { data: sessionsData } = useSessions(project || undefined, true);

  if (loading || !adv) {
    return (
      <div className="space-y-6">
        <div className="grid grid-cols-5 gap-3">{[...Array(5)].map((_, i) => <div key={i} className="h-24 bg-slate-800/50 rounded-xl animate-pulse" />)}</div>
        <div className="grid grid-cols-3 gap-4">{[...Array(3)].map((_, i) => <div key={i} className="h-64 bg-slate-800/50 rounded-xl animate-pulse" />)}</div>
      </div>
    );
  }

  const hb = adv.health_breakdown ?? { graph_connectivity: 0, edge_diversity: 0, elaboration_depth: 0, access_balance: 0, component_unity: 0 };
  const mq = adv.memory_quality ?? { type_distribution: {} };
  const gr = adv.graph ?? { edge_types: {}, avg_degree: 0, typed_edge_ratio: 0, under_connected_0_1: 0, hubs_10_plus: 0, degree_histogram: {} };
  const acc = adv.access ?? { gini_coefficient: 0, never_accessed: 0, never_accessed_pct: 0 };
  const elab = adv.elaboration ?? { avg_count: 0, distribution: {} };

  // Data transforms
  const typeData = Object.entries(mq.type_distribution ?? {}).map(([name, value]) => ({ name, value }));
  const edgeTypeData = Object.entries(gr.edge_types ?? {}).map(([name, value]) => ({ name, value }));
  const growth = adv.growth_timeline ?? [];
  const radarData = [
    { metric: "Graph", value: (hb.graph_connectivity ?? 0) * 100 },
    { metric: "Edges", value: (hb.edge_diversity ?? 0) * 100 },
    { metric: "Elab", value: (hb.elaboration_depth ?? 0) * 100 },
    { metric: "Access", value: (hb.access_balance ?? 0) * 100 },
    { metric: "Unity", value: (hb.component_unity ?? 0) * 100 },
  ];

  // Recent activity: merge sessions + elaborations, sort by date
  const sessions = (sessionsData?.items ?? []).map(s => ({
    type: "extraction" as const, date: s.started_at, project: s.project,
    detail: `${s.memories_extracted} memories`, name: s.run_name,
  }));
  const elabs = (elabOps?.items ?? []).slice(0, 10).map(op => {
    const r = op.result ? (() => { try { return JSON.parse(op.result); } catch { return null; } })() : null;
    return {
      type: "elaboration" as const, date: op.started_at, project: op.project ?? null,
      detail: r ? `+${r.new_memories ?? 0} new, ${r.new_edges ?? 0} edges` : op.status,
      name: op.status,
    };
  });
  const recentActivity = [...sessions, ...elabs]
    .sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())
    .slice(0, 8);

  // Issues
  const issues: { severity: string; message: string; icon: React.ReactNode }[] = [];
  if (hb.access_balance < 0.3)
    issues.push({ severity: "warning", message: `Gini ${acc.gini_coefficient.toFixed(2)} — access heavily biased`, icon: <Eye className="w-4 h-4" /> });
  if (hb.edge_diversity < 0.3)
    issues.push({ severity: "warning", message: `${Math.round(gr.typed_edge_ratio * 100)}% typed edges — too generic`, icon: <GitFork className="w-4 h-4" /> });
  if (acc.never_accessed_pct > 40)
    issues.push({ severity: "info", message: `${acc.never_accessed} memories never accessed (${acc.never_accessed_pct}%)`, icon: <Eye className="w-4 h-4" /> });
  if (gr.under_connected_0_1 > 0)
    issues.push({ severity: "info", message: `${gr.under_connected_0_1} under-connected memories (0-1 edges)`, icon: <Layers className="w-4 h-4" /> });

  return (
    <div className="space-y-5">
      {/* ─── Setup Status Banner ─── */}
      <SetupBanner />

      {/* ─── Row 1: Hero Stats ─── */}
      <div className="grid grid-cols-5 gap-3">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 flex items-center gap-4">
          <ScoreRing score={adv.health_score} size={70} />
          <div>
            <p className="text-xs text-slate-400">Health</p>
            <p className="text-lg font-bold text-white">{Math.round(adv.health_score * 100)}%</p>
          </div>
        </div>
        <HeroCard icon={<Database className="w-4 h-4" />} label="Memories" value={adv.total_memories} color="text-blue-400"
          sub={`${(mq.type_distribution as Record<string, number>).semantic ?? 0} sem · ${(mq.type_distribution as Record<string, number>).procedural ?? 0} proc · ${(mq.type_distribution as Record<string, number>).episodic ?? 0} epi`} />
        <HeroCard icon={<GitFork className="w-4 h-4" />} label="Edges" value={adv.total_edges ?? 0} color="text-green-400"
          sub={`avg ${gr.avg_degree}/mem · ${Math.round(gr.typed_edge_ratio * 100)}% typed`} />
        <HeroCard icon={<Layers className="w-4 h-4" />} label="Elaboration" value={`${elab.avg_count}×`} color="text-cyan-400"
          sub={`${Object.keys(elab.distribution).length} depth levels`} />
        <HeroCard icon={<Eye className="w-4 h-4" />} label="Access Gini" value={acc.gini_coefficient.toFixed(2)} color={acc.gini_coefficient < 0.5 ? "text-green-400" : acc.gini_coefficient < 0.7 ? "text-yellow-400" : "text-red-400"}
          sub={acc.gini_coefficient < 0.5 ? "balanced" : acc.gini_coefficient < 0.7 ? "moderate bias" : "strong bias"} />
      </div>

      {/* ─── Row 2: Radar + Distributions + Growth ─── */}
      <div className="grid grid-cols-3 gap-4">
        {/* Quality Radar + Issues */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Quality Radar</h3>
          <ResponsiveContainer width="100%" height={180}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#334155" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: "#94a3b8", fontSize: 11 }} />
              <Radar dataKey="value" stroke={COLORS.purple} fill={COLORS.purple} fillOpacity={0.2} strokeWidth={2} />
            </RadarChart>
          </ResponsiveContainer>
          {issues.length > 0 && (
            <div className="mt-3 space-y-1.5 border-t border-slate-700/50 pt-3">
              {issues.slice(0, 3).map((issue, i) => (
                <div key={i} className="flex items-center gap-2 text-xs">
                  <span className={issue.severity === "warning" ? "text-yellow-400" : "text-blue-400"}>{issue.icon}</span>
                  <span className="text-slate-400 truncate">{issue.message}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Memory + Edge Distribution */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Distributions</h3>
          <div className="grid grid-cols-2 gap-2 h-[220px]">
            <div>
              <p className="text-xs text-slate-500 text-center mb-1">Memory Types</p>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={45} innerRadius={25}>
                    {typeData.map(d => <Cell key={d.name} fill={TYPE_COLORS[d.name] ?? COLORS.slate} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div>
              <p className="text-xs text-slate-500 text-center mb-1">Edge Types</p>
              <ResponsiveContainer width="100%" height="85%">
                <PieChart>
                  <Pie data={edgeTypeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={45} innerRadius={25}>
                    {edgeTypeData.map(d => <Cell key={d.name} fill={EDGE_COLORS[d.name] ?? COLORS.slate} />)}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </div>
          {/* Mini legends */}
          <div className="flex justify-around text-[10px] text-slate-500 mt-1">
            <div className="flex gap-2">
              {typeData.map(d => (
                <span key={d.name} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full inline-block" style={{ backgroundColor: TYPE_COLORS[d.name] }} />{d.name}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Growth Timeline */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-2">Growth</h3>
          {growth.length === 0 ? (
            <p className="text-slate-500 text-sm">No data</p>
          ) : (
            <ResponsiveContainer width="100%" height={240}>
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
      </div>

      {/* ─── Row 3: Recent Activity + Degree Distribution ─── */}
      <div className="grid grid-cols-2 gap-4">
        {/* Recent Activity */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-3">Recent Activity</h3>
          {recentActivity.length === 0 ? (
            <p className="text-slate-500 text-sm">No activity yet</p>
          ) : (
            <div className="space-y-2">
              {recentActivity.map((a, i) => (
                <div key={i} className="flex items-center gap-3 p-2.5 rounded-lg bg-slate-900/50">
                  <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${a.type === "extraction" ? "bg-purple-500/15" : "bg-cyan-500/15"}`}>
                    {a.type === "extraction" ? <Zap className="w-4 h-4 text-purple-400" /> : <Activity className="w-4 h-4 text-cyan-400" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-slate-200 capitalize">{a.type}</span>
                      {a.project && <span className="text-xs text-slate-500">{a.project}</span>}
                    </div>
                    <p className="text-xs text-slate-400 truncate">{a.detail}</p>
                  </div>
                  <div className="text-xs text-slate-500 shrink-0">
                    <Clock className="w-3 h-3 inline mr-1" />
                    {a.date ? new Date(a.date).toLocaleDateString("it-IT", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Degree Distribution */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <h3 className="text-sm font-medium text-slate-400 mb-1">Connection Distribution</h3>
          <p className="text-xs text-slate-500 mb-3">Edges per memory — {gr.under_connected_0_1} under-connected · {gr.hubs_10_plus} hubs</p>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={Object.entries(gr.degree_histogram ?? {}).map(([k, v]) => ({ edges: k, count: v }))}>
              <XAxis dataKey="edges" stroke="#475569" tick={{ fontSize: 11 }} />
              <YAxis stroke="#475569" tick={{ fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle} />
              <Bar dataKey="count">
                {Object.entries(gr.degree_histogram ?? {}).map(([k], i) => {
                  const isTarget = ["3", "4", "5"].includes(k);
                  const isLow = ["0", "1"].includes(k);
                  return <Cell key={i} fill={isLow ? COLORS.red : isTarget ? COLORS.green : COLORS.purple} />;
                })}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function HeroCard({ icon, label, value, color, sub }: { icon: React.ReactNode; label: string; value: string | number; color: string; sub: string }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-slate-400">{label}</span>
        <span className={color}>{icon}</span>
      </div>
      <p className="text-xl font-bold text-white mt-1">{value}</p>
      <p className="text-xs text-slate-500 mt-1">{sub}</p>
    </div>
  );
}
