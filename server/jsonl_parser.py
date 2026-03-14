"""MangoBrain — JSONL session parser."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


def find_latest_session(project: str) -> Optional[str]:
    """Find the most recently modified JSONL session file for a project.

    Claude Code stores sessions in ~/.claude/projects/[encoded-path]/*.jsonl
    The encoded path replaces path separators with double dashes.
    """
    home = Path.home()
    # Try common encoded patterns
    project_paths = [
        home / ".claude" / "projects",
    ]

    for base in project_paths:
        if not base.exists():
            continue
        # Look for directories matching the project name
        for d in base.iterdir():
            if not d.is_dir():
                continue
            if project.lower() in d.name.lower():
                # Find latest JSONL
                jsonls = sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
                if jsonls:
                    return str(jsonls[0])

    return None


def find_all_sessions(project: str) -> list[str]:
    """Find all JSONL session files for a project, sorted oldest-first.

    Returns list of absolute paths.
    """
    home = Path.home()
    base = home / ".claude" / "projects"
    if not base.exists():
        return []

    results: list[tuple[float, str]] = []
    for d in base.iterdir():
        if not d.is_dir():
            continue
        if project.lower() in d.name.lower():
            for jsonl in d.glob("*.jsonl"):
                results.append((jsonl.stat().st_mtime, str(jsonl)))

    results.sort(key=lambda x: x[0])  # oldest first
    return [path for _, path in results]


def parse_session_jsonl(path: str) -> tuple[str, int]:
    """Parse a Claude Code JSONL session file into clean dialogue.

    Returns:
        (formatted_dialogue, message_count)
    """
    lines: list[str] = []
    message_count = 0

    with open(path, "r", encoding="utf-8") as f:
        for raw_line in f:
            raw_line = raw_line.strip()
            if not raw_line:
                continue
            try:
                entry = json.loads(raw_line)
            except json.JSONDecodeError:
                continue

            # Handle different JSONL formats
            msg = entry if "role" in entry else entry.get("message", {})
            role = msg.get("role", "")

            if role not in ("user", "assistant"):
                continue

            # Extract text content only (skip tool_use, tool_result blocks)
            content = msg.get("content", "")
            if isinstance(content, list):
                # Content is array of blocks
                text_parts = []
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        text_parts.append(block)
                content = "\n".join(text_parts)

            if not content or not content.strip():
                continue

            label = "[USER]" if role == "user" else "[ASSISTANT]"
            lines.append(f"{label}: {content.strip()}")
            message_count += 1

    return "\n\n".join(lines), message_count
