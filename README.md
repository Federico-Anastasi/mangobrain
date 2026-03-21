<p align="center">
  <img src="assets/logo.svg" alt="MangoBrain" width="80" />
</p>

<h1 align="center">MangoBrain</h1>

<p align="center">
  <strong>The learning layer for Claude Code</strong>
</p>

<p align="center">
  <em>Persistent memory that builds itself as you work. Zero manual effort.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/MCP-compatible-8A2BE2?style=flat-square" />
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" />
</p>

---

**Session 1:** You tell Claude that prices must be stored in cents, not euros.
**Session 47:** Claude is about to write price logic. MangoBrain surfaces the memory automatically. Claude already knows.

**Session 3:** A timezone bug costs you 2 hours.
**Session 28:** Claude touches date logic. The verifier recalls the gotcha. The bug doesn't happen again.

**No manual saving. No tagging. No "remember this".** The mem-manager captures knowledge at session close. The analyzer and verifier recall it when it matters. You just work.

---

## Quick Start

```bash
pip install mango-brain           # lightweight (~50MB, no PyTorch yet)
cd /your/project
mangobrain install                # detects GPU, installs PyTorch, configures Claude Code
mangobrain serve --api            # start server + dashboard
# restart Claude Code, then run /brain-init
```

<details>
<summary>Or let Claude do everything</summary>

Open Claude Code in your project and paste:

```
Install MangoBrain for this project.
IMPORTANT: Use Python 3.11 or higher. Check available versions first (python --version,
py -3.12 --version, python3.12 --version, etc.) and use the correct one for pip install.
Run: pip install mango-brain  (using Python >= 3.11's pip)
Then run: mangobrain install
Then run: mangobrain serve --api (in background)
Then tell me to open http://localhost:3101 and to restart Claude Code.
After restart, I should run /brain-init.
```

</details>

---

## How It Works

```
/discuss ──→ /task ──→ knowledge saved automatically ──→ next session starts smarter
```

| Step | What happens | Memory role |
|------|-------------|------------|
| **`/discuss`** | Plan a feature. Claude recalls past decisions, patterns, gotchas. | Analyzer queries memory during exploration |
| **`/task`** | 4 agents execute: analyzer, executor, verifier, mem-manager. | Verifier checks for known issues before shipping |
| **close** | mem-manager runs automatically at session end. | Captures decisions, bugs, patterns — zero effort |
| **next session** | `/discuss` or `/task` starts with full context. | Memory surfaces relevant knowledge automatically |

This is the closed loop: **work → capture → recall → better work**.

---

## What Makes It Different

|  | Memory Stores | Workflow Tools | **MangoBrain** |
|--|---------------|----------------|----------------|
|  | *Mem0, MCP Memory* | *Ruflo, Claude Pilot* |  |
| Remembers across sessions | ✅ | — | ✅ |
| Structured agent workflow | — | ✅ | ✅ |
| **Auto-captures knowledge** | — | — | ✅ |
| **Memory informs execution** | — | — | ✅ |
| Graph relationships | — | — | ✅ typed edges |
| Temporal decay | — | — | ✅ per memory type |
| Contradicts & supersedes | — | — | ✅ auto-suppressed |
| Health monitoring | — | — | ✅ dashboard + alerts |

> Other tools give you storage or structure. MangoBrain gives you both — and the memory builds itself.

---

## Dashboard

A 7-page visual control center. Health score, memory browser, graph visualization, query interface, monitoring.

<p align="center">
  <img src="assets/dashboard-overview.png" alt="Dashboard Overview" width="800" />
</p>

---

## The Workflow in Detail

### `/discuss` — Plan with memory

Describe what you want to build. Claude recalls past decisions, known bugs, architectural patterns. Analyzer agents explore the codebase *and* query memory for gotchas. Output: a `task.md` ready for execution.

### `/task` — Execute with agents

4 specialized agents with strict roles:

| Agent | Role | Memory access |
|-------|------|---------------|
| **Analyzer** | Explores code, finds patterns and risks | ✅ reads memory |
| **Executor** | Writes code — 100% focused on implementation | ❌ no memory (receives context from Main) |
| **Verifier** | QA: build, tests, lint, known issues | ✅ reads memory |
| **Mem-manager** | Saves knowledge at session close | ✅ full memory access |

### `/memorize` — Manual save

For sessions outside the discuss→task cycle. Spawns the mem-manager to capture what happened.

### Maintenance

| Skill | When | What it does |
|-------|------|-------------|
| `/elaborate` | Weekly | Consolidates: graph edges, contradictions, abstractions |
| `/health-check` | Monthly | Diagnoses gaps, runs targeted fixes |
| `/smoke-test` | After changes | Tests retrieval quality with diverse queries |

---

## Installation Details

### What `mangobrain install` does

1. **Detects hardware** — finds your GPU (NVIDIA CUDA) or defaults to CPU
2. **Installs embedding engine** — PyTorch + sentence-transformers, optimized for your hardware
   - GPU detected → asks CUDA (~2GB) or CPU (~200MB)
   - No GPU → installs CPU automatically
   - Already installed → skips
3. **Installs skills & rules** — copies 7 skills, 4 agents, 2 rules into `.claude/`
4. **Configures MCP** — creates `.mcp.json` for Claude Code
5. **Updates CLAUDE.md** — adds MangoBrain documentation

### Memory initialization

`/brain-init` guides you through **14 steps across 7 phases**:

| Phase | What it does | Sessions |
|-------|-------------|----------|
| Doc Base | Extract from CLAUDE.md, rules, documentation | 1 |
| Code Base | Parallel agents scan codebase for patterns | 1-2 |
| Event Base | Import existing knowledge (optional) | 1 |
| Chat Base | Extract from past Claude Code sessions | 1-3 |
| Elaborate | Build graph: edges, contradictions, abstractions | 1-2 |
| Smoke Test | Verify retrieval quality | 1 |
| Health Check | Diagnose gaps, validate final state | 1 |

Progress is tracked automatically. If you stop mid-way, `/brain-init` picks up where you left off.

---

<details>
<summary><strong>Under the Hood</strong></summary>

### Retrieval

| Mode | Results | When |
|------|---------|------|
| **Deep** | ~20, full graph propagation | Session start, big picture |
| **Quick** | ~6, light propagation | Mid-task targeted lookups |
| **Recent** | ~15, time-weighted | WIP context, session resume |

Pipeline: cosine similarity (BGE embeddings) → graph propagation (PageRank-style) → knapsack selection (optimize relevance per token).

### Graph

Typed edges: `relates_to`, `depends_on`, `caused_by`, `co_occurs`, `contradicts`, `supersedes`. When a decision is updated, the old version gets automatically suppressed.

### Decay

| Type | Rate | Example |
|------|------|---------|
| Episodic | 0.01/day | "Bug X happened Tuesday" — fades fast |
| Semantic | 0.002/day | "This module uses strategy pattern" — persists |
| Procedural | 0.001/day | "Always use cents, never euros" — sticks forever |

### Storage

Single SQLite database at `~/.mangobrain/mangobrain.db`. Override with `MANGOBRAIN_DB` env var.

### MCP Tools (15)

remember, memorize, update_memory, extract_session, init_project, read_project_memory, prepare_elaboration, apply_elaboration, reinforce, decay, stats, diagnose, list_memories, sync_codebase, setup_status

</details>

---

## Configuration

```toml
# mangobrain.toml (optional — defaults work for most setups)

[database]
path = "~/.mangobrain/mangobrain.db"

[embedding]
model = "auto"    # GPU → bge-large (1024d), CPU → bge-base (768d)
device = "auto"   # auto-detects CUDA

[decay]
episodic = 0.01
semantic = 0.002
procedural = 0.001
```

## CLI

```bash
mangobrain serve              # MCP server (stdio)
mangobrain serve --api        # API + dashboard
mangobrain serve --all        # Both
mangobrain install            # Full interactive setup
mangobrain init -p NAME       # Initialize project
mangobrain status -p NAME     # Setup progress
mangobrain doctor             # System health check
mangobrain dashboard          # Open dashboard
```

## Requirements

- **Python** 3.11+
- **Claude Code** (Anthropic CLI)
- **GPU** optional — works on CPU (slower, slightly lower quality embeddings)

---

<p align="center">
  <strong>Built by <a href="https://github.com/Federico-Anastasi">Federico Anastasi</a></strong>
  <br/>
  <sub>Because your AI pair-programmer shouldn't have amnesia.</sub>
</p>
