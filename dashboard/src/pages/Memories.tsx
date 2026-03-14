import { useState } from "react";
import MemoryTable from "../components/MemoryTable.tsx";
import MemoryDialog from "../components/MemoryDialog.tsx";
import ProjectSelector from "../components/ProjectSelector.tsx";
import { useMemories } from "../hooks/useApi.ts";
import { Search, ChevronLeft, ChevronRight, Database, Eye, Layers, Filter } from "lucide-react";

export default function Memories() {
  const [project, setProject] = useState("");
  const [type, setType] = useState("");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("created");
  const [deprecated, setDeprecated] = useState(false);
  const [offset, setOffset] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const limit = 50;

  const { data, loading } = useMemories({
    project: project || undefined,
    type: type || undefined,
    search: search || undefined,
    sort,
    deprecated,
    limit,
    offset,
  });

  const memories = data?.items ?? [];
  const total = data?.total ?? 0;
  const pages = Math.ceil(total / limit);
  const currentPage = Math.floor(offset / limit) + 1;

  // Compute stats from visible set
  const typeBreakdown = memories.reduce<Record<string, number>>((acc, m) => {
    acc[m.type] = (acc[m.type] ?? 0) + 1; return acc;
  }, {});
  const avgDecay = memories.length > 0 ? memories.reduce((s, m) => s + m.decay_score, 0) / memories.length : 0;
  const avgAccess = memories.length > 0 ? memories.reduce((s, m) => s + m.access_count, 0) / memories.length : 0;
  const avgElab = memories.length > 0 ? memories.reduce((s, m) => s + m.elaboration_count, 0) / memories.length : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">Memories</h1>
          <span className="px-2.5 py-0.5 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-300 font-mono">{total}</span>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap items-center">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
          <input
            value={search}
            onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
            placeholder="Search content, tags, file paths..."
            className="w-full pl-9 pr-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-1 focus:ring-purple-500"
          />
        </div>
        <select value={type} onChange={(e) => { setType(e.target.value); setOffset(0); }}
          className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2">
          <option value="">All Types</option>
          <option value="semantic">Semantic</option>
          <option value="episodic">Episodic</option>
          <option value="procedural">Procedural</option>
        </select>
        <ProjectSelector value={project} onChange={(v) => { setProject(v); setOffset(0); }} />
        <select value={sort} onChange={(e) => setSort(e.target.value)}
          className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2">
          <option value="created">Newest</option>
          <option value="accessed">Last Accessed</option>
          <option value="decay">Lowest Decay</option>
        </select>
        <button
          onClick={() => { setDeprecated(!deprecated); setOffset(0); }}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm border transition-colors ${
            deprecated ? "bg-red-500/15 border-red-500/30 text-red-300" : "bg-slate-800 border-slate-700 text-slate-400 hover:text-slate-200"
          }`}
        >
          <Filter className="w-3.5 h-3.5" />
          {deprecated ? "Showing Deprecated" : "Include Deprecated"}
        </button>
      </div>

      {/* Stats Bar */}
      {memories.length > 0 && (
        <div className="flex items-center gap-6 px-4 py-2.5 bg-slate-800/30 border border-slate-700/30 rounded-lg">
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span className="flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" />
              {Object.entries(typeBreakdown).map(([t, c]) => (
                <span key={t} className="flex items-center gap-1">
                  <span className={`w-2 h-2 rounded-full ${t === "semantic" ? "bg-blue-500" : t === "episodic" ? "bg-green-500" : "bg-orange-500"}`} />
                  {c}
                </span>
              ))}
            </span>
            <span className="text-slate-600">|</span>
            <span className="flex items-center gap-1"><Eye className="w-3 h-3" /> avg access: <span className="text-slate-300 font-mono">{avgAccess.toFixed(1)}</span></span>
            <span className="text-slate-600">|</span>
            <span className="flex items-center gap-1"><Layers className="w-3 h-3" /> avg elab: <span className="text-slate-300 font-mono">{avgElab.toFixed(1)}×</span></span>
            <span className="text-slate-600">|</span>
            <span>avg decay: <span className={`font-mono ${avgDecay > 0.7 ? "text-green-400" : avgDecay > 0.3 ? "text-yellow-400" : "text-red-400"}`}>{avgDecay.toFixed(2)}</span></span>
          </div>
        </div>
      )}

      {/* Table */}
      <MemoryTable memories={memories} loading={loading} selectedId={selectedId} onSelect={setSelectedId} />

      {/* Pagination */}
      {pages > 1 && (
        <div className="flex items-center justify-center gap-4 py-2">
          <button disabled={currentPage <= 1} onClick={() => setOffset(Math.max(0, offset - limit))}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors">
            <ChevronLeft className="w-5 h-5" />
          </button>
          <div className="flex items-center gap-2">
            {Array.from({ length: Math.min(pages, 7) }, (_, i) => {
              let pageNum: number;
              if (pages <= 7) {
                pageNum = i + 1;
              } else if (currentPage <= 4) {
                pageNum = i + 1;
              } else if (currentPage >= pages - 3) {
                pageNum = pages - 6 + i;
              } else {
                pageNum = currentPage - 3 + i;
              }
              return (
                <button key={pageNum} onClick={() => setOffset((pageNum - 1) * limit)}
                  className={`w-8 h-8 rounded-lg text-sm font-medium transition-colors ${
                    pageNum === currentPage ? "bg-purple-600 text-white" : "text-slate-400 hover:bg-slate-800 hover:text-white"
                  }`}>
                  {pageNum}
                </button>
              );
            })}
          </div>
          <button disabled={currentPage >= pages} onClick={() => setOffset(offset + limit)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 disabled:opacity-30 transition-colors">
            <ChevronRight className="w-5 h-5" />
          </button>
        </div>
      )}

      {/* Memory Dialog */}
      {selectedId && (
        <MemoryDialog memoryId={selectedId} onClose={() => setSelectedId(null)} onNavigateToMemory={(id) => setSelectedId(id)} />
      )}
    </div>
  );
}
