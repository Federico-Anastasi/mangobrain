"""MangoBrain — Pydantic models."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

import numpy as np
from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class MemoryType(str, Enum):
    episodic = "episodic"
    semantic = "semantic"
    procedural = "procedural"


class EdgeType(str, Enum):
    relates_to = "relates_to"
    caused_by = "caused_by"
    depends_on = "depends_on"
    co_occurs = "co_occurs"
    contradicts = "contradicts"
    supersedes = "supersedes"


class RunType(str, Enum):
    implementation = "implementation"
    planning = "planning"
    microfix = "microfix"


class MemorySource(str, Enum):
    extraction = "extraction"
    elaboration = "elaboration"
    manual = "manual"


# ── Core Models ────────────────────────────────────────────────────────────

class Memory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    embedding: bytes = b""  # numpy tobytes

    type: MemoryType
    project: Optional[str] = None
    tags: list[str] = Field(default_factory=list)

    token_count: int = 0
    source: Optional[MemorySource] = None
    source_session: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    elaboration_date: Optional[datetime] = None
    elaboration_count: int = 0

    decay_score: float = 1.0
    is_deprecated: bool = False
    deprecated_by: Optional[str] = None

    file_path: Optional[str] = None
    code_signature: Optional[str] = None

    model_config = {"arbitrary_types_allowed": True}


class Edge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    from_id: str
    to_id: str

    weight: float = 0.5
    type: EdgeType

    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_reinforced: Optional[datetime] = None
    reinforce_count: int = 0
    source: Optional[MemorySource] = None


class SessionInfo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project: Optional[str] = None
    run_type: Optional[RunType] = None
    run_name: Optional[str] = None

    started_at: datetime = Field(default_factory=datetime.utcnow)
    extracted_at: Optional[datetime] = None

    memories_extracted: int = 0
    raw_token_count: Optional[int] = None
    notes: Optional[str] = None


# ── Input Models (no auto-generated fields) ────────────────────────────────

class Relation(BaseModel):
    target_query: str
    relation_type: EdgeType = EdgeType.relates_to
    weight: float = 0.5


class MemoryInput(BaseModel):
    content: str
    type: MemoryType
    project: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)
    file_path: Optional[str] = None
    code_signature: Optional[str] = None


# ── Elaboration Models ─────────────────────────────────────────────────────

class MemoryUpdate(BaseModel):
    id: str
    new_content: str


class MemoryDeprecation(BaseModel):
    id: str
    reason: str
    replaced_by: Optional[str] = None


class EdgeAdd(BaseModel):
    from_id: str
    to_id: str
    type: EdgeType
    weight: float = 0.5


class EdgeUpdate(BaseModel):
    id: str
    new_weight: float


class ElaborationUpdate(BaseModel):
    memories_to_update: list[MemoryUpdate] = Field(default_factory=list)
    memories_to_add: list[MemoryInput] = Field(default_factory=list)
    memories_to_deprecate: list[MemoryDeprecation] = Field(default_factory=list)
    edges_to_add: list[EdgeAdd] = Field(default_factory=list)
    edges_to_update: list[EdgeUpdate] = Field(default_factory=list)
    edges_to_remove: list[str] = Field(default_factory=list)
    confirmed: list[str] = Field(default_factory=list)


class ElaborationReport(BaseModel):
    new_memories: int = 0
    updated_memories: int = 0
    deprecated: int = 0
    new_edges: int = 0
    updated_edges: int = 0
    removed_edges: int = 0
    summary: str = ""


# ── Stats Models ───────────────────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_memories: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)
    by_project: dict[str, int] = Field(default_factory=dict)
    total_edges: int = 0
    avg_connections_per_memory: float = 0.0
    memories_never_accessed: int = 0
    memories_never_elaborated: int = 0
    oldest_unelaborated: Optional[datetime] = None
    last_extraction: Optional[datetime] = None
    last_elaboration: Optional[datetime] = None
    health_alerts: list[str] = Field(default_factory=list)


# ── Setup Progress ────────────────────────────────────────────────────────────

class SetupStatus(str, Enum):
    pending = "pending"
    in_progress = "in_progress"
    completed = "completed"
    skipped = "skipped"
    failed = "failed"


class SetupStep(BaseModel):
    project: str
    phase: str
    step: str
    order_index: int
    title: str
    description: str = ""
    status: SetupStatus = SetupStatus.pending
    prompt_file: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None  # JSON string


# The 14 setup steps — (phase, step, order, title, description, prompt_file)
SETUP_STEPS_TEMPLATE: list[tuple[str, str, int, str, str, str | None]] = [
    ("install", "skills_rules", 1,
     "Install Skills & Rules",
     "Copy MangoBrain skills, agents, and rules into the project's .claude/ directory",
     None),
    ("install", "mcp_config", 2,
     "Verify MCP Config",
     "Verify the MCP server is configured and accessible from the project",
     None),
    ("init", "doc_base", 3,
     "Doc Base — Rules & Documentation",
     "Extract memories from CLAUDE.md, .claude/rules/, and any project documentation",
     "prompts/init/01-doc-base.md"),
    ("init", "code_base", 4,
     "Code Base — Parallel Codebase Scan",
     "Explore the codebase with 4-5 parallel analyzer agents to create reference memories",
     "prompts/init/02-code-base.md"),
    ("init", "event_base", 5,
     "Event Base — Existing Memory Import",
     "Import from PROJECT_MEMORY.jsonl, documents, task lists, or other knowledge archives (optional)",
     "prompts/init/03-event-base.md"),
    ("init", "chat_base", 6,
     "Chat Base — Chat History Extraction",
     "Extract memories from 5-20 recent Claude Code chat sessions",
     "prompts/init/04-chat-base.md"),
    ("init", "elaborate_base", 7,
     "Elaborate Base — First Elaboration Pass",
     "Run N elaboration cycles until all memories have at least one pass and unconnected nodes are linked",
     "prompts/init/05-elaborate-base.md"),
    ("smoke_test", "queries", 8,
     "Smoke Test — Query Verification",
     "Run 10-20 diverse remember queries to verify retrieval quality across different areas",
     None),
    ("health_check", "diagnose", 9,
     "Health Check — Initial Diagnosis",
     "Run diagnose() to get the baseline health score and identify issues",
     None),
    ("health_check", "content_gap", 10,
     "Content Gap — Coverage Analysis",
     "Scan filesystem and code for areas with no memory coverage, fill the gaps",
     None),
    ("health_check", "elaborate_fix", 11,
     "Elaborate Fix — Structural Repair",
     "Run 2-3 targeted elaboration rounds to fix structural issues identified by diagnose",
     None),
    ("validation", "final_queries", 12,
     "Final Queries — Retrieval Validation",
     "Run diverse queries and verify improved retrieval quality vs. smoke test",
     None),
    ("validation", "final_health", 13,
     "Final Health Check — Score Confirmation",
     "Re-run diagnose() and confirm health score meets target thresholds",
     None),
    ("ready", "memory_ready", 14,
     "Memory Ready",
     "Memory system is fully initialized and operational. Normal workflow can begin.",
     None),
]
