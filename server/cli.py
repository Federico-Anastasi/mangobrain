"""MangoBrain — CLI entry points."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

from server.config import PROJECT_ROOT, API_PORT, DB_PATH, EMBEDDING_MODEL, EMBEDDING_DEVICE

logger = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────

SKILLS_SRC = PROJECT_ROOT / "skills"
AGENTS_SRC = PROJECT_ROOT / "agents"
RULES_SRC = PROJECT_ROOT / "rules"


# ── Commands ──────────────────────────────────────────────────────────────────

def cmd_serve(args: argparse.Namespace) -> None:
    """Start the MangoBrain server."""
    from server.main import main as server_main

    if args.api:
        sys.argv = ["server", "api"]
    elif args.all:
        sys.argv = ["server", "all"]
    else:
        sys.argv = ["server"]
    server_main()


def cmd_init(args: argparse.Namespace) -> None:
    """Initialize a project for MangoBrain."""
    project = args.project
    project_path = Path(args.path).resolve() if args.path else None

    if not project:
        print("Error: --project is required")
        sys.exit(1)

    if project_path and not project_path.exists():
        print(f"Error: path does not exist: {project_path}")
        sys.exit(1)

    async def _init():
        from server.database import Database
        db = await Database.create(DB_PATH)

        # Check if already initialized
        summary = await db.get_setup_summary(project)
        if summary.get("initialized"):
            print(f"Project '{project}' already initialized ({summary['completed']}/{summary['total_steps']} steps completed)")
            print(f"Progress: {summary['progress_pct']}%")
            if summary.get("current_step"):
                print(f"Next step: {summary['current_step']['title']}")
            return

        # Create setup progress entries
        count = await db.init_setup_progress(project)
        print(f"Project '{project}' initialized with {count} setup steps.")

        # Auto-install skills/rules if path provided
        if project_path:
            installed = _install_files(project_path)
            if installed:
                from datetime import datetime
                await db.update_setup_step(project, "install", "skills_rules", {
                    "status": "completed",
                    "started_at": datetime.utcnow(),
                    "completed_at": datetime.utcnow(),
                    "result": json.dumps({"files_installed": installed}),
                })
                print(f"Installed {len(installed)} files into {project_path / '.claude'}")

            # Update CLAUDE.md
            _patch_claude_md(project_path, project)

        print(f"\nOpen the dashboard to track progress: http://localhost:{API_PORT}")
        print(f"In a Claude Code session in {project_path or 'the project'}, run: /init")

        await db.close()

    asyncio.run(_init())


def cmd_install(args: argparse.Namespace) -> None:
    """Install MangoBrain skills/agents/rules into a project."""
    project_path = Path(args.path).resolve()

    if not project_path.exists():
        print(f"Error: path does not exist: {project_path}")
        sys.exit(1)

    installed = _install_files(project_path)
    print(f"Installed {len(installed)} files:")
    for f in installed:
        print(f"  {f}")

    if args.patch_claude_md:
        _patch_claude_md(project_path, args.project or project_path.name)
        print("Updated CLAUDE.md with MangoBrain section")


def cmd_doctor(args: argparse.Namespace) -> None:
    """Check MangoBrain health."""
    print("MangoBrain Doctor")
    print("=" * 50)

    # Check config
    print(f"\n[Config]")
    print(f"  Database: {DB_PATH}")
    print(f"  DB exists: {DB_PATH.exists()}")
    print(f"  Embedding model: {EMBEDDING_MODEL}")
    print(f"  Device: {EMBEDDING_DEVICE}")
    print(f"  API port: {API_PORT}")

    # Check DB
    if DB_PATH.exists():
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.execute("SELECT COUNT(*) FROM memories WHERE is_deprecated=0")
        mem_count = cur.fetchone()[0]
        cur = conn.execute("SELECT COUNT(*) FROM edges")
        edge_count = cur.fetchone()[0]
        cur = conn.execute("SELECT DISTINCT project FROM memories WHERE project IS NOT NULL")
        projects = [r[0] for r in cur.fetchall()]
        conn.close()

        print(f"\n[Database]")
        print(f"  Memories: {mem_count}")
        print(f"  Edges: {edge_count}")
        print(f"  Projects: {', '.join(projects) if projects else 'none'}")

        # Check setup progress per project
        conn = sqlite3.connect(str(DB_PATH))
        for proj in projects:
            cur = conn.execute(
                "SELECT COUNT(*), SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) "
                "FROM setup_progress WHERE project=?", (proj,)
            )
            row = cur.fetchone()
            if row and row[0] > 0:
                print(f"\n[Setup: {proj}]")
                print(f"  Progress: {row[1] or 0}/{row[0]} steps completed")
        conn.close()
    else:
        print(f"\n[Database] Not found — will be created on first run")

    # Check embedding model
    print(f"\n[Embedding]")
    try:
        import torch
        print(f"  PyTorch: {torch.__version__}")
        print(f"  CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"  GPU: {torch.cuda.get_device_name(0)}")
    except ImportError:
        print("  PyTorch: not installed")

    # Check MCP
    print(f"\n[MCP Server]")
    try:
        import mcp
        print(f"  MCP library: installed")
    except ImportError:
        print(f"  MCP library: NOT installed")

    print(f"\nAll checks complete.")


def cmd_dashboard(args: argparse.Namespace) -> None:
    """Open the dashboard in the browser."""
    url = f"http://localhost:{API_PORT}"
    print(f"Opening dashboard at {url}")
    print("(Make sure the API server is running: mango-brain serve --api)")
    webbrowser.open(url)


def cmd_status(args: argparse.Namespace) -> None:
    """Show setup status for a project."""
    project = args.project

    async def _status():
        from server.database import Database
        db = await Database.create(DB_PATH)

        if project:
            steps = await db.get_setup_progress(project)
            if not steps:
                print(f"Project '{project}' not initialized. Run: mango-brain init --project {project}")
                return
            print(f"Setup progress for '{project}':")
            print("-" * 60)
            for s in steps:
                icon = {"pending": " ", "in_progress": "~", "completed": "+", "skipped": "-", "failed": "!"}
                print(f"  [{icon.get(s.status.value, '?')}] {s.order_index:2d}. {s.title} ({s.status.value})")
            summary = await db.get_setup_summary(project)
            print(f"\nProgress: {summary['progress_pct']}% ({summary['completed']}/{summary['total_steps']})")
        else:
            summaries = await db.get_all_projects_setup()
            if not summaries:
                print("No projects initialized yet.")
                return
            for s in summaries:
                status = "READY" if s["is_ready"] else f"{s['progress_pct']}%"
                print(f"  {s['project']}: {status} ({s['completed']}/{s['total_steps']} steps)")

        await db.close()

    asyncio.run(_status())


# ── Helpers ───────────────────────────────────────────────────────────────────

def _install_files(project_path: Path) -> list[str]:
    """Copy skills/agents/rules into a project's .claude/ directory."""
    installed = []
    claude_dir = project_path / ".claude"

    # Skills
    if SKILLS_SRC.exists():
        for skill_dir in SKILLS_SRC.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                dest = claude_dir / "skills" / skill_dir.name / "SKILL.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_dir / "SKILL.md", dest)
                installed.append(f"skills/{skill_dir.name}/SKILL.md")

    # Agents
    if AGENTS_SRC.exists():
        for agent_file in AGENTS_SRC.glob("*.md"):
            dest = claude_dir / "agents" / agent_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_file, dest)
            installed.append(f"agents/{agent_file.name}")

    # Rules
    if RULES_SRC.exists():
        for rule_file in RULES_SRC.glob("*.md"):
            dest = claude_dir / "rules" / rule_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rule_file, dest)
            installed.append(f"rules/{rule_file.name}")

    return installed


def _patch_claude_md(project_path: Path, project_name: str) -> None:
    """Add MangoBrain section to project's CLAUDE.md if not already present."""
    claude_md = project_path / "CLAUDE.md"
    marker = "## MangoBrain"

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if marker in content:
            return  # Already patched
    else:
        content = f"# {project_name}\n\n"

    section = f"""
{marker} — Persistent Memory

MangoBrain provides persistent, associative memory and a complete development workflow.

### Workflow Skills
- `/discuss` — Brainstorm + memory-enhanced planning (INTAKE -> EXPLORE -> BRAINSTORM -> DOCUMENT)
- `/task` — Task execution with memory (INTAKE -> ANALYZE -> PLAN -> EXECUTE -> VERIFY -> CLOSE)
- `/memorize` — End-of-session memory sync for free sessions
- `/init` — First-time memory initialization (guided setup)
- `/elaborate` — Periodic memory consolidation
- `/health-check` — Memory health diagnosis and optimization
- `/smoke-test` — Query verification

### Agents (spawned by skills, not invoked directly)
- **analyzer** — Code exploration + memory recall (Read, Grep, Glob, remember)
- **executor** — Implementation (Read, Edit, Write, Bash) — NO memory, 100% code focus
- **verifier** — QA/build verification + memory recall (Bash, Read, remember)
- **mem-manager** — Memory management at session close (memorize, sync, WIP tracking)

### Rules (auto-loaded)
- `mangobrain-remember.md` — How to query memory effectively
- `mangobrain-workflow.md` — When and how to use memory in the workflow

### MCP Tools
remember, memorize, update_memory, extract_session, init_project, prepare_elaboration,
apply_elaboration, reinforce, decay, stats, diagnose, list_memories, sync_codebase, setup_status
"""

    claude_md.write_text(content + section, encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="mango-brain",
        description="MangoBrain — Persistent memory + workflow system for Claude Code",
    )
    sub = parser.add_subparsers(dest="command")

    # serve
    p_serve = sub.add_parser("serve", help="Start the MangoBrain server")
    p_serve.add_argument("--api", action="store_true", help="Run API server only (for dashboard)")
    p_serve.add_argument("--all", action="store_true", help="Run both MCP (stdio) and API server")
    p_serve.set_defaults(func=cmd_serve)

    # init
    p_init = sub.add_parser("init", help="Initialize a project for MangoBrain")
    p_init.add_argument("--project", "-p", required=True, help="Project name")
    p_init.add_argument("--path", help="Path to the project directory")
    p_init.set_defaults(func=cmd_init)

    # install
    p_install = sub.add_parser("install", help="Install skills/agents/rules into a project")
    p_install.add_argument("--path", required=True, help="Path to the project directory")
    p_install.add_argument("--project", help="Project name (for CLAUDE.md patch)")
    p_install.add_argument("--patch-claude-md", action="store_true", help="Also patch CLAUDE.md")
    p_install.set_defaults(func=cmd_install)

    # doctor
    p_doctor = sub.add_parser("doctor", help="Check MangoBrain system health")
    p_doctor.set_defaults(func=cmd_doctor)

    # dashboard
    p_dash = sub.add_parser("dashboard", help="Open the dashboard in the browser")
    p_dash.set_defaults(func=cmd_dashboard)

    # status
    p_status = sub.add_parser("status", help="Show setup progress")
    p_status.add_argument("--project", "-p", help="Project name (omit for all)")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)

    args.func(args)
