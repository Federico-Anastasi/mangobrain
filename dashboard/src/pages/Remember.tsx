import { useState, useCallback } from "react";
import { Search, Zap, Clock, Layers, ChevronDown, ChevronRight, Tag, FileCode, Link2 } from "lucide-react";
import ProjectSelector from "../components/ProjectSelector.tsx";

const BASE_URL = "http://localhost:3101";

interface RememberResult {
  id: string;
  content: string;
  type: string;
  project: string;
  tags: string[];
  score: number;
  file_path?: string;
  code_signature?: string;
  access_count: number;
  decay_score: number;
  created_at: string;
  token_count: number;
}

interface RememberResponse {
  query: string;
  mode: string;
  project: string | null;
  count: number;
  results: RememberResult[];
}

const modeConfig = {
  deep: { label: "Deep", icon: Layers, color: "purple", desc: "~20 results, full graph propagation" },
  quick: { label: "Quick", icon: Zap, color: "yellow", desc: "~6 results, fast lookup" },
  recent: { label: "Recent", icon: Clock, color: "blue", desc: "~15 results, time-weighted" },
} as const;

export default function Remember() {
  const [query, setQuery] = useState("");
  const [mode, setMode] = useState<"deep" | "quick" | "recent">("deep");
  const [project, setProject] = useState<string | undefined>();
  const [results, setResults] = useState<RememberResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState<number | null>(null);

  const handleSearch = useCallback(async () => {
    if (!query.trim() && mode !== "recent") return;
    setLoading(true);
    setError(null);
    setExpandedId(null);
    const start = performance.now();

    try {
      const params = new URLSearchParams({ query: query.trim(), mode });
      if (project) params.set("project", project);
      const res = await fetch(`${BASE_URL}/api/remember?${params}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data: RememberResponse = await res.json();
      setResults(data);
      setElapsed(Math.round(performance.now() - start));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [query, mode, project]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSearch();
  };

  const scoreColor = (score: number) => {
    if (score >= 0.85) return "text-green-400";
    if (score >= 0.75) return "text-yellow-400";
    if (score >= 0.65) return "text-orange-400";
    return "text-red-400";
  };

  const typeColor = (type: string) => {
    switch (type) {
      case "semantic": return "bg-blue-500/20 text-blue-300 border-blue-500/30";
      case "episodic": return "bg-amber-500/20 text-amber-300 border-amber-500/30";
      case "procedural": return "bg-green-500/20 text-green-300 border-green-500/30";
      default: return "bg-slate-500/20 text-slate-300 border-slate-500/30";
    }
  };

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Remember</h1>
        <p className="text-slate-400 text-sm mt-1">
          Query the memory engine — same retrieval as Claude&apos;s MCP tool
        </p>
      </div>

      {/* Search bar */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700 p-4 space-y-3">
        <div className="flex gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Keywords: booking wizard localStorage state persistence gotcha..."
              className="w-full bg-slate-900 border border-slate-700 rounded-lg pl-10 pr-4 py-2.5 text-sm text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
            />
          </div>
          <button
            onClick={handleSearch}
            disabled={loading || (!query.trim() && mode !== "recent")}
            className="px-5 py-2.5 bg-purple-600 hover:bg-purple-500 disabled:bg-slate-700 disabled:text-slate-500 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {loading ? "Searching..." : "Search"}
          </button>
        </div>

        {/* Mode + Project */}
        <div className="flex items-center gap-4">
          <div className="flex gap-1 bg-slate-900 rounded-lg p-0.5">
            {(Object.keys(modeConfig) as Array<keyof typeof modeConfig>).map((m) => {
              const cfg = modeConfig[m];
              const Icon = cfg.icon;
              return (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                    mode === m
                      ? `bg-${cfg.color}-500/20 text-${cfg.color}-300 border border-${cfg.color}-500/30`
                      : "text-slate-400 hover:text-white"
                  }`}
                  title={cfg.desc}
                >
                  <Icon className="w-3.5 h-3.5" />
                  {cfg.label}
                </button>
              );
            })}
          </div>
          <div className="w-px h-6 bg-slate-700" />
          <ProjectSelector value={project ?? ""} onChange={(v) => setProject(v || undefined)} />
          <div className="ml-auto text-xs text-slate-500">
            {modeConfig[mode].desc}
          </div>
        </div>
      </div>

      {/* Results */}
      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-300 text-sm">
          {error}
        </div>
      )}

      {results && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-slate-400">
              <span className="text-white font-medium">{results.count}</span> results
              {elapsed !== null && <span className="text-slate-600"> · {elapsed}ms</span>}
            </span>
            <span className="text-slate-600 text-xs">
              mode: {results.mode} · query: &quot;{results.query}&quot;
            </span>
          </div>

          <div className="space-y-2">
            {results.results.map((r, i) => (
              <div
                key={r.id}
                className="bg-slate-800/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-colors"
              >
                {/* Main row */}
                <button
                  onClick={() => setExpandedId(expandedId === r.id ? null : r.id)}
                  className="w-full flex items-start gap-3 p-3 text-left"
                >
                  {/* Rank */}
                  <span className="text-slate-600 text-xs font-mono w-5 pt-0.5 shrink-0">
                    #{i + 1}
                  </span>

                  {/* Score bar */}
                  <div className="w-12 shrink-0 pt-0.5">
                    <div className={`text-xs font-mono font-bold ${scoreColor(r.score)}`}>
                      {(r.score * 100).toFixed(0)}%
                    </div>
                    <div className="mt-0.5 h-1 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-purple-500 rounded-full"
                        style={{ width: `${r.score * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 leading-relaxed">
                      {expandedId === r.id ? r.content : r.content.slice(0, 200) + (r.content.length > 200 ? "..." : "")}
                    </p>
                  </div>

                  {/* Type badge + expand */}
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={`text-[10px] px-1.5 py-0.5 rounded border ${typeColor(r.type)}`}>
                      {r.type}
                    </span>
                    {expandedId === r.id ? (
                      <ChevronDown className="w-4 h-4 text-slate-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-500" />
                    )}
                  </div>
                </button>

                {/* Expanded details */}
                {expandedId === r.id && (
                  <div className="border-t border-slate-700 px-3 py-2 text-xs space-y-2">
                    <div className="flex flex-wrap gap-3 text-slate-400">
                      <span>ID: <code className="text-slate-500">{r.id.slice(0, 8)}</code></span>
                      <span>Decay: {(r.decay_score * 100).toFixed(0)}%</span>
                      <span>Accessed: {r.access_count}x</span>
                      <span>Tokens: {r.token_count}</span>
                      <span>Created: {new Date(r.created_at).toLocaleDateString()}</span>
                    </div>
                    {r.file_path && (
                      <div className="flex items-center gap-1.5 text-slate-400">
                        <FileCode className="w-3 h-3" />
                        <code className="text-slate-300">{r.file_path}</code>
                        {r.code_signature && (
                          <>
                            <Link2 className="w-3 h-3 ml-2" />
                            <code className="text-slate-300">{r.code_signature}</code>
                          </>
                        )}
                      </div>
                    )}
                    {r.tags.length > 0 && (
                      <div className="flex items-center gap-1.5 flex-wrap">
                        <Tag className="w-3 h-3 text-slate-500" />
                        {r.tags.map((t) => (
                          <span key={t} className="bg-slate-700 text-slate-300 px-1.5 py-0.5 rounded text-[10px]">
                            {t}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>

          {results.count === 0 && (
            <div className="text-center py-12 text-slate-500">
              <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No memories found for this query.</p>
              <p className="text-xs mt-1">Try different keywords or a broader mode.</p>
            </div>
          )}
        </div>
      )}

      {/* Empty state */}
      {!results && !loading && (
        <div className="text-center py-16 text-slate-500">
          <Search className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-lg">Query your memory</p>
          <p className="text-sm mt-1">
            Use keywords, not natural language.
            <br />
            Example: <code className="text-purple-400">booking wizard localStorage state gotcha</code>
          </p>
        </div>
      )}
    </div>
  );
}
