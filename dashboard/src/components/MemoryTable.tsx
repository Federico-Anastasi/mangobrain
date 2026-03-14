import { AlertTriangle, FileCode } from "lucide-react";
import type { Memory } from "../types/index.ts";

interface Props {
  memories: Memory[];
  loading: boolean;
  selectedId: string | null;
  onSelect: (id: string) => void;
}

const typeBadge: Record<string, string> = {
  semantic: "bg-blue-500/20 text-blue-300",
  episodic: "bg-green-500/20 text-green-300",
  procedural: "bg-orange-500/20 text-orange-300",
};

export default function MemoryTable({ memories, loading, selectedId, onSelect }: Props) {
  if (loading) {
    return (
      <div className="space-y-1">
        {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
          <div key={i} className="h-11 bg-slate-800/50 rounded animate-pulse" style={{ animationDelay: `${i * 50}ms` }} />
        ))}
      </div>
    );
  }

  if (memories.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-slate-500">
        <p className="text-sm">No memories found</p>
        <p className="text-xs mt-1 text-slate-600">Try adjusting your filters</p>
      </div>
    );
  }

  const hasFilePaths = memories.some((m) => m.file_path);

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-slate-400 border-b border-slate-700">
            <th className="text-left py-2 px-3 font-medium w-24">Type</th>
            <th className="text-left py-2 px-3 font-medium">Content</th>
            {hasFilePaths && <th className="text-left py-2 px-3 font-medium w-36">File</th>}
            <th className="text-left py-2 px-3 font-medium w-44">Tags</th>
            <th className="text-right py-2 px-3 font-medium w-16">Access</th>
            <th className="text-right py-2 px-3 font-medium w-14">Elab</th>
            <th className="text-right py-2 px-3 font-medium w-16">Decay</th>
          </tr>
        </thead>
        <tbody>
          {memories.map((m) => (
            <tr
              key={m.id}
              onClick={() => onSelect(m.id)}
              className={`border-b border-slate-800/50 cursor-pointer transition-colors ${
                selectedId === m.id ? "bg-purple-500/10 border-purple-500/20" : "hover:bg-slate-800/40"
              } ${m.is_deprecated ? "opacity-50" : ""}`}
            >
              <td className="py-2 px-3">
                <div className="flex items-center gap-1.5">
                  <span className={`px-2 py-0.5 rounded text-xs font-medium ${typeBadge[m.type] ?? "bg-slate-700 text-slate-300"}`}>
                    {m.type.slice(0, 3)}
                  </span>
                  {m.is_deprecated && <span title="Deprecated"><AlertTriangle className="w-3 h-3 text-red-400" /></span>}
                </div>
              </td>
              <td className="py-2 px-3 text-slate-200 max-w-md">
                <span className="line-clamp-1">{m.content}</span>
              </td>
              {hasFilePaths && (
                <td className="py-2 px-3 max-w-[140px]">
                  {m.file_path ? (
                    <span className="flex items-center gap-1 text-xs text-slate-400 truncate" title={m.file_path}>
                      <FileCode className="w-3 h-3 shrink-0" />
                      <span className="truncate">{m.file_path.split("/").pop()}</span>
                    </span>
                  ) : (
                    <span className="text-slate-700 text-xs">—</span>
                  )}
                </td>
              )}
              <td className="py-2 px-3">
                <div className="flex gap-1 flex-wrap">
                  {m.tags.slice(0, 3).map((t) => (
                    <span key={t} className="px-1.5 py-0.5 rounded bg-slate-700/60 text-slate-400 text-[11px]">{t}</span>
                  ))}
                  {m.tags.length > 3 && <span className="text-slate-600 text-[11px]">+{m.tags.length - 3}</span>}
                </div>
              </td>
              <td className="py-2 px-3 text-right">
                <span className={`font-mono text-xs ${m.access_count > 0 ? "text-slate-300" : "text-slate-600"}`}>
                  {m.access_count}
                </span>
              </td>
              <td className="py-2 px-3 text-right">
                <span className={`font-mono text-xs ${m.elaboration_count >= 3 ? "text-green-400" : m.elaboration_count >= 2 ? "text-blue-400" : "text-yellow-400"}`}>
                  {m.elaboration_count}×
                </span>
              </td>
              <td className="py-2 px-3 text-right">
                <span className={`font-mono text-xs ${m.decay_score < 0.3 ? "text-red-400" : m.decay_score < 0.7 ? "text-yellow-400" : "text-green-400"}`}>
                  {m.decay_score.toFixed(2)}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
