# MangoBrain

**Persistent associative memory + complete development workflow for Claude Code.**

MangoBrain gives Claude long-term memory across sessions. It remembers architecture decisions, bug patterns, code conventions, and project knowledge — so every conversation starts with real context instead of a blank slate.

It also provides a structured development workflow (discuss, task, specialized agents) that integrates memory naturally into how you build software.

## What It Does

- **Remembers** decisions, patterns, bugs, and architecture across Claude Code sessions
- **Retrieves** relevant memories using semantic search + graph propagation
- **Forgets gracefully** — episodic memories decay fast, procedural knowledge stays
- **Provides a workflow** — /discuss to plan, /task to execute, agents to specialize
- **Dashboard** — visual monitoring, setup wizard, graph explorer

## Quick Start

### 1. Clone & Install

```bash
# Clone into your project (or anywhere you like)
git clone https://github.com/user/mango-brain.git
cd mango-brain

# Create virtual environment
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate

# Install
pip install -e .
```

### 2. Build the Dashboard

```bash
cd dashboard
npm install
npm run build
cd ..
```

### 3. Initialize Your Project

```bash
mango-brain init --project myproject --path /path/to/your/project
```

This will:
- Create 14 setup steps in the database
- Copy skills, agents, and rules into your project's `.claude/` directory
- Patch your project's `CLAUDE.md` with MangoBrain instructions
- Tell you to open the dashboard

### 4. Start the Server

```bash
# API + Dashboard (for browser monitoring)
mango-brain serve --api

# MCP server only (for Claude Code integration)
mango-brain serve

# Both simultaneously
mango-brain serve --all
```

Dashboard: `http://localhost:3101` — go to the **Setup** tab to track initialization progress.

### 5. Configure Claude Code

Add MangoBrain to your Claude Code MCP config. In your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "mango-brain": {
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "/path/to/mango-brain"
    }
  }
}
```

### 6. Complete Setup

In a Claude Code session inside your project, run `/init`. The skill guides you through:

1. **Doc Base** — Extract memories from your documentation
2. **Code Base** — Parallel codebase scan with analyzer agents
3. **Event Base** — Import existing knowledge (optional)
4. **Chat Base** — Extract from chat history
5. **Elaborate** — Build graph connections

Each phase runs in a separate session. The dashboard tracks progress.

## How It Works

### Memory Engine

Memories are atomic units (2-5 lines each) stored with vector embeddings in a graph structure.

**Retrieval** combines three signals:
- **Cosine similarity** (BGE embeddings, 1024 dim on GPU / 768 dim on CPU)
- **Graph propagation** (PageRank-style, typed edges: depends_on, contradicts, supersedes...)
- **Temporal decay** (episodic fades fast, procedural stays)

Three retrieval modes:

| Mode | Results | When |
|------|---------|------|
| `deep` | ~20 | Session/task start — full graph propagation |
| `quick` | ~6 | Mid-task — lightweight, focused |
| `recent` | ~15 | WIP context — temporal + neighbors |

### Workflow

```
/discuss  →  Plan with memory context  →  task.md
     ↓
/task     →  Execute with agents       →  Code changes + new memories
     ↓
/memorize →  Save session knowledge    →  Persistent memory
```

### Agents

Skills spawn specialized agents:

| Agent | Role | Tools | Memory |
|-------|------|-------|--------|
| **analyzer** | Explore code, find patterns | Read, Grep, Glob | `remember(quick)` |
| **executor** | Write code | Read, Edit, Write, Bash | None — 100% code focus |
| **verifier** | QA, build checks | Bash, Read | `remember(quick)` |
| **mem-manager** | Save knowledge at session close | Read, MangoBrain tools | Full access |

### Dashboard

6 pages:
- **Overview** — Health score, stats, growth timeline, setup status
- **Setup** — Step-by-step initialization wizard with progress tracking
- **Memories** — Search, filter, inspect individual memories
- **Graph** — Force-directed visualization of the memory graph
- **Monitoring** — Health breakdown, prescriptions, elaboration logs
- **Guide** — Complete user documentation

## Configuration

Edit `mangobrain.toml`:

```toml
[server]
api_port = 3101

[embedding]
model = "auto"     # auto: GPU → bge-large (1024d), CPU → bge-base (768d)
device = "auto"    # auto-detects CUDA

[retrieval]
deep_threshold = 0.78
quick_threshold = 0.85
deep_budget = 8000      # tokens
quick_budget = 2000

[decay]
episodic = 0.01         # fast — events, bugs
semantic = 0.002        # medium — knowledge, patterns
procedural = 0.001      # slow — conventions, how-to
```

Environment variables override TOML (prefixed `MANGOBRAIN_`). Legacy `.env` format also supported.

## CLI Reference

```bash
mango-brain serve              # MCP server (stdio)
mango-brain serve --api        # API server + dashboard
mango-brain serve --all        # Both

mango-brain init -p NAME --path PATH   # Initialize project
mango-brain install --path PATH        # Install skills/agents/rules only
mango-brain status -p NAME             # Show setup progress
mango-brain status                     # All projects
mango-brain doctor                     # System health check
mango-brain dashboard                  # Open in browser
```

## Skills Reference

| Skill | Purpose |
|-------|---------|
| `/discuss` | Plan + brainstorm with memory. Spawns analyzers, produces task.md |
| `/task` | Execute tasks. Analyze → Plan → Execute → Verify → Close with mem-manager |
| `/init` | Guided memory initialization (14 steps across multiple sessions) |
| `/memorize` | End-of-session sync for free sessions |
| `/elaborate` | Periodic consolidation — build graph, find contradictions |
| `/health-check` | Diagnose memory health, prescribe fixes, verify improvement |
| `/smoke-test` | Test retrieval quality with diverse queries |

## MCP Tools

| Tool | Description |
|------|-------------|
| `remember` | Retrieve memories (deep/quick/recent modes) |
| `memorize` | Save new memories with embeddings and relations |
| `update_memory` | Modify content, tags, file_path, deprecate |
| `extract_session` | Parse Claude Code chat JSONL |
| `prepare_elaboration` | Build working set for elaboration cycle |
| `apply_elaboration` | Apply elaboration updates |
| `sync_codebase` | Detect stale/orphan memories vs. filesystem |
| `diagnose` | Health score + prescriptions + content gaps |
| `setup_status` | Track initialization progress |
| `stats` | System statistics and alerts |
| `list_memories` | Search/filter with pagination |
| `reinforce` | Boost co-occurrence edges |
| `decay` | Apply temporal decay |

## Maintenance

| Task | Frequency | Skill |
|------|-----------|-------|
| Elaborate | Weekly | `/elaborate` |
| Health check | Monthly | `/health-check` |
| Smoke test | After major changes | `/smoke-test` |
| Decay | Automatic via elaborate | `decay` tool |

## Requirements

- **Python** >= 3.11
- **PyTorch** >= 2.2 (GPU optional — CPU works, just slower embeddings)
- **Node.js** >= 18 (for dashboard)

GPU recommended but not required. On CPU, MangoBrain uses a smaller embedding model (bge-base, 768 dim) that works well for most projects.

## Project Structure

```
mango-brain/
├── server/              # Python MCP server + REST API
├── dashboard/           # React 19 + Vite + Tailwind dashboard
├── skills/              # 7 Claude Code skills
├── agents/              # 4 agent prompts
├── rules/               # 2 auto-loaded rules
├── prompts/             # Init phase instructions + memory quality reference
├── tests/               # Test suite
├── mangobrain.toml      # Configuration
├── pyproject.toml       # Python package definition
└── CLAUDE.md            # Project self-knowledge for Claude Code
```

## License

MIT
