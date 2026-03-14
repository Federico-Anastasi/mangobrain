<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/react-19-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/MCP-compatible-8A2BE2?style=for-the-badge" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" />
</p>

<h1 align="center">🧠 MangoBrain</h1>

<p align="center">
  <strong>Persistent associative memory + complete development workflow for Claude Code</strong>
</p>

<p align="center">
  <em>Claude forgets everything between sessions. MangoBrain fixes that.</em>
</p>

---

## The Problem

Every time you start a new Claude Code session, you lose context. Architecture decisions, bug patterns, code conventions, past mistakes — all gone. You end up re-explaining the same things, hitting the same bugs, making the same decisions.

## The Solution

MangoBrain gives Claude **long-term memory** that persists across sessions. It remembers what matters and retrieves it when relevant — automatically.

It also provides a **complete development workflow** (plan → execute → verify → remember) that naturally captures knowledge as you work.

```
Session 1: "Prices must be stored in cents, never euros"
    ↓ saved to memory
Session 47: *Claude is about to write price logic*
    ↓ memory surfaces automatically
Claude: "I see from past sessions that prices are stored in cents..."
```

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🔍 Smart Retrieval
Three modes tuned for different moments:
- **Deep** (~20 results) — session start, full context
- **Quick** (~6 results) — mid-task lookups
- **Recent** (~15 results) — WIP and temporal context

</td>
<td width="50%">

### 🕸️ Graph Memory
Memories aren't flat — they're connected:
- `depends_on`, `caused_by` — directional
- `contradicts` — suppresses outdated info
- `supersedes` — version chains
- PageRank-style propagation

</td>
</tr>
<tr>
<td>

### ⏳ Temporal Decay
Not all memories age equally:
- **Episodic** (bugs, events) → decay fast
- **Semantic** (architecture, patterns) → decay slow
- **Procedural** (conventions, how-to) → persist

</td>
<td>

### 🤖 Agent Workflow
Specialized agents for each job:
- **analyzer** — explores code + recalls memory
- **executor** — writes code (100% focus, no memory)
- **verifier** — QA + checks known issues
- **mem-manager** — saves knowledge at session close

</td>
</tr>
</table>

### 📊 Dashboard

Visual monitoring with 6 pages:

| Page | What it shows |
|------|---------------|
| **Overview** | Health score, growth timeline, setup status |
| **Setup** | Step-by-step initialization wizard |
| **Memories** | Search, filter, inspect individual memories |
| **Graph** | Force-directed memory graph visualization |
| **Monitoring** | Health breakdown, prescriptions, elaboration logs |
| **Guide** | Complete in-app documentation |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/Federico-Anastasi/mangobrain.git
cd mangobrain

python -m venv .venv
# Windows:
.venv\Scripts\activate
# Unix:
source .venv/bin/activate

pip install -e .
```

### 2. Build Dashboard

```bash
cd dashboard && npm install && npm run build && cd ..
```

### 3. Initialize Your Project

```bash
mango-brain init --project myproject --path /path/to/your/project
```

### 4. Configure Claude Code

Add to your project's `.mcp.json`:

```json
{
  "mcpServers": {
    "mango-brain": {
      "command": "python",
      "args": ["-m", "server"],
      "cwd": "/path/to/mangobrain"
    }
  }
}
```

### 5. Start Using

```bash
# Start API + Dashboard
mango-brain serve --api
# → http://localhost:3101
```

Then in Claude Code, run `/init` to begin the guided setup.

---

## 🔧 Daily Workflow

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│  /discuss    │────▶│   /task      │────▶│  /memorize   │
│  Plan with   │     │  Execute     │     │  Save what   │
│  memory      │     │  with agents │     │  you learned │
└─────────────┘     └─────────────┘     └──────────────┘
       │                    │                    │
       ▼                    ▼                    ▼
  remember()           analyzer()          mem-manager()
  past decisions       code + memory       memorize + sync
```

### Skills

| Skill | Purpose |
|-------|---------|
| `/discuss` | Brainstorm + plan with memory context → produces `task.md` |
| `/task` | Full execution cycle: analyze → plan → execute → verify → close |
| `/memorize` | End-of-session sync for free sessions |
| `/init` | Guided memory initialization (14 steps) |
| `/elaborate` | Periodic consolidation — build graph, find contradictions |
| `/health-check` | Diagnose + optimize memory health |
| `/smoke-test` | Test retrieval quality with diverse queries |

### Maintenance Schedule

| Task | Frequency | Skill |
|------|-----------|-------|
| Elaborate | Weekly | `/elaborate` |
| Health check | Monthly | `/health-check` |
| Smoke test | After major changes | `/smoke-test` |

---

## ⚙️ Configuration

Edit `mangobrain.toml`:

```toml
[embedding]
model = "auto"        # GPU → bge-large (1024d), CPU → bge-base (768d)
device = "auto"       # auto-detects CUDA

[retrieval]
deep_threshold = 0.78
quick_threshold = 0.85

[decay]
episodic = 0.01       # fast
semantic = 0.002      # medium
procedural = 0.001    # slow
```

---

## 🛠️ CLI Reference

```bash
mango-brain serve              # MCP server (stdio)
mango-brain serve --api        # API + dashboard
mango-brain serve --all        # Both

mango-brain init -p NAME --path PATH   # Initialize project
mango-brain install --path PATH        # Install skills/agents/rules
mango-brain status -p NAME             # Setup progress
mango-brain doctor                     # System health
mango-brain dashboard                  # Open in browser
```

---

## 🧩 MCP Tools

<details>
<summary><strong>14 tools available</strong> (click to expand)</summary>

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

## 📁 Project Structure

```
mangobrain/
├── server/           # Python MCP server + REST API
├── dashboard/        # React 19 + Vite + Tailwind
├── skills/           # 7 Claude Code skills
├── agents/           # 4 specialized agent prompts
├── rules/            # 2 auto-loaded rules
├── prompts/          # Init phase instructions + quality reference
├── tests/            # Test suite
├── mangobrain.toml   # Configuration
├── pyproject.toml    # Python package
└── CLAUDE.md         # Self-knowledge for Claude Code
```

---

## Requirements

- **Python** ≥ 3.11
- **PyTorch** ≥ 2.2 (GPU optional — CPU works fine)
- **Node.js** ≥ 18 (for dashboard)

---

<p align="center">
  <strong>Built by <a href="https://github.com/Federico-Anastasi">Mango</a></strong>
  <br/>
  <sub>Because Claude deserves a brain that doesn't reset every session.</sub>
</p>
