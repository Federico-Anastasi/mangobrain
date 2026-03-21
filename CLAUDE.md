# MangoBrain

Persistent associative memory system + complete development workflow for Claude Code.

## Role
You are a technical agent working on MangoBrain. You develop the memory engine (Python server), dashboard (React), skills, agents, and prompts.

## Structure
```
mangobrain/
├── server/           # Python MCP server + REST API
│   ├── config.py     # TOML + .env config loader
│   ├── database.py   # Async SQLite (WAL mode)
│   ├── embeddings.py # BGE models, auto-detect GPU/CPU
│   ├── retrieval.py  # Cosine similarity + graph propagation + knapsack
│   ├── graph.py      # Typed adjacency matrix, PageRank-style propagation
│   ├── decay.py      # Exponential decay by memory type
│   ├── mcp_tools.py  # 15 MCP tools
│   ├── api_routes.py # REST endpoints for dashboard
│   ├── cli.py        # CLI commands (serve, init, install, doctor, status, dashboard)
│   ├── main.py       # Entry point (MCP stdio / API / both)
│   ├── skills/       # Claude Code skills (installed into target projects)
│   │   ├── discuss/      # Brainstorm + memory-enhanced planning
│   │   ├── task/         # Task execution with agents + memory
│   │   ├── brain-init/   # Guided memory initialization (14 step)
│   │   ├── memorize/     # End-of-session sync
│   │   ├── elaborate/    # Memory consolidation
│   │   ├── health-check/ # Diagnosis + optimization
│   │   └── smoke-test/   # Query verification
│   ├── agents/       # Agent prompts (spawned by skills)
│   │   ├── analyzer.md   # Code exploration + remember
│   │   ├── executor.md   # Implementation (no memory, 100% code)
│   │   ├── verifier.md   # QA + remember for known issues
│   │   └── mem-manager.md # Memory management at session close
│   ├── rules/        # Auto-loaded rules (installed into target projects)
│   └── prompts/      # Reference material for init phases
├── dashboard/        # React 19 + Vite + Tailwind
│   └── src/pages/    # Overview, Setup, Remember, Memories, Graph, Monitoring, Guide
├── tests/            # Test suite
├── mangobrain.toml   # Configuration
└── pyproject.toml    # Python package
```

## MCP Tools
remember, memorize, update_memory, extract_session, init_project, read_project_memory,
prepare_elaboration, apply_elaboration, reinforce, decay, stats, diagnose,
list_memories, sync_codebase, setup_status

## Development
- **Python**: 3.12+. Use `python` (not `python3` on Windows).
- **Venv**: `.venv/Scripts/python.exe` (Windows) or `.venv/bin/python` (Unix)
- **Dashboard dev**: `cd dashboard && npm run dev` (port 3102)
- **API server**: `mangobrain serve --api` (port 3101)
- **Tests**: `python -m pytest tests/ -v`
- **Build dashboard**: `cd dashboard && npm run build`
- Set `PYTHONIOENCODING=utf-8` for Windows Unicode compatibility.

## Language
English for code, comments, memories, and documentation.
