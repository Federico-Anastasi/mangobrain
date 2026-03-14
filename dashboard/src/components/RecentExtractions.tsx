import type { Session } from "../types/index.ts";

interface Props {
  sessions: Session[];
  loading: boolean;
}

export default function RecentExtractions({ sessions, loading }: Props) {
  const recent = sessions.slice(0, 5);

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <h3 className="text-sm font-medium text-slate-400 mb-3">Recent Extractions</h3>
      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-10 bg-slate-700/30 rounded animate-pulse" />
          ))}
        </div>
      ) : recent.length === 0 ? (
        <p className="text-slate-500 text-sm">No extractions yet.</p>
      ) : (
        <div className="space-y-2">
          {recent.map((s) => (
            <div key={s.id} className="flex items-center justify-between p-2 rounded-lg bg-slate-900/50">
              <div>
                <span className="text-sm text-slate-200">{s.project ?? "unknown"}</span>
                {s.run_name && <span className="text-xs text-slate-500 ml-2">{s.run_name}</span>}
              </div>
              <div className="text-right">
                <span className="text-sm font-medium text-purple-400">{s.memories_extracted}</span>
                <span className="text-xs text-slate-500 ml-1">memories</span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
