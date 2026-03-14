<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/react-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/MCP-compatible-8A2BE2?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
</p>

<h1 align="center">🧠 MangoBrain</h1>

<p align="center">
  <strong>A development system for Claude Code where every session learns from the last</strong>
</p>

<p align="center">
  <em>Plan with /discuss. Execute with /task. Knowledge saves itself.</em>
</p>

---

## The Problem

Claude Code forgets everything between sessions. Every new conversation starts from zero — you re-explain architecture, re-discover bugs, re-make decisions. The longer your project lives, the more you repeat yourself.

Memory MCP servers exist, but they're just databases. They store and retrieve. You still have to manually decide what to save, when to recall, and how to structure it. The memory doesn't participate in your workflow — it sits next to it.

## How MangoBrain Works

MangoBrain is not a memory store. It's a **complete development workflow** that builds memory as a side-effect of doing real work.

```
 /discuss                    /task                         automatic
 ┌──────────────┐      ┌───────────────────┐      ┌──────────────────┐
 │ Plan a feature│      │ Execute the plan   │      │ mem-manager      │
 │              │      │                   │      │ saves what you   │
 │ Claude starts │─────▶│ analyzer explores  │─────▶│ learned, what    │
 │ by recalling  │      │   with memory     │      │ broke, what      │
 │ past decisions│      │ executor codes     │      │ decisions were   │
 │ and known bugs│      │ verifier checks    │      │ made — without   │
 │              │      │   known issues    │      │ you doing        │
 │ You plan     │      │                   │      │ anything         │
 │ better.      │      │ You ship faster.  │      │ Next session     │
 │              │      │                   │      │ starts smarter.  │
 └──────────────┘      └───────────────────┘      └──────────────────┘
```

**Session 1:** You tell Claude that prices must be stored in cents, not euros.
**Session 47:** Claude is about to write price logic. The memory surfaces automatically. Claude already knows.

**Session 3:** A timezone bug costs you 2 hours debugging.
**Session 28:** Claude touches date logic. The verifier recalls the timezone gotcha. The bug doesn't happen again.

This is the closed loop that no other tool provides: **work → capture → recall → better work**.

---

## How It's Different

Most tools give you a piece of the puzzle. MangoBrain is the whole puzzle.

| | Memory Store | Workflow Framework | MangoBrain |
|---|---|---|---|
| | *Mem0, Official MCP, WhenMoon* | *Ruflo, Claude Pilot, cc-sdd* | |
| **Remembers across sessions** | ✅ | ❌ or basic | ✅ |
| **Structured workflow** | ❌ | ✅ | ✅ |
| **Specialized agents** | ❌ | Some | ✅ 4 agents with strict roles |
| **Graph relationships** | ❌ | ❌ | ✅ typed edges + propagation |
| **Temporal decay** | ❌ | ❌ | ✅ episodic/semantic/procedural |
| **Contradicts & supersedes** | ❌ | ❌ | ✅ outdated info auto-suppressed |
| **Memory captures automatically** | ❌ | ❌ | ✅ mem-manager at session close |
| **Memory informs execution** | ❌ | ❌ | ✅ analyzer + verifier query memory |
| **Health monitoring** | ❌ | ❌ | ✅ dashboard + diagnose + alerts |

> **The difference:** other tools give you storage or structure. MangoBrain gives you a system where the *verifier* knows that bug #47 already happened, the *analyzer* starts with architectural context from 30 sessions ago, and the *mem-manager* captures what worked — without you lifting a finger.

---

## The Workflow

### Daily cycle

```
/discuss ──→ /task ──→ knowledge saved automatically
    │            │              │
    │            │              ▼
    │            │        Next /discuss starts
    │            │        with more context
    │            ▼
    │      4 specialized agents:
    │      • analyzer (explores code + recalls memory)
    │      • executor (writes code — 100% focused, no memory)
    │      • verifier (QA + checks past known issues)
    │      • mem-manager (saves everything at close)
    │
    ▼
  Produces task.md → fed into /task
```

### `/discuss` — Plan with memory
You describe what you want to build. Claude recalls past decisions, known bugs, architectural patterns. Analyzer agents explore the codebase *and* query memory for relevant gotchas. You plan with full context. Output: a `task.md` ready for execution.

### `/task` — Execute with agents
Claude reads the task, spawns analyzers (code + memory), creates a plan, then sends executors to write code. The verifier checks the result *and* queries memory for known issues in the areas touched. At close, the mem-manager captures everything learned.

### `/memorize` — Manual save (free sessions)
For sessions outside the discuss→task cycle. Spawns the mem-manager to extract and save what happened.

### Maintenance

| Skill | When | What it does |
|-------|------|-------------|
| `/elaborate` | Weekly | Consolidates memory: builds graph edges, finds contradictions, creates abstractions |
| `/health-check` | Monthly | Diagnoses memory health, finds content gaps, runs targeted fixes |
| `/smoke-test` | After changes | Tests retrieval quality with 10-20 diverse queries |

---

## Under the Hood

The memory engine isn't a simple vector database. It has three layers that work together:

<details>
<summary><strong>🔍 Retrieval — Three modes for different moments</strong></summary>

| Mode | Results | Graph | When |
|------|---------|-------|------|
| **Deep** | ~20 | Full propagation (α=0.3) | Session start, big picture |
| **Quick** | ~6 | Light propagation (α=0.15) | Mid-task lookups |
| **Recent** | ~15 | Time-weighted | WIP context, session resume |

The retrieval pipeline: cosine similarity → graph propagation (PageRank-style) → knapsack selection (optimize relevance per token).

</details>

<details>
<summary><strong>🕸️ Graph — Memories are connected, not flat</strong></summary>

Every memory can relate to others through typed edges:

| Edge | Direction | Effect in retrieval |
|------|-----------|-------------------|
| `relates_to` | bidirectional | mutual boost |
| `depends_on` | A → B | A boosts B |
| `caused_by` | A → B | A boosts B |
| `co_occurs` | bidirectional | mutual boost |
| `contradicts` | bidirectional | **suppresses** the weaker one |
| `supersedes` | A → B | **suppresses** the old version |

This means: when a decision is updated, the old version doesn't just sit there confusing Claude — it gets automatically suppressed.

</details>

<details>
<summary><strong>⏳ Decay — Not all memories age equally</strong></summary>

| Type | Decay rate | Example |
|------|-----------|---------|
| **Episodic** | Fast (0.01/day) | "Bug X happened on Tuesday" |
| **Semantic** | Slow (0.002/day) | "This module uses the strategy pattern" |
| **Procedural** | Very slow (0.001/day) | "Always use cents, never euros" |

Bug reports fade. Architecture decisions persist. Conventions stick around forever.

</details>

<details>
<summary><strong>🧩 MCP Tools (14 available)</strong></summary>

| Tool | Description |
|------|-------------|
| `remember` | Retrieve memories (deep/quick/recent) |
| `memorize` | Save new memories with embeddings |
| `update_memory` | Modify content, tags, deprecate |
| `extract_session` | Parse Claude Code chat JSONL |
| `prepare_elaboration` | Build working set for elaboration |
| `apply_elaboration` | Apply elaboration updates |
| `sync_codebase` | Detect stale/orphan memories |
| `diagnose` | Health score + prescriptions |
| `setup_status` | Track initialization progress |
| `stats` | System statistics |
| `list_memories` | Search/filter with pagination |
| `reinforce` | Boost edge weights |
| `decay` | Apply temporal decay |
| `init_project` | Bootstrap project metadata |

</details>

---

## Dashboard

A visual control center with 6 pages:

| Page | Purpose |
|------|---------|
| **Overview** | Health score, memory growth timeline, setup status, alerts |
| **Setup** | Step-by-step initialization wizard with progress tracking |
| **Memories** | Browse, search, filter, inspect individual memories |
| **Graph** | Force-directed visualization of the memory network |
| **Monitoring** | Health breakdown, prescriptions, elaboration history |
| **Guide** | Complete in-app documentation |

---

## Quick Start

### Requirements

- **Python** 3.11+ and **Node.js** 18+
- **Claude Code** (Anthropic CLI)

### Step 1 — Install

Open Claude Code **inside your project** and paste this prompt:

```
Install MangoBrain for this project.

1. Clone the repo:
   git clone https://github.com/Federico-Anastasi/mangobrain.git .mangobrain

2. Create a Python venv inside .mangobrain/.venv and install dependencies:
   pip install -e .  (from the .mangobrain directory)

3. Build the dashboard:
   cd .mangobrain/dashboard && npm install && npm run build

4. Run the init command using the venv's mango-brain binary:
   mango-brain init --project {USE_THIS_PROJECT_FOLDER_NAME} --path {ABSOLUTE_PATH_TO_THIS_PROJECT}

5. Add a "mango-brain" entry to .mcp.json at the project root:
   - command: path to the python binary inside .mangobrain/.venv
   - args: ["-m", "server"]
   - cwd: ".mangobrain"
   (Detect the OS and use the correct venv path: Scripts/python.exe on Windows, bin/python on Unix)

6. Add .mangobrain/ to .gitignore

7. When everything is done, tell me to CLOSE AND REOPEN Claude Code to load the
   MangoBrain MCP server. After reopening, I should run /init to start memory
   initialization.
```

Claude handles everything — just approve the commands when prompted.

### Step 2 — Restart Claude Code

After Step 1 completes, Claude will tell you to restart. **Close and reopen Claude Code** in your project. This loads the MangoBrain MCP server.

### Step 3 — Initialize Memory

In the new session, run:

```
/init
```

The `/init` wizard guides you through **14 steps across 5 phases**:

| Phase | What it does | Sessions |
|-------|-------------|----------|
| **1. Doc Base** | Extracts memories from CLAUDE.md, rules, and documentation | 1 |
| **2. Code Base** | Parallel agents scan the codebase for patterns and architecture | 1-2 |
| **3. Event Base** | Imports existing knowledge (task lists, project docs) — optional | 1 |
| **4. Chat Base** | Extracts knowledge from past Claude Code sessions (JSONL) | 1-3 |
| **5. Elaborate** | Builds the memory graph: edges, contradictions, abstractions | 1-2 |

> **Note:** Each phase runs in a separate Claude Code session (for fresh context). The wizard tells you exactly when to restart and what to do next. Progress is tracked automatically — if you stop mid-way, `/init` picks up where you left off.

After initialization, your daily workflow is simply: `/discuss` → `/task` → repeat.

### Step 4 — Dashboard (optional but recommended)

Open a separate terminal:

```bash
# Windows
.mangobrain\.venv\Scripts\mango-brain serve --api

# Unix
.mangobrain/.venv/bin/mango-brain serve --api
```

Dashboard opens at **http://localhost:3101** — monitor health, browse memories, track setup progress, and view the memory graph.

---

## Configuration

```toml
# mangobrain.toml

[embedding]
model = "auto"          # GPU → bge-large (1024d), CPU → bge-base (768d)
device = "auto"         # auto-detects CUDA

[retrieval]
deep_threshold = 0.78
quick_threshold = 0.85

[decay]
episodic = 0.01         # fast
semantic = 0.002        # medium
procedural = 0.001      # slow
```

## CLI

```bash
mango-brain serve              # MCP server (stdio)
mango-brain serve --api        # API + dashboard
mango-brain serve --all        # Both

mango-brain init -p NAME --path PATH   # Initialize project
mango-brain install --path PATH        # Install skills/agents/rules
mango-brain status -p NAME             # Setup progress
mango-brain doctor                     # System health check
mango-brain dashboard                  # Open dashboard in browser
```

## Requirements

- **Python** 3.11+
- **PyTorch** 2.2+ (GPU optional — CPU works fine)
- **Node.js** 18+ (for dashboard build)

## Project Structure

```
mangobrain/
├── server/           # Python MCP server + REST API
├── dashboard/        # React 19 + Vite + Tailwind
├── skills/           # 7 skills (/discuss, /task, /init, /memorize, /elaborate, /health-check, /smoke-test)
├── agents/           # 4 agent prompts (analyzer, executor, verifier, mem-manager)
├── rules/            # 2 auto-loaded rules (query strategy, workflow integration)
├── prompts/          # Init phase instructions + memory quality reference
├── tests/            # Test suite
├── mangobrain.toml   # Configuration
└── pyproject.toml    # Python package
```

---

<p align="center">
  <strong>Built by <a href="https://github.com/Federico-Anastasi">Mango</a></strong>
  <br/>
  <sub>Because your AI pair-programmer shouldn't have amnesia.</sub>
</p>
