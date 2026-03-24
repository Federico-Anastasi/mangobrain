"""MangoBrain — MCP tool definitions."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import numpy as np
from mcp.server.fastmcp import FastMCP

from server.config import DEDUP_THRESHOLD, count_tokens
from server.database import Database
from server.decay import DecayManager
from server.embeddings import Embedder
from server.graph import GraphManager
from server.models import (
    Edge,
    EdgeType,
    ElaborationReport,
    ElaborationUpdate,
    Memory,
    MemoryInput,
    MemorySource,
    MemoryType,
    SessionInfo,
)
from server.retrieval import RetrievalEngine

logger = logging.getLogger(__name__)


async def _log_op(
    db: Database,
    tool: str,
    project: str | None = None,
    params: dict | None = None,
    result: dict | None = None,
    status: str = "ok",
    duration_ms: int | None = None,
) -> None:
    """Log an MCP tool operation to operation_log."""
    try:
        await db.insert_operation({
            "tool": tool,
            "project": project,
            "params": json.dumps(params, ensure_ascii=False) if params else None,
            "result": json.dumps(result, ensure_ascii=False) if result else None,
            "status": status,
            "duration_ms": duration_ms,
        })
    except Exception as e:
        logger.warning(f"Failed to log operation {tool}: {e}")


def register_tools(
    server: FastMCP,
    db: Database,
    embedder: Embedder,
    graph: GraphManager,
    retrieval: RetrievalEngine,
) -> None:
    """Register all MCP tools on the server."""

    # ── remember ───────────────────────────────────────────────────────────

    @server.tool()
    async def remember(
        query: str = "",
        mode: str = "deep",
        project: str | None = None,
        budget: int | None = None,
        session_id: str | None = None,
        limit: int = 15,
        k_neighbors: int = 2,
    ) -> str:
        """Retrieve relevant memories for a task or question.

        Args:
            query: Description of the task or question. Optional for mode="recent".
            mode: "deep" for session start, "quick" for mid-session, "recent" for temporal retrieval.
            project: Filter by project name (e.g. "myproject"). None = search all.
            budget: Override token budget. Default: deep=8000, quick=2000.
            session_id: Session ID for budget tracking (quick mode).
            limit: Number of recent memories to fetch (mode="recent" only, default 15).
            k_neighbors: Graph hops for neighbor expansion (mode="recent" only, default 2).
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        try:
            if mode == "recent":
                from server.config import DEEP_BUDGET
                memories, scores, total_tokens = await retrieval.remember_recent(
                    project=project, limit=limit, k_neighbors=k_neighbors,
                    budget=budget or DEEP_BUDGET,
                )
                # Determine which are recent vs neighbor
                recent_mems = await db.get_recent_memories(project=project, limit=limit)
                recent_ids = {m.id for m in recent_mems}
                recent_count = sum(1 for m in memories if m.id in recent_ids)
                neighbor_count = len(memories) - recent_count

                result = {
                    "memories": [
                        {
                            "id": m.id,
                            "content": m.content,
                            "type": m.type.value if hasattr(m.type, 'value') else m.type,
                            "project": m.project,
                            "tags": m.tags,
                            "relevance": round(scores[i], 4),
                            "file_path": m.file_path,
                            "code_signature": m.code_signature,
                            "is_recent": m.id in recent_ids,
                        }
                        for i, m in enumerate(memories)
                    ],
                    "total_tokens": total_tokens,
                    "count": len(memories),
                    "recent_count": recent_count,
                    "neighbor_count": neighbor_count,
                }
            else:
                if not query:
                    return json.dumps({"error": "query is required for deep/quick mode"})
                memories, scores, total_tokens = await retrieval.remember(
                    query=query, mode=mode, project=project,
                    budget=budget, session_id=session_id,
                )
                result = {
                    "memories": [
                        {
                            "id": m.id,
                            "content": m.content,
                            "type": m.type.value if hasattr(m.type, 'value') else m.type,
                            "project": m.project,
                            "tags": m.tags,
                            "relevance": round(scores[i], 4),
                            "file_path": m.file_path,
                            "code_signature": m.code_signature,
                        }
                        for i, m in enumerate(memories)
                    ],
                    "total_tokens": total_tokens,
                    "count": len(memories),
                }
            _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
            await _log_op(db, "remember", project=project,
                          params={"query": query, "mode": mode, "limit": limit},
                          result={"count": result["count"], "total_tokens": result["total_tokens"]},
                          duration_ms=_dur)
            return json.dumps(result, indent=2)
        except ValueError as e:
            _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
            await _log_op(db, "remember", project=project,
                          params={"query": query, "mode": mode},
                          result={"error": str(e)}, status="error", duration_ms=_dur)
            return json.dumps({"error": str(e)})

    # ── memorize ───────────────────────────────────────────────────────────

    @server.tool()
    async def memorize(
        memories: list[dict[str, Any]],
        session_id: str | None = None,
        source: str = "manual",
    ) -> str:
        """Save one or more memories to the brain.

        Args:
            memories: List of memory objects with keys: content, type, project?, tags?, relations?
            session_id: Session ID if from extraction.
            source: "manual", "extraction", or "elaboration".
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        created = 0
        edges_created = 0
        duplicates_skipped = 0
        _project = None
        src = MemorySource(source)

        for mem_dict in memories:
            mi = MemoryInput(**mem_dict)
            if mi.project:
                _project = mi.project

            # Compute embedding
            emb = embedder.encode(mi.content)
            emb_bytes = Embedder.embedding_to_bytes(emb)

            # Dedup check
            existing = await db.get_all_memories(project=mi.project, deprecated=False)
            if existing:
                existing_embs = np.array([
                    Embedder.bytes_to_embedding(m.embedding) for m in existing
                ])
                sims = Embedder.cosine_similarity(emb, existing_embs)
                if sims.max() > DEDUP_THRESHOLD:
                    duplicates_skipped += 1
                    continue

            # Create memory
            memory = Memory(
                content=mi.content,
                embedding=emb_bytes,
                type=mi.type,
                project=mi.project,
                tags=mi.tags,
                token_count=count_tokens(mi.content),
                source=src,
                source_session=session_id,
                file_path=mi.file_path,
                code_signature=mi.code_signature,
            )
            await db.insert_memory(memory)
            created += 1

            # Create edges from relations
            for rel in mi.relations:
                target_mem_id = None
                if rel.target_id:
                    # Direct ID — verify it exists
                    target_mem = await db.get_memory(rel.target_id)
                    if target_mem:
                        target_mem_id = rel.target_id
                if not target_mem_id and rel.target_query and existing:
                    # Semantic search fallback
                    rel_emb = embedder.encode(rel.target_query)
                    sims = Embedder.cosine_similarity(rel_emb, existing_embs)
                    best_idx = int(sims.argmax())
                    if sims[best_idx] > 0.5:
                        target_mem_id = existing[best_idx].id
                if target_mem_id:
                    edge = Edge(
                        from_id=memory.id,
                        to_id=target_mem_id,
                        weight=rel.weight,
                        type=rel.relation_type,
                        source=src,
                    )
                    await db.insert_edge(edge)
                    edges_created += 1

        _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
        _res = {"created": created, "edges_created": edges_created, "duplicates_skipped": duplicates_skipped}
        await _log_op(db, "memorize", project=_project,
                      params={"count": len(memories), "source": source},
                      result=_res, duration_ms=_dur)
        return json.dumps(_res)

    # ── extract_session ────────────────────────────────────────────────────

    @server.tool()
    async def extract_session(
        session_jsonl_path: str | None = None,
        project: str | None = None,
        run_type: str | None = None,
        run_name: str | None = None,
    ) -> str:
        """Prepare raw session data for extraction.

        Returns metadata only (session_id, token_count, chat_file_path).
        The chat text is saved to a file — read it with the Read tool using offset/limit.

        Args:
            session_jsonl_path: Path to JSONL file. If None, uses latest for project.
            project: Project name.
            run_type: "implementation", "planning", or "microfix".
            run_name: Human-readable session name.
        """
        from server.jsonl_parser import find_latest_session, parse_session_jsonl

        if session_jsonl_path is None and project:
            session_jsonl_path = find_latest_session(project)
        if session_jsonl_path is None:
            return json.dumps({"error": "No session file found"})

        chat_text, message_count = parse_session_jsonl(session_jsonl_path)
        token_count_val = count_tokens(chat_text)

        session = SessionInfo(
            project=project,
            run_type=run_type,
            run_name=run_name,
            raw_token_count=token_count_val,
        )
        await db.insert_session(session)

        # Save chat to file for chunked reading
        from server.config import PROJECT_ROOT
        chat_dir = PROJECT_ROOT / "data" / "sessions"
        chat_dir.mkdir(parents=True, exist_ok=True)
        chat_file = chat_dir / f"{session.id}.txt"
        chat_file.write_text(chat_text, encoding="utf-8")

        return json.dumps({
            "session_id": session.id,
            "chat_file_path": str(chat_file),
            "token_count": token_count_val,
            "message_count": message_count,
        })

    # ── prepare_elaboration ────────────────────────────────────────────────

    @server.tool()
    async def prepare_elaboration(
        seed_count: int = 50,
        project: str | None = None,
        focus: str | None = None,
        focus_instructions: str | None = None,
    ) -> str:
        """Prepare working set for elaboration (the 'sleep' process).

        Args:
            seed_count: Number of seed memories (default 50).
            project: Filter by project.
            focus: Optional focus type for this elaboration round.
                   Values: "general", "typed_edges", "contradicts",
                   "supersedes", "connectivity", "quality".
                   When set, the working set JSON includes prioritized
                   instructions for the elaboration agent.
            focus_instructions: Optional free-text instructions from Claude
                   or diagnose() to guide elaboration. Complements the focus
                   type with specific context (e.g. current metric values,
                   what to look for).
        """
        seeds = await db.get_memories_for_elaboration(seed_count, project)
        if not seeds:
            return json.dumps({"error": "No memories to elaborate"})

        # Expand: for each seed, find top-5 by similarity + top-5 by graph
        all_memories = await db.get_all_memories(project=project, deprecated=False)
        all_edges = await db.get_all_edges([m.id for m in all_memories])

        seed_ids = {m.id for m in seeds}
        working_ids = set(seed_ids)

        all_embs = np.array([Embedder.bytes_to_embedding(m.embedding) for m in all_memories])
        id_to_idx = {m.id: i for i, m in enumerate(all_memories)}

        for seed in seeds:
            # Top 5 by cosine similarity
            seed_emb = Embedder.bytes_to_embedding(seed.embedding)
            sims = Embedder.cosine_similarity(seed_emb, all_embs)
            top_indices = np.argsort(sims)[-6:][::-1]  # top 6 (includes self)
            for idx in top_indices:
                working_ids.add(all_memories[idx].id)

            # Top 5 by graph (direct + 1 hop)
            neighbors = graph.get_neighbors(seed.id, all_edges, hops=1)
            for nid in neighbors[:5]:
                working_ids.add(nid)

        working_set = [m for m in all_memories if m.id in working_ids]
        ws_edges = [e for e in all_edges if e.from_id in working_ids and e.to_id in working_ids]

        # Create elaboration log (store seed_ids for apply_elaboration filtering)
        elab_id = str(uuid.uuid4())
        await db.insert_elaboration_log({
            "id": elab_id,
            "started_at": datetime.utcnow().isoformat(),
            "seed_count": len(seeds),
            "working_set": len(working_set),
            "seed_ids": json.dumps(list(seed_ids)),
            "status": "running",
        })

        total_tokens = sum(m.token_count for m in working_set)

        def mem_to_dict(m: Memory) -> dict:
            return {
                "id": m.id,
                "content": m.content,
                "type": m.type.value if hasattr(m.type, 'value') else m.type,
                "project": m.project,
                "tags": m.tags,
                "decay_score": m.decay_score,
                "access_count": m.access_count,
                "is_seed": m.id in seed_ids,
            }

        def edge_to_dict(e: Edge) -> dict:
            return {
                "id": e.id,
                "from_id": e.from_id,
                "to_id": e.to_id,
                "weight": e.weight,
                "type": e.type.value if hasattr(e.type, 'value') else e.type,
            }

        # Build focus block for elaboration agent
        focus_block = None
        if focus or focus_instructions:
            FOCUS_TEMPLATES = {
                "typed_edges": (
                    "PRIORITY: Edge type diversity is too low. Do NOT create new relates_to edges. "
                    "For every edge, choose the most specific type: depends_on (component→utility, "
                    "feature→config), caused_by (bug→decision, refactor→incident), contradicts "
                    "(conflicting info), supersedes (newer replaces older). Use relates_to ONLY "
                    "as last resort. Also review existing relates_to edges — convert them to more "
                    "specific types where the relationship is clearly directional or causal."
                ),
                "contradicts": (
                    "PRIORITY: Find contradictions. Look for memory pairs where the information "
                    "conflicts. Examples: old architecture decision vs new approach, deprecated "
                    "pattern vs current pattern, different claims about same feature. Create "
                    "contradicts edges (symmetric, negative in retrieval) between them. Target: "
                    "at least 5 contradicts edges this round."
                ),
                "supersedes": (
                    "PRIORITY: Find superseded pairs. Look for memories where a newer one clearly "
                    "replaces an older one, but BOTH are worth keeping. Don't deprecate the old one "
                    "— create a supersedes edge instead (A supersedes B means: finding B boosts A, "
                    "finding A pushes B down). Target: at least 5 supersedes edges this round."
                ),
                "connectivity": (
                    "PRIORITY: Connect isolated memories. Many memories in this working set have "
                    "0-1 edges. For EVERY memory with less than 3 edges, actively search the working "
                    "set for connections. Each memory should end up with at least 3 edges."
                ),
                "quality": (
                    "PRIORITY: Improve memory content quality. Focus on: rewriting vague memories "
                    "to be specific and self-contained, ensuring correct type classification, "
                    "adding missing file_path and code_signature where applicable, improving tags."
                ),
            }
            template = FOCUS_TEMPLATES.get(focus or "", "")
            focus_block = {
                "type": focus or "custom",
                "template_instructions": template,
                "custom_instructions": focus_instructions or "",
            }

        # Save full working set to file (too large for MCP inline result)
        from server.config import PROJECT_ROOT
        elaboration_dir = PROJECT_ROOT / "data" / "elaborations"
        elaboration_dir.mkdir(parents=True, exist_ok=True)
        working_set_file = elaboration_dir / f"{elab_id}.json"

        ws_data: dict[str, Any] = {
            "elaboration_id": elab_id,
            "seeds": [mem_to_dict(m) for m in seeds],
            "working_set": [mem_to_dict(m) for m in working_set],
            "edges": [edge_to_dict(e) for e in ws_edges],
            "total_tokens": total_tokens,
        }
        if focus_block:
            ws_data["focus"] = focus_block

        full_data = json.dumps(ws_data, ensure_ascii=False, indent=2)
        working_set_file.write_text(full_data, encoding="utf-8")

        return json.dumps({
            "elaboration_id": elab_id,
            "working_set_file": str(working_set_file),
            "seed_count": len(seeds),
            "working_set_count": len(working_set),
            "edge_count": len(ws_edges),
            "total_tokens": total_tokens,
        })

    # ── apply_elaboration ──────────────────────────────────────────────────

    async def _get_elab_count(memory_id: str) -> int:
        """Get current elaboration_count for a memory."""
        cur = await db.conn.execute(
            "SELECT elaboration_count FROM memories WHERE id=?", (memory_id,)
        )
        row = await cur.fetchone()
        return row[0] if row else 0

    @server.tool()
    async def apply_elaboration(
        elaboration_id: str,
        updates: dict[str, Any],
    ) -> str:
        """Apply elaboration results to the database.

        Args:
            elaboration_id: ID from prepare_elaboration.
            updates: Dict with these optional fields:
                - memories_to_update: [{id, new_content}]
                - memories_to_add: [{content, type, project, tags, relations, file_path, code_signature}]
                - memories_to_deprecate: [{id, reason, replaced_by?}]
                - edges_to_add: [{from_id, to_id, type, weight}] — type: relates_to|depends_on|caused_by|co_occurs|contradicts|supersedes
                - edges_to_update: [{id, new_weight?, new_type?}]
                - edges_to_remove: [edge_id_strings]
                - confirmed: [memory_id_strings] — IDs of memories reviewed but unchanged
        """
        eu = ElaborationUpdate(**updates)
        report = ElaborationReport()
        now = datetime.utcnow()

        # Retrieve seed_ids from elaboration log to filter elaboration marking
        logs = await db.get_elaboration_logs(limit=100)
        seed_ids: set[str] = set()
        for log in logs:
            if log.get("id") == elaboration_id and log.get("seed_ids"):
                seed_ids = set(json.loads(log["seed_ids"]))
                break

        # Update memories (content changes apply to all, elaboration marking only for seeds)
        for mu in eu.memories_to_update:
            emb = embedder.encode(mu.new_content)
            fields: dict[str, Any] = {
                "content": mu.new_content,
                "embedding": Embedder.embedding_to_bytes(emb),
                "token_count": count_tokens(mu.new_content),
            }
            if mu.id in seed_ids:
                fields["elaboration_date"] = now
                fields["elaboration_count"] = await _get_elab_count(mu.id) + 1
            await db.update_memory(mu.id, fields)
            report.updated_memories += 1

        # Add new memories (always marked as elaborated)
        for mi in eu.memories_to_add:
            emb = embedder.encode(mi.content)
            memory = Memory(
                content=mi.content,
                embedding=Embedder.embedding_to_bytes(emb),
                type=mi.type,
                project=mi.project,
                tags=mi.tags,
                token_count=count_tokens(mi.content),
                source=MemorySource.elaboration,
                elaboration_date=now,
                elaboration_count=1,
            )
            await db.insert_memory(memory)
            report.new_memories += 1

        # Deprecate (always mark — deprecation is definitive)
        for md in eu.memories_to_deprecate:
            fields = {"is_deprecated": True, "elaboration_date": now}
            if md.replaced_by:
                fields["deprecated_by"] = md.replaced_by
            await db.update_memory(md.id, fields)
            report.deprecated += 1

        # Add edges
        for ea in eu.edges_to_add:
            edge = Edge(
                from_id=ea.from_id,
                to_id=ea.to_id,
                weight=ea.weight,
                type=ea.type,
                source=MemorySource.elaboration,
            )
            await db.insert_edge(edge)
            report.new_edges += 1

        # Update edges
        for eup in eu.edges_to_update:
            fields: dict[str, Any] = {}
            if eup.new_weight is not None:
                fields["weight"] = eup.new_weight
            if eup.new_type is not None:
                fields["type"] = eup.new_type
            if fields:
                await db.update_edge(eup.id, fields)
                report.updated_edges += 1

        # Remove edges
        for eid in eu.edges_to_remove:
            await db.delete_edge(eid)
            report.removed_edges += 1

        # Confirm — only mark seeds as elaborated (neighbors are just context)
        for mid in eu.confirmed:
            if mid in seed_ids:
                await db.update_memory(mid, {
                    "elaboration_date": now,
                    "elaboration_count": await _get_elab_count(mid) + 1,
                })

        # Update elaboration log
        report.summary = (
            f"Updated {report.updated_memories}, added {report.new_memories}, "
            f"deprecated {report.deprecated}, "
            f"edges: +{report.new_edges} ~{report.updated_edges} -{report.removed_edges}"
        )
        await db.update_elaboration_log(elaboration_id, {
            "completed_at": now.isoformat(),
            "new_memories": report.new_memories,
            "updated_memories": report.updated_memories,
            "deprecated_memories": report.deprecated,
            "new_edges": report.new_edges,
            "updated_edges": report.updated_edges,
            "summary": report.summary,
            "status": "completed",
        })

        return json.dumps(report.model_dump())

    # ── reinforce ──────────────────────────────────────────────────────────

    @server.tool()
    async def reinforce(memory_ids: list[str]) -> str:
        """Signal that memories were useful — boost their scores.

        Args:
            memory_ids: List of memory IDs to reinforce.
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        now = datetime.utcnow()
        for mid in memory_ids:
            m = await db.get_memory(mid)
            if m:
                await db.update_memory(mid, {
                    "access_count": m.access_count + 1,
                    "last_accessed": now,
                    "decay_score": 1.0,
                })

        # Reinforce co_occurs edges between all pairs
        edges = await db.get_all_edges(memory_ids)
        id_set = set(memory_ids)
        for i, id1 in enumerate(memory_ids):
            for id2 in memory_ids[i + 1:]:
                existing = [
                    e for e in edges
                    if e.type == EdgeType.co_occurs
                    and {e.from_id, e.to_id} == {id1, id2}
                ]
                if existing:
                    e = existing[0]
                    await db.update_edge(e.id, {
                        "weight": min(e.weight + 0.1, 1.0),
                        "last_reinforced": now,
                        "reinforce_count": e.reinforce_count + 1,
                    })
                else:
                    edge = Edge(
                        from_id=id1, to_id=id2,
                        weight=0.2, type=EdgeType.co_occurs,
                        source=MemorySource.manual,
                    )
                    await db.insert_edge(edge)

        _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
        await _log_op(db, "reinforce", params={"count": len(memory_ids)},
                      result={"reinforced": len(memory_ids)}, duration_ms=_dur)
        return json.dumps({"reinforced": len(memory_ids)})

    # ── update_memory ────────────────────────────────────────────────────

    @server.tool()
    async def update_memory(
        memory_id: str,
        content: str | None = None,
        file_path: str | None = None,
        code_signature: str | None = None,
        tags: list[str] | None = None,
        memory_type: str | None = None,
        is_deprecated: bool | None = None,
        deprecated_by: str | None = None,
    ) -> str:
        """Update fields of an existing memory.

        Use this to fix stale file_path after renames, update content after
        code changes, correct tags, or deprecate obsolete memories.
        Only provided (non-null) fields are updated; others stay unchanged.

        Args:
            memory_id: ID of the memory to update.
            content: New content text (embedding is recomputed automatically).
            file_path: New file path (relative to project root). Pass empty string to clear.
            code_signature: New code signature. Pass empty string to clear.
            tags: New tags list (replaces existing tags entirely).
            memory_type: New type ("episodic", "semantic", "procedural").
            is_deprecated: Set True to deprecate, False to un-deprecate.
            deprecated_by: ID of the memory that replaces this one.
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        m = await db.get_memory(memory_id)
        if not m:
            return json.dumps({"error": f"Memory {memory_id} not found"})

        fields: dict[str, Any] = {}

        if content is not None:
            fields["content"] = content
            fields["token_count"] = count_tokens(content)
            emb = embedder.encode(content)
            fields["embedding"] = Embedder.embedding_to_bytes(emb)

        if file_path is not None:
            fields["file_path"] = file_path if file_path != "" else None

        if code_signature is not None:
            fields["code_signature"] = code_signature if code_signature != "" else None

        if tags is not None:
            fields["tags"] = tags

        if memory_type is not None:
            fields["type"] = MemoryType(memory_type)

        if is_deprecated is not None:
            fields["is_deprecated"] = is_deprecated

        if deprecated_by is not None:
            fields["deprecated_by"] = deprecated_by

        if not fields:
            return json.dumps({"error": "No fields to update"})

        await db.update_memory(memory_id, fields)

        _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
        _res = {"updated": memory_id, "fields_changed": list(fields.keys()), "project": m.project}
        await _log_op(db, "update_memory", project=m.project,
                      params={"memory_id": memory_id, "fields": list(fields.keys())},
                      result=_res, duration_ms=_dur)
        return json.dumps(_res)

    # ── decay ──────────────────────────────────────────────────────────────

    @server.tool()
    async def decay(dry_run: bool = False) -> str:
        """Apply temporal decay to all memories.

        Args:
            dry_run: If true, show what would happen without applying.
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        result = await DecayManager.apply_decay(db, dry_run=dry_run)
        _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
        await _log_op(db, "decay", params={"dry_run": dry_run},
                      result={"affected": result.get("affected", 0)}, duration_ms=_dur)
        return json.dumps(result)

    # ── stats ──────────────────────────────────────────────────────────────

    @server.tool()
    async def stats(project: str | None = None) -> str:
        """Get memory statistics.

        Args:
            project: Filter by project name. None = all projects.
        """
        all_mems = await db.get_all_memories(project=project, deprecated=False)
        all_mems_incl = await db.get_all_memories(project=project, deprecated=True)
        all_edges = await db.get_all_edges([m.id for m in all_mems_incl]) if all_mems_incl else []

        by_type: dict[str, int] = {}
        by_project: dict[str, int] = {}
        never_accessed = 0
        never_elaborated = 0
        oldest_unelab: Optional[datetime] = None

        for m in all_mems:
            t = m.type.value if hasattr(m.type, 'value') else m.type
            by_type[t] = by_type.get(t, 0) + 1
            p = m.project or "global"
            by_project[p] = by_project.get(p, 0) + 1
            if m.access_count == 0:
                never_accessed += 1
            if m.elaboration_date is None:
                never_elaborated += 1
                if oldest_unelab is None or m.created_at < oldest_unelab:
                    oldest_unelab = m.created_at

        # Last extraction/elaboration
        sessions = await db.get_sessions(project)
        last_extraction = sessions[0].extracted_at if sessions and sessions[0].extracted_at else None
        elab_logs = await db.get_elaboration_logs(1)
        last_elaboration = elab_logs[0].get("completed_at") if elab_logs else None

        n = len(all_mems)
        avg_conn = len(all_edges) * 2 / n if n > 0 else 0

        alerts: list[str] = []
        if never_elaborated > 0:
            alerts.append(f"{never_elaborated} memories never elaborated")
        if never_accessed > 50:
            alerts.append(f"{never_accessed} memories never accessed")

        result = {
            "total_memories": len(all_mems),
            "by_type": by_type,
            "by_project": by_project,
            "total_edges": len(all_edges),
            "avg_connections_per_memory": round(avg_conn, 2),
            "memories_never_accessed": never_accessed,
            "memories_never_elaborated": never_elaborated,
            "oldest_unelaborated": oldest_unelab.isoformat() if oldest_unelab else None,
            "last_extraction": last_extraction.isoformat() if isinstance(last_extraction, datetime) else last_extraction,
            "last_elaboration": last_elaboration,
            "health_alerts": alerts,
        }
        return json.dumps(result, indent=2)

    # ── diagnose ────────────────────────────────────────────────────────────

    @server.tool()
    async def diagnose(
        project: str | None = None,
        project_path: str | None = None,
    ) -> str:
        """Diagnose memory health and return prescriptions for improvement.

        Returns health score, structural prescriptions, and content gaps.
        Used by /health-check workflow.

        Args:
            project: Project to diagnose (e.g. "myproject"). None = all.
            project_path: Root path of the project codebase. If provided,
                scans filesystem to detect content gaps accurately.
        """
        from server.api_routes import diagnose_impl_standalone
        result = await diagnose_impl_standalone(db, project=project, project_path=project_path)
        return json.dumps(result, indent=2)

    # ── list_memories ──────────────────────────────────────────────────────

    @server.tool()
    async def list_memories(
        project: str | None = None,
        type: str | None = None,
        search: str | None = None,
        tags: list[str] | None = None,
        deprecated: bool = False,
        sort: str = "created",
        limit: int = 50,
        offset: int = 0,
    ) -> str:
        """List and search memories.

        Args:
            project: Filter by project.
            type: Filter by type (episodic/semantic/procedural).
            search: Text search in content.
            tags: Filter by tags.
            deprecated: Include deprecated memories.
            sort: Sort by "created", "accessed", or "decay".
            limit: Max results (default 50).
            offset: Pagination offset.
        """
        mem_type = MemoryType(type) if type else None
        memories, total = await db.search_memories(
            search=search, project=project, type=mem_type,
            tags=tags, deprecated=deprecated, sort=sort,
            limit=limit, offset=offset,
        )
        return json.dumps({
            "memories": [
                {
                    "id": m.id,
                    "content": m.content,
                    "type": m.type.value if hasattr(m.type, 'value') else m.type,
                    "project": m.project,
                    "tags": m.tags,
                    "decay_score": m.decay_score,
                    "access_count": m.access_count,
                    "created_at": m.created_at.isoformat() if isinstance(m.created_at, datetime) else m.created_at,
                    "file_path": m.file_path,
                    "code_signature": m.code_signature,
                }
                for m in memories
            ],
            "total": total,
        }, indent=2)

    # ── init_project ────────────────────────────────────────────────────────

    @server.tool()
    async def init_project(
        project: str,
        project_path: str,
    ) -> str:
        """Gather all data sources for project initialization.

        Returns raw content of rules files, project memory path, and session list.
        The LLM session performs the intelligent extraction — this tool only prepares data.

        Args:
            project: Project name (e.g. "myproject").
            project_path: Root path of the project.
        """
        from server.jsonl_parser import find_all_sessions

        root = Path(project_path)
        report: dict[str, Any] = {
            "project": project,
            "project_path": project_path,
            "rules_files": [],
            "project_memory_path": None,
            "sessions": [],
        }

        # ── Gather rules files (paths only — agent reads content separately) ──
        # Check both root/CLAUDE.md and .claude/CLAUDE.md
        for claude_md_path in [root / "CLAUDE.md", root / ".claude" / "CLAUDE.md"]:
            if claude_md_path.exists():
                report["rules_files"].append({
                    "filename": claude_md_path.name,
                    "path": str(claude_md_path),
                    "size_bytes": claude_md_path.stat().st_size,
                })

        rules_dir = root / ".claude" / "rules"
        if rules_dir.exists():
            for f in sorted(rules_dir.iterdir()):
                if f.is_file() and f.suffix in (".md", ".txt"):
                    report["rules_files"].append({
                        "filename": f.name,
                        "path": str(f),
                        "size_bytes": f.stat().st_size,
                    })

        # ── Find PROJECT_MEMORY.jsonl ─────────────────────────────────
        pm_jsonl = root / "PROJECT_MEMORY.jsonl"
        if pm_jsonl.exists():
            report["project_memory_path"] = str(pm_jsonl)
            report["project_memory_lines"] = sum(1 for _ in open(pm_jsonl, encoding="utf-8"))

        # ── List sessions (newest first, with stats) ──────────────────
        session_paths = find_all_sessions(project)
        # Reverse to newest-first for selection
        session_paths.reverse()
        for sp in session_paths[:30]:  # Cap at 30 for response size
            try:
                stat = Path(sp).stat()
                report["sessions"].append({
                    "path": sp,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except Exception:
                pass

        report["total_sessions_found"] = len(session_paths)

        return json.dumps(report, indent=2)

    # ── read_project_memory ──────────────────────────────────────────────

    @server.tool()
    async def read_project_memory(
        path: str,
        offset: int = 0,
        limit: int = 50,
    ) -> str:
        """Read entries from a PROJECT_MEMORY.jsonl file.

        Returns parsed entries as JSON array. Use offset/limit for pagination.

        Args:
            path: Path to the PROJECT_MEMORY.jsonl file.
            offset: Skip first N entries (default 0).
            limit: Max entries to return (default 50).
        """
        entries = []
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i < offset:
                    continue
                if len(entries) >= limit:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

        total = sum(1 for _ in open(path, encoding="utf-8"))
        return json.dumps({
            "entries": entries,
            "offset": offset,
            "limit": limit,
            "total": total,
            "has_more": offset + limit < total,
        }, indent=2)

    # ── sync_codebase ─────────────────────────────────────────────────

    @server.tool()
    async def sync_codebase(
        changed_files: list[str],
        project: str,
        project_path: str | None = None,
    ) -> str:
        """Compare changed files against existing reference memories.

        Args:
            changed_files: List of file paths (relative to project root) that were modified.
            project: Project name.
            project_path: Absolute path to project root (for orphan detection).

        Returns report with:
            - stale_memories: memories whose file_path matches a changed file
            - orphan_memories: memories whose file_path no longer exists
            - new_files: changed files with no existing memory
        """
        import time as _time
        _t0 = _time.monotonic_ns()
        # 1. Get all memories with file_path for this project
        all_mems = await db.get_all_memories(project=project, deprecated=False)
        ref_mems = [m for m in all_mems if m.file_path]

        # 2. Build lookup: file_path → [memories]
        path_to_mems: dict[str, list] = {}
        for m in ref_mems:
            norm_path = m.file_path.replace("\\", "/")
            path_to_mems.setdefault(norm_path, []).append(m)

        # 3. Classify changed files
        stale = []
        new_files = []

        for fp in changed_files:
            fp_norm = fp.replace("\\", "/")
            if fp_norm in path_to_mems:
                for m in path_to_mems[fp_norm]:
                    stale.append({
                        "memory_id": m.id,
                        "memory_content": m.content,
                        "file_path": m.file_path,
                        "code_signature": m.code_signature,
                        "issue": "file_modified",
                    })
            else:
                new_files.append(fp_norm)

        # 4. Check for orphan memories (file_path doesn't exist anymore)
        orphans = []
        if project_path:
            root = Path(project_path)
            for m in ref_mems:
                if m.file_path and not (root / m.file_path).exists():
                    orphans.append({
                        "memory_id": m.id,
                        "memory_content": m.content,
                        "file_path": m.file_path,
                        "issue": "file_deleted_or_renamed",
                    })

        _dur = int((_time.monotonic_ns() - _t0) / 1_000_000)
        _res_summary = f"{len(stale)} stale, {len(orphans)} orphans, {len(new_files)} new files"
        await _log_op(db, "sync_codebase", project=project,
                      params={"changed_files": changed_files},
                      result={"stale": len(stale), "orphans": len(orphans), "new_files": len(new_files)},
                      duration_ms=_dur)
        return json.dumps({
            "stale_memories": stale,
            "orphan_memories": orphans,
            "new_files_without_memory": new_files,
            "summary": _res_summary,
        }, indent=2)

    # ── diagnose ──────────────────────────────────────────────────────

    @server.tool()
    async def diagnose(project: str | None = None) -> str:
        """Analyze memory health and return actionable prescriptions.

        Returns a structured diagnosis with specific actions to improve
        each suboptimal metric. Use this before running elaboration to
        know what focus to apply, or to show the user what needs attention.

        Args:
            project: Filter by project name. None = all projects.
        """
        memories = await db.get_all_memories(project=project, deprecated=False)
        all_edges_list = await db.get_all_edges([m.id for m in memories])

        n = len(memories)
        if n == 0:
            return json.dumps({"error": "No memories found", "prescriptions": []})

        # ── Compute metrics ──────────────────────────────────────────
        # Degree per memory
        degree: dict[str, int] = {m.id: 0 for m in memories}
        for e in all_edges_list:
            if e.from_id in degree:
                degree[e.from_id] += 1
            if e.to_id in degree:
                degree[e.to_id] += 1
        degrees = list(degree.values())

        # Edge types
        edge_types: dict[str, int] = {}
        for e in all_edges_list:
            et = e.type.value if hasattr(e.type, "value") else e.type
            edge_types[et] = edge_types.get(et, 0) + 1
        total_edges = len(all_edges_list)
        relates_to_count = edge_types.get("relates_to", 0)
        typed_ratio = 1 - (relates_to_count / total_edges) if total_edges > 0 else 0
        has_contradicts = edge_types.get("contradicts", 0) > 0
        has_supersedes = edge_types.get("supersedes", 0) > 0

        # Connectivity
        well_connected_pct = sum(1 for d in degrees if d >= 3) / n if n else 0
        under_connected = sum(1 for d in degrees if d <= 1)
        hubs = sum(1 for d in degrees if d >= 10)

        # Components (BFS)
        adj: dict[str, set[str]] = {m.id: set() for m in memories}
        for e in all_edges_list:
            if e.from_id in adj and e.to_id in adj:
                adj[e.from_id].add(e.to_id)
                adj[e.to_id].add(e.from_id)
        visited: set[str] = set()
        components: list[int] = []
        for mid in adj:
            if mid not in visited:
                queue = [mid]
                size = 0
                while queue:
                    node = queue.pop(0)
                    if node in visited:
                        continue
                    visited.add(node)
                    size += 1
                    queue.extend(adj[node] - visited)
                components.append(size)
        components.sort(reverse=True)
        largest_pct = components[0] / n if components and n else 0

        # Access Gini
        access_counts = sorted([m.access_count for m in memories])
        total_access = sum(access_counts)
        if total_access > 0:
            cumulative = 0
            gini_sum = 0
            for a_val in access_counts:
                cumulative += a_val
                gini_sum += cumulative
            gini = 1 - (2 * gini_sum) / (n * total_access) + 1 / n
            gini = min(max(gini, 0), 1)
        else:
            gini = 0.0
        access_balance = 1 - gini
        never_accessed = sum(1 for m in memories if m.access_count == 0)
        never_accessed_pct = never_accessed / n * 100 if n else 0

        # Elaboration
        elab_counts = [m.elaboration_count for m in memories]
        avg_elab = sum(elab_counts) / n if n else 0

        # Maturity
        if n < 50:
            maturity = "new"
        elif n < 200:
            maturity = "growing"
        elif n < 500:
            maturity = "mature"
        else:
            maturity = "large"

        # ── Build prescriptions ──────────────────────────────────────
        prescriptions: list[dict[str, Any]] = []

        # Adaptive thresholds by maturity
        targets = {
            "new":     {"edge_div": (0.15, 0.60), "access": (0.20, 0.65), "conn": (0.50, 1.0), "unity": (0.80, 1.0), "elab": (1.0, 4.0), "never_acc": 60, "hubs_pct": 0.10},
            "growing": {"edge_div": (0.25, 0.60), "access": (0.30, 0.65), "conn": (0.70, 1.0), "unity": (0.90, 1.0), "elab": (1.5, 4.0), "never_acc": 40, "hubs_pct": 0.07},
            "mature":  {"edge_div": (0.30, 0.60), "access": (0.35, 0.65), "conn": (0.80, 1.0), "unity": (0.95, 1.0), "elab": (2.0, 4.0), "never_acc": 30, "hubs_pct": 0.05},
            "large":   {"edge_div": (0.35, 0.60), "access": (0.35, 0.65), "conn": (0.85, 1.0), "unity": (0.95, 1.0), "elab": (2.0, 4.0), "never_acc": 25, "hubs_pct": 0.04},
        }
        t = targets[maturity]

        # 1. Edge diversity
        if typed_ratio < t["edge_div"][0]:
            prescriptions.append({
                "metric": "edge_diversity",
                "current": round(typed_ratio, 3),
                "target": list(t["edge_div"]),
                "severity": "warning",
                "diagnosis": f"{relates_to_count}/{total_edges} edges are generic relates_to ({round((1-typed_ratio)*100)}%). Graph lacks structural semantics.",
                "action": "elaborate",
                "focus": "typed_edges",
                "focus_instructions": f"Edge diversity is {round(typed_ratio*100)}%. The graph has {relates_to_count} relates_to out of {total_edges} total. Focus on converting relates_to to depends_on or caused_by where the relationship is clearly directional. Also look for contradictions and superseded pairs.",
                "expected_improvement": "+5-10% per elaboration round",
                "rounds": 2,
            })

        # 2. No contradicts
        if not has_contradicts and maturity in ("mature", "large"):
            prescriptions.append({
                "metric": "contradicts_edges",
                "current": 0,
                "target": [1, None],
                "severity": "warning" if maturity == "large" else "info",
                "diagnosis": "No contradicts edges. Conflicting information is not marked, which means retrieval cannot push down outdated or wrong memories.",
                "action": "elaborate",
                "focus": "contradicts",
                "focus_instructions": f"There are {n} memories and 0 contradicts edges. Look for pairs where the information conflicts: old architecture decisions vs new, deprecated patterns vs current patterns, different claims about the same feature or file.",
                "expected_improvement": "5-15 contradicts edges per round",
                "rounds": 1,
            })

        # 3. No supersedes
        if not has_supersedes and maturity in ("mature", "large"):
            prescriptions.append({
                "metric": "supersedes_edges",
                "current": 0,
                "target": [1, None],
                "severity": "info",
                "diagnosis": "No supersedes edges. Older memories are not versioned — retrieval treats old and new equally even when one clearly replaces the other.",
                "action": "elaborate",
                "focus": "supersedes",
                "focus_instructions": f"There are {n} memories and 0 supersedes edges. Look for pairs where a newer memory clearly replaces an older one but both are worth keeping for context. Create supersedes edges (A supersedes B) instead of deprecating.",
                "expected_improvement": "5-20 supersedes edges per round",
                "rounds": 1,
            })

        # 4. Access balance
        if access_balance < t["access"][0]:
            prescriptions.append({
                "metric": "access_balance",
                "current": round(access_balance, 3),
                "target": list(t["access"]),
                "severity": "warning",
                "diagnosis": f"Gini coefficient {gini:.3f} — retrieval is heavily biased toward a few memories. {never_accessed} memories ({never_accessed_pct:.0f}%) never accessed.",
                "action": "decay_and_investigate",
                "focus": None,
                "focus_instructions": f"Access Gini is {gini:.3f}. {never_accessed} memories never accessed. This improves with: (1) running decay to penalize over-accessed, (2) better graph connectivity so propagation reaches more memories, (3) using multi-query strategy (1 deep + N quick) instead of single broad queries. Run decay(project='{project or ''}') and investigate the top accessed memories with list_memories(sort='accessed', limit=15) to check if they are too generic.",
                "expected_improvement": "Gradual — Gini decreases ~0.05 per month of active use",
                "rounds": 0,
            })

        # 5. Graph connectivity
        if well_connected_pct < t["conn"][0]:
            prescriptions.append({
                "metric": "graph_connectivity",
                "current": round(well_connected_pct, 3),
                "target": list(t["conn"]),
                "severity": "warning" if well_connected_pct < 0.5 else "info",
                "diagnosis": f"{under_connected} memories have 0-1 edges. Only {round(well_connected_pct*100)}% have 3+ edges.",
                "action": "elaborate",
                "focus": "connectivity",
                "focus_instructions": f"{under_connected} memories have 0-1 edges out of {n} total. The seed selection already prioritizes these. Run a standard elaboration round — the under-connected memories will be selected as seeds automatically.",
                "expected_improvement": "-30-50% under-connected per round",
                "rounds": 1,
            })

        # 6. Component unity
        if largest_pct < t["unity"][0]:
            prescriptions.append({
                "metric": "component_unity",
                "current": round(largest_pct, 3),
                "target": list(t["unity"]),
                "severity": "warning",
                "diagnosis": f"{len(components)} disconnected components. Largest covers {round(largest_pct*100, 1)}% of memories.",
                "action": "elaborate",
                "focus": "connectivity",
                "focus_instructions": f"There are {len(components)} disconnected components in the graph. Isolated memories cannot be found via graph propagation. Elaboration with connectivity focus will bridge them.",
                "expected_improvement": "Should reach 1 component after 1-2 rounds",
                "rounds": 1,
            })

        # 7. Elaboration depth
        if avg_elab < t["elab"][0]:
            prescriptions.append({
                "metric": "elaboration_depth",
                "current": round(avg_elab, 2),
                "target": list(t["elab"]),
                "severity": "info",
                "diagnosis": f"Average elaboration count is {avg_elab:.1f}×. Memories need more curation passes.",
                "action": "elaborate",
                "focus": "general",
                "focus_instructions": f"Average elaboration is {avg_elab:.1f}× (target: {t['elab'][0]}-{t['elab'][1]}×). Run standard elaboration rounds to increase coverage.",
                "expected_improvement": "+0.3-0.5 avg per round",
                "rounds": max(1, int((t["elab"][0] - avg_elab) / 0.4)),
            })

        # 8. Never accessed
        if never_accessed_pct > t["never_acc"]:
            prescriptions.append({
                "metric": "never_accessed",
                "current": round(never_accessed_pct, 1),
                "target": [0, t["never_acc"]],
                "severity": "info",
                "diagnosis": f"{never_accessed} memories ({never_accessed_pct:.0f}%) never retrieved. Some may be unreachable due to poor connectivity or niche content.",
                "action": "investigate",
                "focus": None,
                "focus_instructions": f"{never_accessed_pct:.0f}% of memories never accessed. This improves naturally with use. To accelerate: improve graph connectivity (more edges = better propagation), and review never-accessed memories for possible deprecation. Use list_memories(sort='accessed', limit=50) to inspect.",
                "expected_improvement": "Decreases with active use — target reachable in 2-4 weeks",
                "rounds": 0,
            })

        # 9. Hubs
        hubs_pct = hubs / n if n else 0
        if hubs_pct > t["hubs_pct"]:
            prescriptions.append({
                "metric": "hubs",
                "current": hubs,
                "target": [0, int(n * t["hubs_pct"])],
                "severity": "info",
                "diagnosis": f"{hubs} memories have 10+ edges ({round(hubs_pct*100, 1)}% of total). These may dominate retrieval results (noise floor).",
                "action": "investigate",
                "focus": None,
                "focus_instructions": f"{hubs} hub memories detected. Investigate: are they genuinely central (architecture overview, core patterns) or too generic? Use list_memories to find them, then consider splitting generic ones into specific memories or pruning weak edges.",
                "expected_improvement": "Requires manual review",
                "rounds": 0,
            })

        # Sort prescriptions by severity (warning first) then by actionability
        severity_order = {"warning": 0, "info": 1}
        prescriptions.sort(key=lambda p: (severity_order.get(p["severity"], 2), p.get("rounds", 0) == 0))

        # Determine next recommended action
        elaborate_prescriptions = [p for p in prescriptions if p["action"] == "elaborate"]
        next_action = None
        if elaborate_prescriptions:
            top = elaborate_prescriptions[0]
            next_action = {
                "action": "elaborate",
                "focus": top["focus"],
                "focus_instructions": top["focus_instructions"],
                "reason": top["diagnosis"],
            }
        elif any(p["action"] == "decay_and_investigate" for p in prescriptions):
            next_action = {
                "action": "decay",
                "focus": None,
                "focus_instructions": "Run decay() to apply time-based score reduction, then investigate over-accessed memories.",
                "reason": "Access distribution is imbalanced",
            }

        # Health score (same formula as API)
        health = round(
            well_connected_pct * 0.25
            + typed_ratio * 0.20
            + min(avg_elab / 2, 1.0) * 0.20
            + access_balance * 0.15
            + largest_pct * 0.20,
            3
        )

        return json.dumps({
            "health_score": health,
            "maturity": maturity,
            "total_memories": n,
            "total_edges": total_edges,
            "prescriptions": prescriptions,
            "next_action": next_action,
            "metrics": {
                "edge_diversity": round(typed_ratio, 3),
                "graph_connectivity": round(well_connected_pct, 3),
                "access_balance": round(access_balance, 3),
                "elaboration_depth": round(avg_elab, 2),
                "component_unity": round(largest_pct, 3),
                "gini": round(gini, 3),
                "never_accessed_pct": round(never_accessed_pct, 1),
                "hubs": hubs,
                "has_contradicts": has_contradicts,
                "has_supersedes": has_supersedes,
            },
        }, indent=2)

    # ── setup_status ───────────────────────────────────────────────────

    @server.tool()
    async def setup_status(
        project: str,
        action: str = "get",
        phase: str | None = None,
        step: str | None = None,
        status: str | None = None,
        result: str | dict | None = None,
    ) -> str:
        """Get or update setup progress for a project.

        Args:
            project: Project name.
            action: "get" for status, "update" to change a step, "init" to initialize.
            phase: Phase name (required for action="update").
            step: Step name (required for action="update").
            status: New status: pending, in_progress, completed, skipped, failed.
            result: JSON string with step results/metrics. If a dict is passed, it will be auto-serialized.
        """
        # Auto-serialize dict result to JSON string
        if result is not None and not isinstance(result, str):
            result = json.dumps(result)

        if action == "init":
            count = await db.init_setup_progress(project)
            summary = await db.get_setup_summary(project)
            return json.dumps({
                "action": "init",
                "steps_created": count,
                **summary,
            }, indent=2)

        elif action == "update":
            if not phase or not step:
                return json.dumps({"error": "phase and step are required for action=update"})
            fields: dict[str, Any] = {}
            if status:
                fields["status"] = status
                if status == "in_progress":
                    fields["started_at"] = datetime.utcnow()
                elif status in ("completed", "skipped"):
                    fields["completed_at"] = datetime.utcnow()
            if result:
                fields["result"] = result
            await db.update_setup_step(project, phase, step, fields)

            # Auto-complete ready step if all others done
            if phase != "ready":
                all_steps = await db.get_setup_progress(project)
                non_ready = [s for s in all_steps if s.phase != "ready"]
                if all(s.status.value in ("completed", "skipped") for s in non_ready):
                    await db.update_setup_step(project, "ready", "memory_ready", {
                        "status": "completed",
                        "completed_at": datetime.utcnow(),
                    })

            summary = await db.get_setup_summary(project)
            return json.dumps({"action": "update", **summary}, indent=2)

        else:  # get
            summary = await db.get_setup_summary(project)
            if not summary.get("initialized"):
                return json.dumps({
                    "project": project,
                    "initialized": False,
                    "message": f"Project not initialized. Use setup_status(project='{project}', action='init') first.",
                })
            steps = await db.get_setup_progress(project)
            steps_data = [
                {
                    "phase": s.phase,
                    "step": s.step,
                    "order": s.order_index,
                    "title": s.title,
                    "status": s.status.value,
                    "prompt_file": s.prompt_file,
                }
                for s in steps
            ]
            return json.dumps({**summary, "steps": steps_data}, indent=2)
