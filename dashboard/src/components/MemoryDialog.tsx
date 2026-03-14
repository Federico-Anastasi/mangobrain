import { useEffect, useCallback } from "react";
import { X, GitFork, ExternalLink, FileCode, Hash, AlertTriangle, Clock, Eye, Layers, Tag, Database } from "lucide-react";
import { useMemory } from "../hooks/useApi.ts";
import { useNavigate } from "react-router-dom";

interface Props {
  memoryId: string;
  onClose: () => void;
  onNavigateToMemory?: (id: string) => void;
}

const typeBadge: Record<string, string> = {
  semantic: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
  episodic: "bg-green-500/20 text-green-300 border border-green-500/30",
  procedural: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
};

const edgeTypeColor: Record<string, string> = {
  relates_to: "text-slate-300",
  caused_by: "text-red-400",
  depends_on: "text-yellow-400",
  co_occurs: "text-blue-400",
  contradicts: "text-pink-400",
  supersedes: "text-cyan-400",
};

const edgeTypeBg: Record<string, string> = {
  relates_to: "bg-slate-500/10 border-slate-600/30",
  caused_by: "bg-red-500/10 border-red-600/30",
  depends_on: "bg-yellow-500/10 border-yellow-600/30",
  co_occurs: "bg-blue-500/10 border-blue-600/30",
  contradicts: "bg-pink-500/10 border-pink-600/30",
  supersedes: "bg-cyan-500/10 border-cyan-600/30",
};

const connectedTypeDot: Record<string, string> = {
  semantic: "bg-blue-500",
  episodic: "bg-green-500",
  procedural: "bg-orange-500",
};

export default function MemoryDialog({ memoryId, onClose, onNavigateToMemory }: Props) {
  const { data, loading } = useMemory(memoryId);
  const navigate = useNavigate();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    },
    [onClose]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  // Backdrop click
  const handleBackdropClick = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  if (loading || !data || !("memory" in data)) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={handleBackdropClick}>
        <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl mx-4 p-6">
          <div className="animate-pulse space-y-4">
            <div className="h-6 bg-slate-700 rounded w-1/3" />
            <div className="h-24 bg-slate-700 rounded" />
            <div className="grid grid-cols-3 gap-3">
              <div className="h-12 bg-slate-700 rounded" />
              <div className="h-12 bg-slate-700 rounded" />
              <div className="h-12 bg-slate-700 rounded" />
            </div>
          </div>
        </div>
      </div>
    );
  }

  const { memory: m, edges } = data;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={handleBackdropClick}>
      <div className="bg-slate-900 border border-slate-700 rounded-xl shadow-2xl w-full max-w-2xl mx-4 max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${typeBadge[m.type] ?? "bg-slate-700 text-slate-300 border border-slate-600"}`}>
              {m.type}
            </span>
            {m.is_deprecated && (
              <span className="flex items-center gap-1 px-2.5 py-1 rounded-md text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
                <AlertTriangle className="w-3 h-3" /> deprecated
              </span>
            )}
            {m.project && (
              <span className="px-2 py-0.5 rounded text-xs text-slate-400 bg-slate-800 border border-slate-700">
                {m.project}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors p-1 rounded hover:bg-slate-800">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Body — scrollable */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {/* Content */}
          <div>
            <p className="text-slate-200 whitespace-pre-wrap leading-relaxed">{m.content}</p>
          </div>

          {/* Deprecated by */}
          {m.is_deprecated && m.deprecated_by && (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 rounded-lg text-xs">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0" />
              <span className="text-red-300">Superseded by:</span>
              <button
                onClick={() => onNavigateToMemory?.(m.deprecated_by!)}
                className="text-red-400 hover:text-red-300 font-mono underline underline-offset-2 truncate"
              >
                {m.deprecated_by}
              </button>
            </div>
          )}

          {/* File path & Code signature */}
          {(m.file_path || m.code_signature) && (
            <div className="space-y-2">
              {m.file_path && (
                <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs">
                  <FileCode className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="text-slate-400">File:</span>
                  <span className="text-slate-200 font-mono truncate">{m.file_path}</span>
                </div>
              )}
              {m.code_signature && (
                <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/60 border border-slate-700/50 rounded-lg text-xs">
                  <Hash className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                  <span className="text-slate-400">Signature:</span>
                  <span className="text-slate-200 font-mono truncate">{m.code_signature}</span>
                </div>
              )}
            </div>
          )}

          {/* Metadata grid */}
          <div className="grid grid-cols-3 gap-3">
            <MetaCard icon={<Clock className="w-3.5 h-3.5" />} label="Created" value={m.created_at ? new Date(m.created_at).toLocaleDateString() : "—"} />
            <MetaCard icon={<Eye className="w-3.5 h-3.5" />} label="Last Accessed" value={m.last_accessed ? new Date(m.last_accessed).toLocaleDateString() : "never"} />
            <MetaCard
              icon={<Database className="w-3.5 h-3.5" />}
              label="Decay"
              value={m.decay_score.toFixed(2)}
              valueClass={m.decay_score < 0.3 ? "text-red-400" : m.decay_score < 0.7 ? "text-yellow-400" : "text-green-400"}
            />
            <MetaCard icon={<Eye className="w-3.5 h-3.5" />} label="Access Count" value={String(m.access_count)} />
            <MetaCard icon={<Layers className="w-3.5 h-3.5" />} label="Elaborations" value={String(m.elaboration_count)} />
            <MetaCard icon={<Tag className="w-3.5 h-3.5" />} label="Source" value={m.source ?? "—"} />
          </div>

          {/* Tags */}
          {m.tags.length > 0 && (
            <div>
              <h4 className="text-slate-400 text-xs uppercase font-medium mb-2">Tags</h4>
              <div className="flex flex-wrap gap-1.5">
                {m.tags.map((t) => (
                  <span key={t} className="px-2 py-0.5 bg-slate-800 border border-slate-700 text-slate-300 rounded-md text-xs">
                    {t}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Edges */}
          <div>
            <h4 className="text-slate-400 text-xs uppercase font-medium mb-2 flex items-center gap-1.5">
              <GitFork className="w-3.5 h-3.5" /> Connections ({edges.length})
            </h4>
            {edges.length === 0 ? (
              <p className="text-slate-500 text-xs py-2">No connections</p>
            ) : (
              <div className="space-y-2">
                {edges.map((e) => (
                  <div
                    key={e.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors hover:bg-slate-800/80 ${edgeTypeBg[e.type] ?? "bg-slate-800/40 border-slate-700/30"}`}
                    onClick={() => {
                      const targetId = e.connected_memory?.id ?? (e.source === memoryId ? e.target : e.source);
                      onNavigateToMemory?.(targetId);
                    }}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <span className={`text-xs font-medium ${edgeTypeColor[e.type] ?? "text-slate-300"}`}>
                        {e.type.replace(/_/g, " ")}
                      </span>
                      <span className="text-slate-500 text-xs">w: {e.weight.toFixed(2)}</span>
                    </div>
                    {e.connected_memory && (
                      <div className="flex items-start gap-2">
                        <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${connectedTypeDot[e.connected_memory.type] ?? "bg-slate-500"}`} />
                        <p className="text-slate-300 text-xs leading-relaxed line-clamp-2">
                          {e.connected_memory.content}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* ID (small, copyable) */}
          <div className="flex items-center gap-2 text-xs text-slate-500 pt-1">
            <span>ID:</span>
            <code className="font-mono text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded select-all">{m.id}</code>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-2 p-4 border-t border-slate-700/50">
          <button
            onClick={() => {
              navigate(`/graph?focus=${m.id}`);
              onClose();
            }}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm font-medium transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> View in Graph
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm font-medium transition-colors border border-slate-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

function MetaCard({ icon, label, value, valueClass }: { icon: React.ReactNode; label: string; value: string; valueClass?: string }) {
  return (
    <div className="bg-slate-800/50 border border-slate-700/40 rounded-lg p-2.5">
      <div className="flex items-center gap-1.5 text-slate-400 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className={`text-sm font-medium truncate ${valueClass ?? "text-slate-200"}`}>{value}</p>
    </div>
  );
}
