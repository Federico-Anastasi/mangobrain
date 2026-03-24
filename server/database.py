"""MangoBrain — Async SQLite database layer."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from server.models import (
    Edge, EdgeType, Memory, MemorySource, MemoryType, SessionInfo,
    SetupStatus, SetupStep, SETUP_STEPS_TEMPLATE,
)

# ── SQL Schema ─────────────────────────────────────────────────────────────

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id              TEXT PRIMARY KEY,
    content         TEXT NOT NULL,
    embedding       BLOB NOT NULL,
    type            TEXT NOT NULL,
    project         TEXT,
    tags            TEXT,
    token_count     INTEGER NOT NULL,
    source          TEXT,
    source_session  TEXT,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_accessed   DATETIME,
    access_count    INTEGER DEFAULT 0,
    elaboration_date DATETIME,
    elaboration_count INTEGER DEFAULT 0,
    decay_score     REAL DEFAULT 1.0,
    is_deprecated   BOOLEAN DEFAULT FALSE,
    deprecated_by   TEXT,
    file_path       TEXT,
    code_signature  TEXT,
    FOREIGN KEY (deprecated_by) REFERENCES memories(id)
);

CREATE INDEX IF NOT EXISTS idx_memories_project ON memories(project);
CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type);
CREATE INDEX IF NOT EXISTS idx_memories_decay ON memories(decay_score);
CREATE INDEX IF NOT EXISTS idx_memories_elaboration ON memories(elaboration_date);
CREATE INDEX IF NOT EXISTS idx_memories_deprecated ON memories(is_deprecated);

CREATE TABLE IF NOT EXISTS edges (
    id              TEXT PRIMARY KEY,
    from_id         TEXT NOT NULL,
    to_id           TEXT NOT NULL,
    weight          REAL NOT NULL DEFAULT 0.5,
    type            TEXT NOT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_reinforced DATETIME,
    reinforce_count INTEGER DEFAULT 0,
    source          TEXT,
    FOREIGN KEY (from_id) REFERENCES memories(id),
    FOREIGN KEY (to_id) REFERENCES memories(id),
    UNIQUE(from_id, to_id, type)
);

CREATE INDEX IF NOT EXISTS idx_edges_from ON edges(from_id);
CREATE INDEX IF NOT EXISTS idx_edges_to ON edges(to_id);
CREATE INDEX IF NOT EXISTS idx_edges_weight ON edges(weight);

CREATE TABLE IF NOT EXISTS operation_log (
    id              TEXT PRIMARY KEY,
    tool            TEXT,
    project         TEXT,
    params          TEXT,
    result          TEXT,
    status          TEXT DEFAULT 'ok',
    duration_ms     INTEGER,
    started_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at    DATETIME,
    -- Legacy elaboration columns (NULL for non-elaborate operations)
    seed_count      INTEGER,
    working_set     INTEGER,
    seed_ids        TEXT,
    new_memories    INTEGER DEFAULT 0,
    updated_memories INTEGER DEFAULT 0,
    deprecated_memories INTEGER DEFAULT 0,
    new_edges       INTEGER DEFAULT 0,
    updated_edges   INTEGER DEFAULT 0,
    summary         TEXT
);

CREATE INDEX IF NOT EXISTS idx_operation_log_tool ON operation_log(tool);
CREATE INDEX IF NOT EXISTS idx_operation_log_project ON operation_log(project);
CREATE INDEX IF NOT EXISTS idx_operation_log_started ON operation_log(started_at);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    project         TEXT,
    run_type        TEXT,
    run_name        TEXT,
    started_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    extracted_at    DATETIME,
    memories_extracted INTEGER DEFAULT 0,
    raw_token_count INTEGER,
    notes           TEXT
);

CREATE TABLE IF NOT EXISTS setup_progress (
    project         TEXT NOT NULL,
    phase           TEXT NOT NULL,
    step            TEXT NOT NULL,
    order_index     INTEGER NOT NULL,
    title           TEXT NOT NULL,
    description     TEXT DEFAULT '',
    status          TEXT DEFAULT 'pending',
    prompt_file     TEXT,
    started_at      DATETIME,
    completed_at    DATETIME,
    result          TEXT,
    PRIMARY KEY (project, phase, step)
);
"""


def _row_to_memory(row: aiosqlite.Row) -> Memory:
    d = dict(row)
    d["tags"] = json.loads(d["tags"]) if d["tags"] else []
    d["is_deprecated"] = bool(d["is_deprecated"])
    return Memory(**d)


def _row_to_edge(row: aiosqlite.Row) -> Edge:
    return Edge(**dict(row))


def _row_to_session(row: aiosqlite.Row) -> SessionInfo:
    return SessionInfo(**dict(row))


class Database:
    """Async SQLite database — singleton pattern."""

    _instance: Optional["Database"] = None

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._conn: Optional[aiosqlite.Connection] = None

    @classmethod
    async def create(cls, db_path: str | Path) -> "Database":
        if cls._instance is None:
            inst = cls(db_path)
            await inst._connect()
            cls._instance = inst
        return cls._instance

    async def _connect(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA_SQL)
        await self._conn.execute("PRAGMA journal_mode=WAL")
        await self._conn.commit()

        # Migration for existing DBs: add file_path and code_signature
        try:
            await self._conn.execute("ALTER TABLE memories ADD COLUMN file_path TEXT")
            await self._conn.commit()
        except Exception:
            pass  # Column already exists
        try:
            await self._conn.execute("ALTER TABLE memories ADD COLUMN code_signature TEXT")
            await self._conn.commit()
        except Exception:
            pass  # Column already exists
        await self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_file_path ON memories(file_path)"
        )
        await self._conn.commit()

        # Migration: elaboration_log → operation_log
        await self._migrate_elaboration_log()

    @property
    def conn(self) -> aiosqlite.Connection:
        assert self._conn is not None, "Database not connected"
        return self._conn

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None
            Database._instance = None

    # ── Memories ───────────────────────────────────────────────────────────

    async def insert_memory(self, m: Memory) -> str:
        await self.conn.execute(
            """INSERT INTO memories
               (id, content, embedding, type, project, tags, token_count,
                source, source_session, created_at, last_accessed, access_count,
                elaboration_date, elaboration_count, decay_score, is_deprecated, deprecated_by,
                file_path, code_signature)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                m.id, m.content, m.embedding, m.type.value, m.project,
                json.dumps(m.tags), m.token_count,
                m.source.value if m.source else None, m.source_session,
                m.created_at.isoformat(), m.last_accessed.isoformat() if m.last_accessed else None,
                m.access_count, m.elaboration_date.isoformat() if m.elaboration_date else None,
                m.elaboration_count, m.decay_score, m.is_deprecated, m.deprecated_by,
                m.file_path, m.code_signature,
            ),
        )
        await self.conn.commit()
        return m.id

    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        cur = await self.conn.execute("SELECT * FROM memories WHERE id=?", (memory_id,))
        row = await cur.fetchone()
        return _row_to_memory(row) if row else None

    async def get_all_memories(
        self,
        project: Optional[str] = None,
        type: Optional[MemoryType] = None,
        deprecated: bool = False,
    ) -> list[Memory]:
        clauses: list[str] = []
        params: list[Any] = []
        if not deprecated:
            clauses.append("is_deprecated = 0")
        if project:
            clauses.append("project = ?")
            params.append(project)
        if type:
            clauses.append("type = ?")
            params.append(type.value)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = await self.conn.execute(f"SELECT * FROM memories {where}", params)
        return [_row_to_memory(r) for r in await cur.fetchall()]

    async def get_recent_memories(
        self,
        project: Optional[str] = None,
        limit: int = 15,
    ) -> list[Memory]:
        """Get most recently created non-deprecated memories."""
        clauses = ["is_deprecated = 0"]
        params: list[Any] = []
        if project:
            clauses.append("project = ?")
            params.append(project)
        where = f"WHERE {' AND '.join(clauses)}"
        cur = await self.conn.execute(
            f"SELECT * FROM memories {where} ORDER BY created_at DESC LIMIT ?",
            params + [limit],
        )
        return [_row_to_memory(r) for r in await cur.fetchall()]

    async def update_memory(self, memory_id: str, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        # Serialize special fields
        if "tags" in fields:
            fields["tags"] = json.dumps(fields["tags"])
        if "source" in fields and isinstance(fields["source"], MemorySource):
            fields["source"] = fields["source"].value
        if "type" in fields and isinstance(fields["type"], MemoryType):
            fields["type"] = fields["type"].value
        for k in ("last_accessed", "elaboration_date", "created_at"):
            if k in fields and isinstance(fields[k], datetime):
                fields[k] = fields[k].isoformat()
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [memory_id]
        await self.conn.execute(f"UPDATE memories SET {sets} WHERE id=?", vals)
        await self.conn.commit()
        return True

    # ── Edges ──────────────────────────────────────────────────────────────

    async def insert_edge(self, e: Edge) -> str:
        await self.conn.execute(
            """INSERT OR IGNORE INTO edges
               (id, from_id, to_id, weight, type, created_at, last_reinforced, reinforce_count, source)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                e.id, e.from_id, e.to_id, e.weight, e.type.value,
                e.created_at.isoformat(),
                e.last_reinforced.isoformat() if e.last_reinforced else None,
                e.reinforce_count,
                e.source.value if e.source else None,
            ),
        )
        await self.conn.commit()
        return e.id

    async def get_edges(self, memory_id: Optional[str] = None) -> list[Edge]:
        if memory_id:
            cur = await self.conn.execute(
                "SELECT * FROM edges WHERE from_id=? OR to_id=?",
                (memory_id, memory_id),
            )
        else:
            cur = await self.conn.execute("SELECT * FROM edges")
        return [_row_to_edge(r) for r in await cur.fetchall()]

    async def get_all_edges(self, memory_ids: Optional[list[str]] = None) -> list[Edge]:
        if memory_ids is None:
            return await self.get_edges()
        if not memory_ids:
            return []
        placeholders = ",".join("?" * len(memory_ids))
        cur = await self.conn.execute(
            f"SELECT * FROM edges WHERE from_id IN ({placeholders}) AND to_id IN ({placeholders})",
            memory_ids + memory_ids,
        )
        return [_row_to_edge(r) for r in await cur.fetchall()]

    async def update_edge(self, edge_id: str, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        for k in ("last_reinforced", "created_at"):
            if k in fields and isinstance(fields[k], datetime):
                fields[k] = fields[k].isoformat()
        if "type" in fields and isinstance(fields["type"], EdgeType):
            fields["type"] = fields["type"].value
        if "source" in fields and isinstance(fields["source"], MemorySource):
            fields["source"] = fields["source"].value
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [edge_id]
        await self.conn.execute(f"UPDATE edges SET {sets} WHERE id=?", vals)
        await self.conn.commit()
        return True

    async def delete_edge(self, edge_id: str) -> bool:
        cur = await self.conn.execute("DELETE FROM edges WHERE id=?", (edge_id,))
        await self.conn.commit()
        return cur.rowcount > 0

    # ── Sessions ───────────────────────────────────────────────────────────

    async def insert_session(self, s: SessionInfo) -> str:
        await self.conn.execute(
            """INSERT INTO sessions
               (id, project, run_type, run_name, started_at, extracted_at,
                memories_extracted, raw_token_count, notes)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (
                s.id, s.project,
                s.run_type.value if s.run_type else None,
                s.run_name, s.started_at.isoformat(),
                s.extracted_at.isoformat() if s.extracted_at else None,
                s.memories_extracted, s.raw_token_count, s.notes,
            ),
        )
        await self.conn.commit()
        return s.id

    async def update_session(self, session_id: str, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        for k in ("started_at", "extracted_at"):
            if k in fields and isinstance(fields[k], datetime):
                fields[k] = fields[k].isoformat()
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [session_id]
        await self.conn.execute(f"UPDATE sessions SET {sets} WHERE id=?", vals)
        await self.conn.commit()
        return True

    async def get_sessions(self, project: Optional[str] = None) -> list[SessionInfo]:
        if project:
            cur = await self.conn.execute(
                "SELECT * FROM sessions WHERE project=? ORDER BY started_at DESC", (project,)
            )
        else:
            cur = await self.conn.execute("SELECT * FROM sessions ORDER BY started_at DESC")
        return [_row_to_session(r) for r in await cur.fetchall()]

    # ── Operation Log ─────────────────────────────────────────────────────

    async def _migrate_elaboration_log(self) -> None:
        """Migrate elaboration_log → operation_log for existing DBs."""
        try:
            cur = await self.conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='elaboration_log'"
            )
            if await cur.fetchone():
                # Old table exists — migrate data into operation_log
                await self.conn.execute(
                    """INSERT OR IGNORE INTO operation_log
                       (id, tool, started_at, completed_at, seed_count, working_set,
                        seed_ids, new_memories, updated_memories, deprecated_memories,
                        new_edges, updated_edges, summary, status)
                       SELECT id, 'elaborate', started_at, completed_at, seed_count,
                              working_set, seed_ids, new_memories, updated_memories,
                              deprecated_memories, new_edges, updated_edges, summary, status
                       FROM elaboration_log"""
                )
                await self.conn.execute("DROP TABLE elaboration_log")
                await self.conn.commit()
        except Exception:
            pass  # Already migrated or no old table

    async def insert_operation(self, op: dict[str, Any]) -> str:
        """Insert a generic operation log entry."""
        op_id = op.get("id", str(uuid.uuid4()))
        await self.conn.execute(
            """INSERT INTO operation_log
               (id, tool, project, params, result, status, duration_ms,
                started_at, completed_at,
                seed_count, working_set, seed_ids, new_memories,
                updated_memories, deprecated_memories, new_edges,
                updated_edges, summary)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                op_id, op.get("tool"), op.get("project"),
                op.get("params"), op.get("result"),
                op.get("status", "ok"), op.get("duration_ms"),
                op.get("started_at", datetime.utcnow().isoformat()),
                op.get("completed_at"),
                op.get("seed_count"), op.get("working_set"),
                op.get("seed_ids"),
                op.get("new_memories", 0), op.get("updated_memories", 0),
                op.get("deprecated_memories", 0), op.get("new_edges", 0),
                op.get("updated_edges", 0), op.get("summary"),
            ),
        )
        await self.conn.commit()
        return op_id

    async def update_operation(self, op_id: str, fields: dict[str, Any]) -> bool:
        if not fields:
            return False
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [op_id]
        await self.conn.execute(f"UPDATE operation_log SET {sets} WHERE id=?", vals)
        await self.conn.commit()
        return True

    async def get_operations(
        self,
        tool: str | None = None,
        project: str | None = None,
        limit: int = 50,
    ) -> list[dict]:
        clauses: list[str] = []
        params: list[Any] = []
        if tool:
            clauses.append("tool = ?")
            params.append(tool)
        if project:
            clauses.append("project = ?")
            params.append(project)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        cur = await self.conn.execute(
            f"SELECT * FROM operation_log {where} ORDER BY started_at DESC LIMIT ?",
            params + [limit],
        )
        return [dict(r) for r in await cur.fetchall()]

    # Backward-compatible aliases for elaboration
    async def insert_elaboration_log(self, log: dict[str, Any]) -> str:
        log["tool"] = "elaborate"
        return await self.insert_operation(log)

    async def update_elaboration_log(self, log_id: str, fields: dict[str, Any]) -> bool:
        return await self.update_operation(log_id, fields)

    async def get_elaboration_logs(self, limit: int = 20) -> list[dict]:
        return await self.get_operations(tool="elaborate", limit=limit)

    # ── Search ─────────────────────────────────────────────────────────────

    async def search_memories(
        self,
        search: Optional[str] = None,
        project: Optional[str] = None,
        type: Optional[MemoryType] = None,
        tags: Optional[list[str]] = None,
        deprecated: bool = False,
        sort: str = "created",
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Memory], int]:
        clauses: list[str] = []
        params: list[Any] = []

        if not deprecated:
            clauses.append("is_deprecated = 0")
        if project:
            clauses.append("project = ?")
            params.append(project)
        if type:
            clauses.append("type = ?")
            params.append(type.value)
        if search:
            clauses.append("content LIKE ?")
            params.append(f"%{search}%")
        if tags:
            for tag in tags:
                clauses.append("tags LIKE ?")
                params.append(f'%"{tag}"%')

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        sort_map = {
            "created": "created_at DESC",
            "accessed": "last_accessed DESC",
            "decay": "decay_score ASC",
        }
        order = sort_map.get(sort, "created_at DESC")

        # Count
        cur = await self.conn.execute(f"SELECT COUNT(*) FROM memories {where}", params)
        total = (await cur.fetchone())[0]

        # Fetch
        cur = await self.conn.execute(
            f"SELECT * FROM memories {where} ORDER BY {order} LIMIT ? OFFSET ?",
            params + [limit, offset],
        )
        memories = [_row_to_memory(r) for r in await cur.fetchall()]
        return memories, total

    # ── Elaboration helpers ────────────────────────────────────────────────

    # ── Setup Progress ──────────────────────────────────────────────────────

    async def init_setup_progress(self, project: str) -> int:
        """Initialize setup_progress rows for a project. Returns count of steps created."""
        created = 0
        for phase, step, order, title, desc, prompt_file in SETUP_STEPS_TEMPLATE:
            try:
                await self.conn.execute(
                    """INSERT INTO setup_progress
                       (project, phase, step, order_index, title, description, status, prompt_file)
                       VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
                    (project, phase, step, order, title, desc, prompt_file),
                )
                created += 1
            except Exception:
                pass  # Already exists (UNIQUE constraint)
        await self.conn.commit()
        return created

    async def get_setup_progress(self, project: str) -> list[SetupStep]:
        """Get all setup steps for a project, ordered by index."""
        cur = await self.conn.execute(
            "SELECT * FROM setup_progress WHERE project=? ORDER BY order_index",
            (project,),
        )
        rows = await cur.fetchall()
        return [SetupStep(**dict(r)) for r in rows]

    async def update_setup_step(
        self, project: str, phase: str, step: str, fields: dict[str, Any]
    ) -> bool:
        """Update a setup step's status/result."""
        if not fields:
            return False
        for k in ("started_at", "completed_at"):
            if k in fields and isinstance(fields[k], datetime):
                fields[k] = fields[k].isoformat()
        if "status" in fields and isinstance(fields["status"], SetupStatus):
            fields["status"] = fields["status"].value
        sets = ", ".join(f"{k}=?" for k in fields)
        vals = list(fields.values()) + [project, phase, step]
        await self.conn.execute(
            f"UPDATE setup_progress SET {sets} WHERE project=? AND phase=? AND step=?",
            vals,
        )
        await self.conn.commit()
        return True

    async def get_setup_summary(self, project: str) -> dict[str, Any]:
        """Get a summary of setup progress for a project."""
        steps = await self.get_setup_progress(project)
        if not steps:
            return {"project": project, "initialized": False, "steps": 0}
        total = len(steps)
        completed = sum(1 for s in steps if s.status == SetupStatus.completed)
        skipped = sum(1 for s in steps if s.status == SetupStatus.skipped)
        current = next(
            (s for s in steps if s.status in (SetupStatus.pending, SetupStatus.in_progress, SetupStatus.failed)),
            None,
        )
        is_ready = any(
            s.phase == "ready" and s.status == SetupStatus.completed for s in steps
        )
        return {
            "project": project,
            "initialized": True,
            "total_steps": total,
            "completed": completed,
            "skipped": skipped,
            "progress_pct": round((completed + skipped) / total * 100) if total else 0,
            "is_ready": is_ready,
            "current_step": {
                "phase": current.phase,
                "step": current.step,
                "title": current.title,
                "description": current.description,
                "status": current.status.value,
                "prompt_file": current.prompt_file,
            } if current else None,
        }

    async def get_all_projects_setup(self) -> list[dict[str, Any]]:
        """Get setup summary for all projects that have setup_progress."""
        cur = await self.conn.execute(
            "SELECT DISTINCT project FROM setup_progress ORDER BY project"
        )
        projects = [row[0] for row in await cur.fetchall()]
        return [await self.get_setup_summary(p) for p in projects]

    # ── Elaboration helpers ────────────────────────────────────────────────

    async def get_memories_for_elaboration(
        self, count: int, project: Optional[str] = None
    ) -> list[Memory]:
        clauses = ["m.is_deprecated = 0"]
        params: list[Any] = []
        if project:
            clauses.append("m.project = ?")
            params.append(project)
        where = f"WHERE {' AND '.join(clauses)}"
        # Priority: fewest edges first (sparse graph nodes need connections),
        # then lowest elaboration_count, then oldest elaboration_date.
        cur = await self.conn.execute(
            f"""SELECT m.*
                FROM memories m
                LEFT JOIN (
                    SELECT mid, COUNT(*) as edge_count FROM (
                        SELECT from_id as mid FROM edges
                        UNION ALL
                        SELECT to_id as mid FROM edges
                    ) GROUP BY mid
                ) ec ON m.id = ec.mid
                {where}
                ORDER BY
                    COALESCE(ec.edge_count, 0) ASC,
                    m.elaboration_count ASC,
                    m.elaboration_date IS NOT NULL,
                    m.elaboration_date ASC
                LIMIT ?""",
            params + [count],
        )
        return [_row_to_memory(r) for r in await cur.fetchall()]
