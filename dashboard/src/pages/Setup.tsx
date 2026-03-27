import { useState } from "react";
import { useProject } from "../context/ProjectContext.tsx";
import { useSetupAll, useSetup } from "../hooks/useApi.ts";
import type { SetupStep, SetupStepStatus } from "../types/index.ts";
import {
  CheckCircle,
  Circle,
  Clock,
  SkipForward,
  AlertTriangle,
  Copy,
  ChevronRight,
  Rocket,
  BookOpen,
  Code2,
  FileText,
  MessageSquare,
  Layers,
  Search,
  Stethoscope,
  Target,
  TestTube,
  Shield,
  Zap,
  Settings,
} from "lucide-react";

const PHASE_COLORS: Record<string, string> = {
  install: "text-blue-400",
  init: "text-purple-400",
  smoke_test: "text-amber-400",
  health_check: "text-emerald-400",
  validation: "text-cyan-400",
  ready: "text-green-400",
};

const PHASE_LABELS: Record<string, string> = {
  install: "Installation",
  init: "Initialization",
  smoke_test: "Smoke Test",
  health_check: "Health Check",
  validation: "Validation",
  ready: "Ready",
};

const STEP_ICONS: Record<string, typeof Circle> = {
  skills_rules: Settings,
  mcp_config: Shield,
  doc_base: BookOpen,
  code_base: Code2,
  event_base: FileText,
  chat_base: MessageSquare,
  elaborate_base: Layers,
  queries: Search,
  diagnose: Stethoscope,
  content_gap: Target,
  elaborate_fix: Zap,
  final_queries: TestTube,
  final_health: Stethoscope,
  memory_ready: Rocket,
};

const STATUS_CONFIG: Record<
  SetupStepStatus,
  { icon: typeof Circle; color: string; bg: string; label: string }
> = {
  pending: { icon: Circle, color: "text-slate-500", bg: "bg-slate-800/50", label: "Pending" },
  in_progress: { icon: Clock, color: "text-amber-400", bg: "bg-amber-900/20", label: "In Progress" },
  completed: { icon: CheckCircle, color: "text-green-400", bg: "bg-green-900/20", label: "Completed" },
  skipped: { icon: SkipForward, color: "text-slate-400", bg: "bg-slate-800/30", label: "Skipped" },
  failed: { icon: AlertTriangle, color: "text-red-400", bg: "bg-red-900/20", label: "Failed" },
};

function ProgressRing({ pct }: { pct: number }) {
  const r = 52;
  const circ = 2 * Math.PI * r;
  const offset = circ - (pct / 100) * circ;
  const color = pct >= 100 ? "#22c55e" : pct >= 50 ? "#a78bfa" : "#64748b";

  return (
    <div className="relative w-36 h-36">
      <svg viewBox="0 0 120 120" className="w-full h-full -rotate-90">
        <circle cx="60" cy="60" r={r} fill="none" stroke="#1e293b" strokeWidth="8" />
        <circle
          cx="60"
          cy="60"
          r={r}
          fill="none"
          stroke={color}
          strokeWidth="8"
          strokeLinecap="round"
          strokeDasharray={circ}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-bold text-white">{pct}%</span>
        <span className="text-xs text-slate-400 mt-0.5">complete</span>
      </div>
    </div>
  );
}

function StepCard({
  step,
  isActive,
  index,
}: {
  step: SetupStep;
  isActive: boolean;
  index: number;
}) {
  const [copied, setCopied] = useState(false);
  const config = STATUS_CONFIG[step.status];
  void config.icon;
  const StepIcon = STEP_ICONS[step.step] || Circle;

  const copyPrompt = () => {
    const promptText = step.prompt_file
      ? `Read the file ${step.prompt_file} and follow the instructions for project setup.`
      : `Complete the "${step.title}" step for memory setup.`;
    navigator.clipboard.writeText(promptText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div
      className={`rounded-xl border transition-all duration-300 ${
        isActive
          ? "border-purple-500/50 bg-purple-900/10 ring-1 ring-purple-500/20"
          : step.status === "completed"
          ? "border-green-800/30 bg-slate-800/20"
          : step.status === "skipped"
          ? "border-slate-700/30 bg-slate-800/10 opacity-60"
          : "border-slate-700/30 bg-slate-800/30"
      }`}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Step number & status */}
          <div className="flex flex-col items-center gap-1 pt-0.5">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
                step.status === "completed"
                  ? "bg-green-500/20 text-green-400"
                  : isActive
                  ? "bg-purple-500/20 text-purple-400"
                  : "bg-slate-700/50 text-slate-500"
              }`}
            >
              {step.status === "completed" ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                index + 1
              )}
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <StepIcon className={`w-4 h-4 ${config.color}`} />
              <h3 className={`font-semibold text-sm ${isActive ? "text-white" : "text-slate-200"}`}>
                {step.title}
              </h3>
              <span
                className={`px-2 py-0.5 rounded-full text-xs ${config.bg} ${config.color}`}
              >
                {config.label}
              </span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">{step.description}</p>

            {/* Timing info */}
            {step.completed_at && (
              <p className="text-xs text-slate-500 mt-1">
                Completed: {new Date(step.completed_at).toLocaleDateString()}
              </p>
            )}

            {/* Action area for active step */}
            {isActive && step.status !== "completed" && step.status !== "skipped" && (
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={copyPrompt}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-medium rounded-lg transition-colors"
                >
                  {copied ? (
                    <>
                      <CheckCircle className="w-3.5 h-3.5" />
                      Copied!
                    </>
                  ) : (
                    <>
                      <Copy className="w-3.5 h-3.5" />
                      Copy Prompt
                    </>
                  )}
                </button>
                {step.prompt_file && (
                  <span className="text-xs text-slate-500">
                    {step.prompt_file}
                  </span>
                )}
              </div>
            )}

            {/* Result summary if available */}
            {step.result && (
              <div className="mt-2 p-2 bg-slate-900/50 rounded text-xs text-slate-400 font-mono overflow-x-auto">
                {step.result.length > 200 ? step.result.slice(0, 200) + "..." : step.result}
              </div>
            )}
          </div>

          {/* Phase badge */}
          <span className={`text-xs font-medium ${PHASE_COLORS[step.phase] || "text-slate-400"}`}>
            {PHASE_LABELS[step.phase] || step.phase}
          </span>
        </div>
      </div>
    </div>
  );
}

export default function Setup() {
  const { project: globalProject, setProject } = useProject();
  const { data: projects, loading: loadingProjects } = useSetupAll(true);

  // Use global project if set, otherwise auto-select first project
  const activeProject = globalProject || (projects && projects.length > 0 ? projects[0].project : null);
  const { data: setup, loading: loadingSetup } = useSetup(activeProject, true);

  const steps = setup?.steps || [];
  const activeStepIndex = steps.findIndex(
    (s) => s.status === "pending" || s.status === "in_progress" || s.status === "failed"
  );

  if (loadingProjects) {
    return (
      <div className="flex items-center justify-center h-64 text-slate-400">
        Loading...
      </div>
    );
  }

  if (!projects || projects.length === 0) {
    return (
      <div className="max-w-2xl mx-auto mt-20 text-center">
        <Rocket className="w-16 h-16 text-slate-600 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-white mb-2">No Projects Yet</h1>
        <p className="text-slate-400 mb-6">
          Initialize your first project to get started with MangoBrain.
        </p>
        <div className="bg-slate-800/50 rounded-xl p-6 text-left">
          <p className="text-sm text-slate-300 mb-3">Run this command in your terminal:</p>
          <code className="block bg-slate-900 rounded-lg p-3 text-sm text-purple-300 font-mono">
            mangobrain init --project myproject --path /path/to/project
          </code>
          <p className="text-xs text-slate-500 mt-3">
            Or use the MCP tool in Claude Code:{" "}
            <code className="text-purple-400">setup_status(project="myproject", action="init")</code>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <p className="text-sm text-slate-400">
          Track initialization progress for your projects
        </p>
        {projects.length > 1 && (
          <select
            value={activeProject || ""}
            onChange={(e) => setProject(e.target.value)}
            className="bg-slate-800 border border-slate-700 rounded-lg px-3 py-1.5 text-sm text-white"
          >
            {projects.map((p) => (
              <option key={p.project} value={p.project}>
                {p.project} {p.is_ready ? "(Ready)" : `(${p.progress_pct}%)`}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Progress overview */}
      {setup && (
        <div className="bg-slate-800/30 rounded-2xl border border-slate-700/30 p-6">
          <div className="flex items-center gap-8">
            <ProgressRing pct={setup.progress_pct} />
            <div className="flex-1">
              <h2 className="text-xl font-bold text-white mb-1">
                {setup.project}
                {setup.is_ready && (
                  <span className="ml-2 px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                    READY
                  </span>
                )}
              </h2>
              <p className="text-sm text-slate-400">
                {setup.completed} of {setup.total_steps} steps completed
                {setup.skipped > 0 && `, ${setup.skipped} skipped`}
              </p>
              {setup.current_step && !setup.is_ready && (
                <div className="mt-3 flex items-center gap-2 text-sm">
                  <ChevronRight className="w-4 h-4 text-purple-400" />
                  <span className="text-purple-300 font-medium">
                    Next: {setup.current_step.title}
                  </span>
                </div>
              )}
              {setup.is_ready && (
                <p className="mt-3 text-sm text-green-400">
                  Memory system is fully operational. Use /discuss and /task with persistent memory.
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Steps list */}
      {loadingSetup ? (
        <div className="text-center text-slate-400 py-8">Loading steps...</div>
      ) : (
        <div className="space-y-2">
          {steps.map((step, i) => (
            <StepCard
              key={`${step.phase}-${step.step}`}
              step={step}
              isActive={i === activeStepIndex}
              index={i}
            />
          ))}
        </div>
      )}
    </div>
  );
}
