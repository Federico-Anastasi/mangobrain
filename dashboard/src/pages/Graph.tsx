import { useState, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import GraphView from "../components/GraphView.tsx";
import MemoryDialog from "../components/MemoryDialog.tsx";
import { useProject } from "../context/ProjectContext.tsx";
import { useGraph } from "../hooks/useApi.ts";
import { Search, GitFork, Database, Layers } from "lucide-react";

const NODE_TYPE_COLORS: Record<string, string> = {
  semantic: "#3b82f6",
  episodic: "#22c55e",
  procedural: "#f97316",
  deprecated: "#6b7280",
};

const EDGE_TYPE_COLORS: Record<string, { color: string; label: string }> = {
  relates_to: { color: "#4b5563", label: "Relates to" },
  depends_on: { color: "#3b82f6", label: "Depends on" },
  caused_by: { color: "#ef4444", label: "Caused by" },
  co_occurs: { color: "#8b5cf6", label: "Co-occurs" },
  contradicts: { color: "#f59e0b", label: "Contradicts" },
  supersedes: { color: "#06b6d4", label: "Supersedes" },
};

export default function Graph() {
  const [searchParams] = useSearchParams();
  const focusId = searchParams.get("focus");

  const { project } = useProject();
  const [minWeight, setMinWeight] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(focusId);
  const [searchQuery, setSearchQuery] = useState("");
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set());

  const { data, loading } = useGraph(project || undefined, minWeight);
  const allNodes = data?.nodes ?? [];
  const allEdges = data?.edges ?? [];

  // Filter nodes by type visibility
  const { nodes, edges } = useMemo(() => {
    const visibleNodes = allNodes.filter(n => {
      if (hiddenTypes.has(n.type)) return false;
      if (n.is_deprecated && hiddenTypes.has("deprecated")) return false;
      return true;
    });
    const visibleIds = new Set(visibleNodes.map(n => n.id));
    const visibleEdges = allEdges.filter(e => visibleIds.has(e.source) && visibleIds.has(e.target));
    return { nodes: visibleNodes, edges: visibleEdges };
  }, [allNodes, allEdges, hiddenTypes]);

  // Search: find node by content match
  const searchResult = useMemo(() => {
    if (!searchQuery || searchQuery.length < 2) return null;
    const q = searchQuery.toLowerCase();
    return allNodes.find(n => n.label.toLowerCase().includes(q));
  }, [searchQuery, allNodes]);

  // Stats
  const edgeTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    edges.forEach(e => { counts[e.type] = (counts[e.type] ?? 0) + 1; });
    return counts;
  }, [edges]);

  const toggleType = (type: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  };

  return (
    <div className="flex flex-col h-full space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Graph</h1>
          <span className="text-xs text-slate-400 flex items-center gap-2">
            <Database className="w-3.5 h-3.5" /> {nodes.length} nodes
            <GitFork className="w-3.5 h-3.5 ml-2" /> {edges.length} edges
          </span>
        </div>
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-slate-400" />
            <input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && searchResult) {
                  setSelectedId(searchResult.id);
                }
              }}
              placeholder="Search nodes..."
              className="pl-8 pr-3 py-1.5 bg-slate-800 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500 w-44" />
            {searchResult && searchQuery.length >= 2 && (
              <button onClick={() => { setSelectedId(searchResult.id); setSearchQuery(""); }}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-purple-400 hover:text-purple-300">
                Go
              </button>
            )}
          </div>
          {/* Weight slider */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Min weight</span>
            <input type="range" min={0} max={1} step={0.05} value={minWeight}
              onChange={(e) => setMinWeight(Number(e.target.value))}
              className="w-20 accent-purple-500" />
            <span className="text-xs text-slate-300 w-8 font-mono">{minWeight.toFixed(2)}</span>
          </div>
        </div>
      </div>

      {/* Legends + Filters */}
      <div className="flex items-center justify-between">
        {/* Node type toggles */}
        <div className="flex gap-2">
          {Object.entries(NODE_TYPE_COLORS).map(([type, color]) => {
            const isHidden = hiddenTypes.has(type);
            const count = type === "deprecated"
              ? allNodes.filter(n => n.is_deprecated).length
              : allNodes.filter(n => n.type === type && !n.is_deprecated).length;
            return (
              <button key={type} onClick={() => toggleType(type)}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs border transition-all ${
                  isHidden ? "opacity-40 border-slate-700 bg-slate-800/30" : "border-slate-600 bg-slate-800/60"
                }`}>
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: color }} />
                <span className="text-slate-300 capitalize">{type}</span>
                <span className="text-slate-500 font-mono">{count}</span>
              </button>
            );
          })}
        </div>

        {/* Edge type legend */}
        <div className="flex gap-3 text-[11px] text-slate-500">
          {Object.entries(EDGE_TYPE_COLORS).map(([type, { color, label }]) => {
            const count = edgeTypeCounts[type] ?? 0;
            if (count === 0) return null;
            return (
              <span key={type} className="flex items-center gap-1">
                <span className="w-4 h-0.5 rounded inline-block" style={{ backgroundColor: color }} />
                {label} <span className="font-mono text-slate-600">{count}</span>
              </span>
            );
          })}
        </div>
      </div>

      {/* Graph */}
      <div className="flex-1 min-h-[500px]">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-2 border-purple-500 border-t-transparent rounded-full animate-spin" />
              <span className="text-slate-500 text-sm">Loading graph...</span>
            </div>
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <Layers className="w-10 h-10 mx-auto mb-2 text-slate-600" />
              <p>No data to display</p>
              {hiddenTypes.size > 0 && (
                <button onClick={() => setHiddenTypes(new Set())}
                  className="mt-2 text-sm text-purple-400 hover:text-purple-300">Reset filters</button>
              )}
            </div>
          </div>
        ) : (
          <GraphView nodes={nodes} edges={edges} onNodeClick={setSelectedId} focusNodeId={selectedId ?? focusId} />
        )}
      </div>

      {/* Memory Dialog */}
      {selectedId && (
        <MemoryDialog memoryId={selectedId} onClose={() => setSelectedId(null)} onNavigateToMemory={(id) => setSelectedId(id)} />
      )}
    </div>
  );
}
