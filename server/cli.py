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

from server.config import PACKAGE_DIR, API_PORT, DB_PATH, EMBEDDING_MODEL, EMBEDDING_DEVICE

logger = logging.getLogger(__name__)

# ── Paths (bundled inside the server package) ─────────────────────────────────

SKILLS_SRC = PACKAGE_DIR / "skills"
AGENTS_SRC = PACKAGE_DIR / "agents"
RULES_SRC = PACKAGE_DIR / "rules"
PROMPTS_SRC = PACKAGE_DIR / "prompts"

# Work paths
WORK_DIR = PACKAGE_DIR / "work"
WORK_SKILLS_SRC = WORK_DIR / "skills"
WORK_AGENTS_SRC = WORK_DIR / "agents"
WORK_RULES_SRC = WORK_DIR / "rules"
WORK_PROMPTS_SRC = WORK_DIR / "prompts"
WORK_TEMPLATES_SRC = WORK_DIR / "templates"


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
        print(f"In a Claude Code session in {project_path or 'the project'}, run: /brain-init")

        await db.close()

    asyncio.run(_init())


def cmd_install(args: argparse.Namespace) -> None:
    """Full interactive install: detect hardware, install torch, set up project."""
    project_path = Path(args.path).resolve() if args.path else Path.cwd()
    project_name = args.project or project_path.name

    if not project_path.exists():
        print(f"Error: path does not exist: {project_path}")
        sys.exit(1)

    print("=" * 60)
    print("  MangoBrain — Installation")
    print("=" * 60)

    # ── Step 1: Detect hardware ──
    print("\n[1/5] Detecting hardware...")
    has_gpu = False
    gpu_name = ""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            has_gpu = True
            gpu_name = result.stdout.strip().split("\n")[0]
            print(f"  GPU detected: {gpu_name}")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    if not has_gpu:
        print("  No NVIDIA GPU detected — will use CPU embeddings")

    # ── Step 2: Install embedding engine (torch + sentence-transformers) ──
    print("\n[2/5] Setting up embedding engine...")

    # Check torch
    torch_installed = False
    torch_has_cuda = False
    try:
        import torch
        torch_installed = True
        torch_has_cuda = torch.cuda.is_available()
        print(f"  PyTorch {torch.__version__} found ({'CUDA' if torch_has_cuda else 'CPU'})")
    except ImportError:
        print("  PyTorch not found")

    # Check sentence-transformers
    st_installed = False
    try:
        import sentence_transformers
        st_installed = True
        print(f"  sentence-transformers {sentence_transformers.__version__} found")
    except ImportError:
        print("  sentence-transformers not found")

    # Decide what to install
    needs_torch = False
    use_cuda = False

    if torch_installed and torch_has_cuda and has_gpu and st_installed:
        print("  Everything looks good — skipping.")
    elif torch_installed and not torch_has_cuda and has_gpu:
        # Has torch CPU but GPU available — ask
        print(f"\n  You have PyTorch (CPU-only) but a GPU is available: {gpu_name}")
        print("  Options:")
        print("    1. Reinstall with CUDA (recommended — faster, better quality)")
        print("       Downloads ~2GB, uses bge-large-en-v1.5 (1024d)")
        print("    2. Keep CPU version")
        print("       Uses bge-base-en-v1.5 (768d), ~200MB")
        choice = input("\n  Choice [1]: ").strip() or "1"
        if choice == "1":
            needs_torch = True
            use_cuda = True
        # else keep current torch, just ensure sentence-transformers
    elif not torch_installed:
        needs_torch = True
        if has_gpu:
            print(f"\n  GPU detected: {gpu_name}")
            print("  Options:")
            print("    1. Install with CUDA (recommended — faster, better quality)")
            print("       Downloads ~2GB, uses bge-large-en-v1.5 (1024d)")
            print("    2. Install CPU-only")
            print("       Downloads ~200MB, uses bge-base-en-v1.5 (768d)")
            choice = input("\n  Choice [1]: ").strip() or "1"
            use_cuda = choice == "1"
        else:
            use_cuda = False
            print("  No GPU — installing CPU-only setup...")

    if needs_torch:
        if use_cuda:
            print(f"\n  Installing PyTorch with CUDA support...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "torch",
                 "--index-url", "https://download.pytorch.org/whl/cu124",
                 "--force-reinstall"],
                check=True,
            )
            print("  PyTorch CUDA installed.")
        else:
            print("\n  Installing PyTorch (CPU)...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "torch",
                 "--index-url", "https://download.pytorch.org/whl/cpu"],
                check=True,
            )
            print("  PyTorch CPU installed.")

    if not st_installed:
        print("  Installing sentence-transformers + scipy...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "sentence-transformers>=2.5",
             "scipy>=1.12"],
            check=True,
        )
        print("  sentence-transformers installed.")

    # Pre-download the embedding model
    print("  Verifying embedding model...")
    try:
        from server.config import EMBEDDING_MODEL
        from sentence_transformers import SentenceTransformer
        SentenceTransformer(EMBEDDING_MODEL)
        print(f"  Model ready: {EMBEDDING_MODEL}")
    except Exception as e:
        print(f"  Warning: could not pre-load model ({e}). It will download on first server start.")

    # ── Step 3: Install files ──
    print("\n[3/5] Installing skills, agents, rules, and prompts...")
    installed = _install_files(project_path)
    print(f"  {len(installed)} files installed into {project_path / '.claude'}")

    # ── Step 4: Configure MCP ──
    print("\n[4/5] Configuring MCP server...")
    _setup_mcp_json(project_path)

    # ── Step 5: Patch CLAUDE.md ──
    print("\n[5/5] Updating CLAUDE.md...")
    _patch_claude_md(project_path, project_name)

    # ── Step 6: Init project in DB ──
    async def _init_db():
        from server.database import Database
        db = await Database.create(DB_PATH)
        summary = await db.get_setup_summary(project_name)
        if not summary.get("initialized"):
            count = await db.init_setup_progress(project_name)
            print(f"\n  Project '{project_name}' registered with {count} setup steps.")
        else:
            print(f"\n  Project '{project_name}' already registered ({summary['completed']}/{summary['total_steps']} steps).")
        await db.close()

    asyncio.run(_init_db())

    # ── Done ──
    print("\n" + "=" * 60)
    print("  Installation complete!")
    print("=" * 60)
    print(f"\n  Next steps:")
    print(f"  1. Start the dashboard:  mangobrain serve --api")
    print(f"     Then open http://localhost:{API_PORT}")
    print(f"  2. Restart Claude Code (to load MCP server)")
    print(f"  3. Run /brain-init in Claude Code")
    print()


def cmd_install_work(args: argparse.Namespace) -> None:
    """Install MangoBrain Work into a project — marketing, content, strategy workflow."""
    project_path = Path(args.path).resolve() if args.path else Path.cwd()
    project_name = args.project or project_path.name

    if not project_path.exists():
        print(f"Error: path does not exist: {project_path}")
        sys.exit(1)

    print("=" * 60)
    print("  MangoBrain Work — Installation")
    print("=" * 60)

    # ── Step 1: Install Work files ──
    print("\n[1/4] Installing Work skills, agents, rules, and prompts...")
    installed = _install_work_files(project_path)
    print(f"  {len(installed)} files installed into {project_path / '.claude'}")

    # ── Step 2: Install templates ──
    print("\n[2/4] Installing templates...")
    templates_installed = _install_work_templates(project_path)
    print(f"  {len(templates_installed)} template files installed")

    # ── Step 3: Configure MCP ──
    print("\n[3/4] Configuring MCP server...")
    _setup_mcp_json(project_path)

    # ── Step 4: Create project structure ──
    print("\n[4/4] Setting up project structure...")
    briefs_dir = project_path / "briefs"
    briefs_dir.mkdir(exist_ok=True)
    print(f"  Created briefs/")

    # Patch CLAUDE.md with Work section
    _patch_claude_md_work(project_path, project_name)

    # ── Done ──
    print("\n" + "=" * 60)
    print("  MangoBrain Work installed!")
    print("=" * 60)
    print(f"\n  Installed into: {project_path}")
    print(f"\n  Document skills (optional, recommended):")
    print(f"  Install via Claude Code slash commands or copy from:")
    print(f"  https://github.com/anthropics/claude-code/tree/main/skills")
    print(f"    - pptx  (presentations)")
    print(f"    - xlsx  (spreadsheets)")
    print(f"    - docx  (documents)")
    print(f"    - pdf   (PDF manipulation)")
    print(f"    - brand-guidelines")
    print(f"\n  Next steps:")
    print(f"  1. Start the server:  mangobrain serve --api")
    print(f"  2. Restart Claude Code/Desktop")
    print(f"  3. Run /brain-init-work to initialize brand memory")
    print()


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
    print("(Make sure the API server is running: mangobrain serve --api)")
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
                print(f"Project '{project}' not initialized. Run: mangobrain init --project {project}")
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

    # Prompts
    if PROMPTS_SRC.exists():
        prompts_dest = claude_dir / "prompts" / "mangobrain"
        for md_file in PROMPTS_SRC.rglob("*.md"):
            rel = md_file.relative_to(PROMPTS_SRC)
            dest = prompts_dest / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest)
            installed.append(f"prompts/mangobrain/{rel}")

    return installed


def _install_work_files(project_path: Path) -> list[str]:
    """Copy Work skills/agents/rules/prompts into a project's .claude/ directory."""
    installed = []
    claude_dir = project_path / ".claude"

    # Work Skills
    if WORK_SKILLS_SRC.exists():
        for skill_dir in WORK_SKILLS_SRC.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                dest = claude_dir / "skills" / skill_dir.name / "SKILL.md"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(skill_dir / "SKILL.md", dest)
                installed.append(f"skills/{skill_dir.name}/SKILL.md")

    # Work Agents
    if WORK_AGENTS_SRC.exists():
        for agent_file in WORK_AGENTS_SRC.glob("*.md"):
            dest = claude_dir / "agents" / agent_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_file, dest)
            installed.append(f"agents/{agent_file.name}")

    # Work Rules
    if WORK_RULES_SRC.exists():
        for rule_file in WORK_RULES_SRC.glob("*.md"):
            dest = claude_dir / "rules" / rule_file.name
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(rule_file, dest)
            installed.append(f"rules/{rule_file.name}")

    # Work Prompts
    if WORK_PROMPTS_SRC.exists():
        prompts_dest = claude_dir / "prompts" / "mangobrain"
        for md_file in WORK_PROMPTS_SRC.rglob("*.md"):
            rel = md_file.relative_to(WORK_PROMPTS_SRC)
            dest = prompts_dest / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest)
            installed.append(f"prompts/mangobrain/{rel}")

    return installed


def _install_work_templates(project_path: Path) -> list[str]:
    """Copy Work templates (CLAUDE.md template + rule templates) into the project."""
    installed = []
    templates_dest = project_path / ".claude" / "templates"

    if WORK_TEMPLATES_SRC.exists():
        for md_file in WORK_TEMPLATES_SRC.rglob("*.md"):
            rel = md_file.relative_to(WORK_TEMPLATES_SRC)
            dest = templates_dest / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(md_file, dest)
            installed.append(f"templates/{rel}")

    return installed


def _patch_claude_md_work(project_path: Path, project_name: str) -> None:
    """Add MangoBrain Work section to project's CLAUDE.md."""
    claude_md_inner = project_path / ".claude" / "CLAUDE.md"
    claude_md_root = project_path / "CLAUDE.md"
    marker = "## MangoBrain"

    if claude_md_inner.exists():
        claude_md = claude_md_inner
    elif claude_md_root.exists():
        claude_md = claude_md_root
    else:
        claude_md = claude_md_root

    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if marker in content:
            return
    else:
        content = f"# {project_name}\n\n"

    section = f"""
{marker} Work — Memory-Powered Workflow

MangoBrain provides persistent memory and a complete workflow for marketing, content, and strategy work.

### Workflow Skills
- `/brief` — Intake with memory context, produces structured brief in briefs/
- `/create` — Full pipeline: Researcher -> Creator -> Reviewer -> Mem-manager
- `/brain-init-work` — Initialize brand memory (guided setup)
- `/memorize-work` — End-of-session memory sync
- `/elaborate-work` — Periodic memory consolidation
- `/health-check-work` — Memory health diagnosis
- `/smoke-test-work` — Query verification

### Agents (spawned by /create, not invoked directly)
- **researcher** — Gathers context from memory, docs, web
- **creator** — Produces deliverables (copy, presentations, documents)
- **reviewer** — QA against brief and brand guidelines
- **mem-manager** — Persists session knowledge

### Output Structure
- `briefs/` — Brief files ({{date}}-{{HHmm}}-{{slug}}.md)
- `docs/` — Strategy, research, brand documents
- `content/` — Social, copy, editorial
- `media/` — Graphics, video
- `deliverables/` — Presentations, reports, exports

### Rules (auto-loaded)
- `mangobrain-remember-work.md` — Query strategy for Work projects
- `mangobrain-workflow-work.md` — Brief -> Create workflow integration
"""

    claude_md.write_text(content + section, encoding="utf-8")


def _setup_mcp_json(project_path: Path) -> None:
    """Create or update .mcp.json with MangoBrain server entry."""
    mcp_json = project_path / ".mcp.json"

    if mcp_json.exists():
        config = json.loads(mcp_json.read_text(encoding="utf-8"))
    else:
        config = {}

    if "mcpServers" not in config:
        config["mcpServers"] = {}

    # Remove legacy entry if present
    if "mango-brain" in config["mcpServers"]:
        del config["mcpServers"]["mango-brain"]

    # Point to the installed mangobrain's python
    python_path = sys.executable.replace("\\", "/")

    config["mcpServers"]["mangobrain"] = {
        "command": python_path,
        "args": ["-m", "server"],
        "env": {
            "PYTHONIOENCODING": "utf-8",
        },
    }

    mcp_json.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"  .mcp.json configured (python: {python_path})")


def _patch_claude_md(project_path: Path, project_name: str) -> None:
    """Add MangoBrain section to project's CLAUDE.md if not already present.

    Searches for CLAUDE.md in order: .claude/CLAUDE.md, then root CLAUDE.md.
    Patches whichever is found first. Creates root CLAUDE.md only if neither exists.
    """
    claude_md_inner = project_path / ".claude" / "CLAUDE.md"
    claude_md_root = project_path / "CLAUDE.md"
    marker = "## MangoBrain"

    # Find existing CLAUDE.md — prefer .claude/ over root
    if claude_md_inner.exists():
        claude_md = claude_md_inner
    elif claude_md_root.exists():
        claude_md = claude_md_root
    else:
        claude_md = claude_md_root  # Create at root if neither exists

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
- `/brain-init` — First-time memory initialization (guided setup)
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
        prog="mangobrain",
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
    p_install = sub.add_parser("install", help="Full interactive install into a project")
    p_install.add_argument("--path", help="Path to the project directory (default: current dir)")
    p_install.add_argument("--project", "-p", help="Project name (default: folder name)")
    p_install.set_defaults(func=cmd_install)

    # install-work
    p_install_work = sub.add_parser("install-work", help="Install MangoBrain Work (marketing/content/strategy)")
    p_install_work.add_argument("--path", help="Path to the project directory (default: current dir)")
    p_install_work.add_argument("--project", "-p", help="Project name (default: folder name)")
    p_install_work.set_defaults(func=cmd_install_work)

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
