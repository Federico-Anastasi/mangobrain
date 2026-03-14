import { Brain, Terminal, Zap, BookOpen, GitFork, Search, ArrowRight, Layers } from "lucide-react";

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Brain;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="bg-slate-800/30 rounded-2xl border border-slate-700/30 p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="p-2 bg-purple-500/10 rounded-lg">
          <Icon className="w-5 h-5 text-purple-400" />
        </div>
        <h2 className="text-lg font-bold text-white">{title}</h2>
      </div>
      <div className="text-sm text-slate-300 leading-relaxed space-y-3">{children}</div>
    </section>
  );
}

function ToolRow({ name, desc }: { name: string; desc: string }) {
  return (
    <div className="flex items-start gap-3 py-2 border-b border-slate-700/30 last:border-0">
      <code className="text-purple-300 text-xs font-mono bg-slate-900/50 px-2 py-0.5 rounded whitespace-nowrap">
        {name}
      </code>
      <span className="text-xs text-slate-400">{desc}</span>
    </div>
  );
}

function WorkflowStep({
  num,
  skill,
  desc,
}: {
  num: number;
  skill: string;
  desc: string;
}) {
  return (
    <div className="flex items-start gap-3">
      <div className="w-7 h-7 rounded-full bg-purple-500/20 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-xs font-bold text-purple-300">{num}</span>
      </div>
      <div>
        <code className="text-purple-300 text-sm font-mono">{skill}</code>
        <p className="text-xs text-slate-400 mt-0.5">{desc}</p>
      </div>
    </div>
  );
}

export default function Guide() {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Guide</h1>
        <p className="text-sm text-slate-400 mt-1">
          Everything you need to know about MangoBrain
        </p>
      </div>

      {/* What is MangoBrain */}
      <Section icon={Brain} title="What is MangoBrain?">
        <p>
          MangoBrain is a <strong className="text-white">persistent, associative memory system</strong> for
          Claude Code. It remembers decisions, patterns, bugs, and architecture across sessions so Claude
          starts every conversation with context instead of a blank slate.
        </p>
        <p>
          It also provides a <strong className="text-white">complete development workflow</strong> (discuss,
          task, agents) that naturally integrates memory into how you work. Think of it as Claude's
          long-term brain.
        </p>
      </Section>

      {/* Quick Start */}
      <Section icon={Terminal} title="Quick Start">
        <div className="bg-slate-900/50 rounded-xl p-4 space-y-3 font-mono text-xs">
          <div>
            <span className="text-slate-500"># Initialize a project</span>
            <br />
            <span className="text-green-400">mango-brain</span>{" "}
            <span className="text-white">init --project myproject --path /path/to/project</span>
          </div>
          <div>
            <span className="text-slate-500"># Check system health</span>
            <br />
            <span className="text-green-400">mango-brain</span>{" "}
            <span className="text-white">doctor</span>
          </div>
          <div>
            <span className="text-slate-500"># Start the API + dashboard</span>
            <br />
            <span className="text-green-400">mango-brain</span>{" "}
            <span className="text-white">serve --api</span>
          </div>
          <div>
            <span className="text-slate-500"># View setup progress</span>
            <br />
            <span className="text-green-400">mango-brain</span>{" "}
            <span className="text-white">status --project myproject</span>
          </div>
        </div>
        <p className="text-xs text-slate-500">
          After init, go to the Setup tab to track initialization progress step by step.
        </p>
      </Section>

      {/* Daily Workflow */}
      <Section icon={Zap} title="Daily Workflow">
        <div className="space-y-4">
          <WorkflowStep
            num={1}
            skill="/discuss"
            desc="Brainstorm and plan. Memory provides past decisions, known bugs, and relevant patterns as context. Creates a task.md file."
          />
          <div className="flex justify-center">
            <ArrowRight className="w-4 h-4 text-slate-600" />
          </div>
          <WorkflowStep
            num={2}
            skill="/task"
            desc="Execute the plan. Analyzers recall relevant memory. Executors write code. Verifier checks quality. Mem-manager saves new knowledge."
          />
          <div className="flex justify-center">
            <ArrowRight className="w-4 h-4 text-slate-600" />
          </div>
          <WorkflowStep
            num={3}
            skill="/memorize"
            desc="End of free session (without /task). Saves what you discussed and decided to memory."
          />
        </div>
        <div className="mt-4 p-3 bg-slate-900/30 rounded-lg border border-slate-700/20">
          <p className="text-xs text-slate-400">
            <strong className="text-slate-300">Periodic maintenance:</strong> Run{" "}
            <code className="text-purple-300">/elaborate</code> weekly to consolidate memory and{" "}
            <code className="text-purple-300">/health-check</code> monthly to optimize.
          </p>
        </div>
      </Section>

      {/* Skills Reference */}
      <Section icon={BookOpen} title="Skills Reference">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {[
            { name: "/discuss", desc: "Plan + brainstorm with memory context. Spawns analyzer agents, generates task.md." },
            { name: "/task", desc: "Execute tasks. Full cycle: analyze, plan, execute, verify, close with mem-manager." },
            { name: "/memorize", desc: "End-of-session sync. Saves decisions and work to memory." },
            { name: "/init", desc: "Initialize memory for a project. Guided multi-phase setup." },
            { name: "/elaborate", desc: "Consolidate memory. Build graph connections, find contradictions." },
            { name: "/health-check", desc: "Diagnose + optimize memory health. Prescriptions and auto-fix." },
            { name: "/smoke-test", desc: "Test retrieval quality with diverse queries." },
          ].map((s) => (
            <div key={s.name} className="p-3 bg-slate-900/30 rounded-lg">
              <code className="text-purple-300 text-sm font-mono font-bold">{s.name}</code>
              <p className="text-xs text-slate-400 mt-1">{s.desc}</p>
            </div>
          ))}
        </div>
      </Section>

      {/* Agents */}
      <Section icon={Layers} title="Agents">
        <p className="text-xs text-slate-500 mb-3">
          Spawned by /discuss and /task. You don't invoke them directly.
        </p>
        <div className="space-y-2">
          {[
            { name: "analyzer", desc: "Explores code + recalls relevant memory. Read-only. Returns findings, patterns, risks.", color: "text-blue-400" },
            { name: "executor", desc: "Implements code changes. 100% code focus, no memory tools. 1-2 files per task.", color: "text-green-400" },
            { name: "verifier", desc: "Runs build, type checks, logs. Recalls known issues from memory. Reports confidence level.", color: "text-amber-400" },
            { name: "mem-manager", desc: "Saves new knowledge, syncs codebase changes, tracks WIP. Runs at session close.", color: "text-purple-400" },
          ].map((a) => (
            <div key={a.name} className="flex items-start gap-3 p-3 bg-slate-900/20 rounded-lg">
              <span className={`font-mono text-sm font-bold ${a.color}`}>{a.name}</span>
              <span className="text-xs text-slate-400">{a.desc}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* How Memory Works */}
      <Section icon={GitFork} title="How Memory Works">
        <div className="space-y-2">
          <p>
            Memories are <strong className="text-white">atomic units</strong> (2-5 lines each) stored with
            embeddings in a graph structure. Three retrieval modes:
          </p>
          <div className="grid grid-cols-3 gap-3">
            {[
              { mode: "deep", results: "~20", when: "Session/task start", desc: "Full graph propagation" },
              { mode: "quick", results: "~6", when: "Mid-task lookups", desc: "Light, focused" },
              { mode: "recent", results: "~15", when: "WIP context", desc: "Temporal + neighbors" },
            ].map((m) => (
              <div key={m.mode} className="p-3 bg-slate-900/30 rounded-lg text-center">
                <code className="text-purple-300 text-sm font-bold">{m.mode}</code>
                <p className="text-xs text-slate-400 mt-1">{m.results} results</p>
                <p className="text-xs text-slate-500">{m.when}</p>
              </div>
            ))}
          </div>
          <p className="text-xs text-slate-500">
            The graph uses typed edges (depends_on, caused_by, contradicts, supersedes) to propagate
            relevance. Memories decay over time — episodic fast, procedural slow.
          </p>
        </div>
      </Section>

      {/* MCP Tools */}
      <Section icon={Search} title="MCP Tools Reference">
        <div className="space-y-0.5">
          <ToolRow name="remember" desc="Retrieve relevant memories (deep/quick/recent modes)" />
          <ToolRow name="memorize" desc="Save new memories with embeddings and relations" />
          <ToolRow name="update_memory" desc="Modify content, tags, file_path, deprecate" />
          <ToolRow name="extract_session" desc="Parse Claude Code chat JSONL for extraction" />
          <ToolRow name="prepare_elaboration" desc="Select seeds and build working set for elaboration" />
          <ToolRow name="apply_elaboration" desc="Apply Claude's elaboration updates to DB" />
          <ToolRow name="sync_codebase" desc="Detect stale/orphan memories vs. filesystem" />
          <ToolRow name="diagnose" desc="Health score, prescriptions, content gaps" />
          <ToolRow name="stats" desc="System statistics and health alerts" />
          <ToolRow name="list_memories" desc="Search/filter memories with pagination" />
          <ToolRow name="setup_status" desc="Get/update setup progress for a project" />
          <ToolRow name="reinforce" desc="Boost co-occurrence edges between memories" />
          <ToolRow name="decay" desc="Apply temporal decay to all memories" />
        </div>
      </Section>

      {/* Footer */}
      <div className="text-center text-xs text-slate-600 pb-8">
        MangoBrain v3.0 — Persistent memory + workflow system for Claude Code
      </div>
    </div>
  );
}
