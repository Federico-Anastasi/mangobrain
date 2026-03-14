import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";
import type { Stats } from "../types/index.ts";

interface Props {
  stats: Stats | null;
}

const TYPE_COLORS: Record<string, string> = {
  semantic: "#3b82f6",
  episodic: "#22c55e",
  procedural: "#f97316",
};

const EDGE_COLORS: Record<string, string> = {
  relates_to: "#6b7280",
  caused_by: "#ef4444",
  depends_on: "#3b82f6",
  co_occurs: "#8b5cf6",
  contradicts: "#f59e0b",
  supersedes: "#06b6d4",
};

export default function DistributionCharts({ stats }: Props) {
  if (!stats) return null;

  const typeData = Object.entries(stats.by_type).map(([name, value]) => ({ name, value }));
  const edgeData = Object.entries(stats.edge_by_type).map(([name, value]) => ({ name, value }));

  return (
    <div className="grid grid-cols-2 gap-4">
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-400 mb-2">Memory Types</h3>
        {typeData.length === 0 ? (
          <p className="text-slate-500 text-sm">No data</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={typeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                {typeData.map((d) => (
                  <Cell key={d.name} fill={TYPE_COLORS[d.name] ?? "#6b7280"} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "8px" }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-400 mb-2">Edge Types</h3>
        {edgeData.length === 0 ? (
          <p className="text-slate-500 text-sm">No data</p>
        ) : (
          <ResponsiveContainer width="100%" height={200}>
            <PieChart>
              <Pie data={edgeData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} label>
                {edgeData.map((d) => (
                  <Cell key={d.name} fill={EDGE_COLORS[d.name] ?? "#6b7280"} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#1e293b", border: "1px solid #334155", borderRadius: "8px" }} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
