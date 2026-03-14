import { AlertTriangle, Info } from "lucide-react";
import type { HealthAlert } from "../types/index.ts";

interface Props {
  alerts: HealthAlert[];
}

export default function AlertsPanel({ alerts }: Props) {
  if (alerts.length === 0) {
    return (
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
        <h3 className="text-sm font-medium text-slate-400 mb-2">Alerts</h3>
        <p className="text-slate-500 text-sm">No alerts. Everything looks good.</p>
      </div>
    );
  }

  return (
    <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4">
      <h3 className="text-sm font-medium text-slate-400 mb-3">Alerts</h3>
      <div className="space-y-2">
        {alerts.map((a, i) => (
          <div
            key={i}
            className={`flex items-start gap-3 p-3 rounded-lg ${
              a.severity === "warning" ? "bg-yellow-500/10 border border-yellow-500/20" : "bg-blue-500/10 border border-blue-500/20"
            }`}
          >
            {a.severity === "warning" ? (
              <AlertTriangle className="w-4 h-4 text-yellow-400 mt-0.5 shrink-0" />
            ) : (
              <Info className="w-4 h-4 text-blue-400 mt-0.5 shrink-0" />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-slate-200">{a.message}</p>
              <code className="text-xs text-slate-400 mt-1 block">{a.action}</code>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
