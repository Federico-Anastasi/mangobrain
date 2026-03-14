import { Database, GitFork, AlertCircle, Heart } from "lucide-react";
import type { Stats } from "../types/index.ts";

interface Props {
  stats: Stats | null;
  loading: boolean;
}

export default function StatsCards({ stats, loading }: Props) {
  if (loading || !stats) {
    return (
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="bg-slate-800/50 rounded-xl p-4 h-24 animate-pulse" />
        ))}
      </div>
    );
  }

  const cards = [
    { label: "Total Memories", value: stats.total_memories, icon: Database, color: "text-blue-400" },
    { label: "Total Edges", value: stats.total_edges, icon: GitFork, color: "text-green-400" },
    { label: "Unelaborated", value: stats.memories_never_elaborated, icon: AlertCircle, color: "text-yellow-400" },
    {
      label: "Health Score",
      value: `${Math.round(stats.health_score * 100)}%`,
      icon: Heart,
      color: stats.health_score > 0.7 ? "text-green-400" : stats.health_score > 0.4 ? "text-yellow-400" : "text-red-400",
    },
  ];

  return (
    <div className="grid grid-cols-4 gap-4">
      {cards.map((c) => (
        <div key={c.label} className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">{c.label}</span>
            <c.icon className={`w-4 h-4 ${c.color}`} />
          </div>
          <div className="mt-2 text-2xl font-bold text-white">{c.value}</div>
        </div>
      ))}
    </div>
  );
}
