"""MangoBrain — REST API routes for dashboard (Fase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from server.database import Database
from server.models import MemoryType


def _memory_to_dict(m) -> dict:
    """Convert a Memory model to a JSON-safe dict (exclude embedding bytes)."""
    d = m.model_dump()
    d.pop("embedding", None)
    # Serialize datetimes
    for k in ("created_at", "last_accessed", "elaboration_date"):
        if d.get(k) and isinstance(d[k], datetime):
            d[k] = d[k].isoformat()
    if d.get("source"):
        d["source"] = d["source"].value if hasattr(d["source"], "value") else d["source"]
    if d.get("type"):
        d["type"] = d["type"].value if hasattr(d["type"], "value") else d["type"]
    return d


def _edge_to_dict(e) -> dict:
    d = e.model_dump()
    for k in ("created_at", "last_reinforced"):
        if d.get(k) and isinstance(d[k], datetime):
            d[k] = d[k].isoformat()
    if d.get("type"):
        d["type"] = d["type"].value if hasattr(d["type"], "value") else d["type"]
    if d.get("source"):
        d["source"] = d["source"].value if hasattr(d["source"], "value") else d["source"]
    return d


def _session_to_dict(s) -> dict:
    d = s.model_dump()
    for k in ("started_at", "extracted_at"):
        if d.get(k) and isinstance(d[k], datetime):
            d[k] = d[k].isoformat()
    if d.get("run_type"):
        d["run_type"] = d["run_type"].value if hasattr(d["run_type"], "value") else d["run_type"]
    return d


async def diagnose_impl_standalone(db: Database, project: Optional[str] = None, project_path: Optional[str] = None) -> dict:
    """Compute health diagnosis with prescriptions — standalone version.

    Can be called from both the API router and the MCP tool.

    Args:
        db: Database instance.
        project: Filter by project name.
        project_path: Root path of the project codebase. If provided, scans
            the filesystem to detect content gaps (modules with no memory coverage).
    """
    memories = await db.get_all_memories(project=project, deprecated=False)
    all_edges_raw = await db.get_edges()
    if project:
        mem_ids = {m.id for m in memories}
        all_edges_list = [e for e in all_edges_raw if e.from_id in mem_ids or e.to_id in mem_ids]
    else:
        all_edges_list = all_edges_raw

    n = len(memories)
    if n == 0:
        return {"error": "No memories", "prescriptions": [], "content_gaps": [], "health_score": 0, "maturity": "new", "metrics": {}}

    # Degree
    degree: dict[str, int] = {m.id: 0 for m in memories}
    for e in all_edges_list:
        if e.from_id in degree: degree[e.from_id] += 1
        if e.to_id in degree: degree[e.to_id] += 1
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

    well_connected_pct = sum(1 for d in degrees if d >= 3) / n if n else 0
    under_connected = sum(1 for d in degrees if d <= 1)
    hubs = sum(1 for d in degrees if d >= 10)

    # Components
    adj: dict[str, set] = {m.id: set() for m in memories}
    for e in all_edges_list:
        if e.from_id in adj and e.to_id in adj:
            adj[e.from_id].add(e.to_id)
            adj[e.to_id].add(e.from_id)
    visited: set = set()
    components: list[int] = []
    for mid in adj:
        if mid not in visited:
            queue = [mid]
            size = 0
            while queue:
                node = queue.pop(0)
                if node in visited: continue
                visited.add(node)
                size += 1
                queue.extend(adj[node] - visited)
            components.append(size)
    components.sort(reverse=True)
    largest_pct = components[0] / n if components and n else 0

    # Gini
    access_counts = sorted([m.access_count for m in memories])
    total_access = sum(access_counts)
    if total_access > 0:
        cumulative = gini_sum = 0
        for a_val in access_counts:
            cumulative += a_val
            gini_sum += cumulative
        gini = min(max(1 - (2 * gini_sum) / (n * total_access) + 1 / n, 0), 1)
    else:
        gini = 0.0
    access_balance = 1 - gini
    never_accessed = sum(1 for m in memories if m.access_count == 0)
    never_accessed_pct = never_accessed / n * 100 if n else 0

    elab_counts = [m.elaboration_count for m in memories]
    avg_elab = sum(elab_counts) / n if n else 0

    maturity = "new" if n < 50 else "growing" if n < 200 else "mature" if n < 500 else "large"

    # Targets by maturity
    targets = {
        "new":     {"edge_div": (0.15, 0.60), "access": (0.20, 0.65), "conn": (0.50, 1.0), "unity": (0.80, 1.0), "elab": (1.0, 4.0), "never_acc": 60, "hubs_pct": 0.10},
        "growing": {"edge_div": (0.25, 0.60), "access": (0.30, 0.65), "conn": (0.70, 1.0), "unity": (0.90, 1.0), "elab": (1.5, 4.0), "never_acc": 40, "hubs_pct": 0.07},
        "mature":  {"edge_div": (0.30, 0.60), "access": (0.35, 0.65), "conn": (0.80, 1.0), "unity": (0.95, 1.0), "elab": (2.0, 4.0), "never_acc": 30, "hubs_pct": 0.05},
        "large":   {"edge_div": (0.35, 0.60), "access": (0.35, 0.65), "conn": (0.85, 1.0), "unity": (0.95, 1.0), "elab": (2.0, 4.0), "never_acc": 25, "hubs_pct": 0.04},
    }
    t = targets[maturity]

    prescriptions = []

    def _in_lower_third(current: float, low: float, high: float) -> bool:
        if current < low:
            return False
        third = low + (high - low) / 3
        return current < third

    # ── Edge diversity ───────────────────────────────────────
    ed_low, ed_high = t["edge_div"]
    if typed_ratio < ed_low:
        prescriptions.append({
            "metric": "edge_diversity", "current": round(typed_ratio, 3), "target": list(t["edge_div"]),
            "severity": "warning",
            "diagnosis": f"{relates_to_count}/{total_edges} edges are generic relates_to ({round((1-typed_ratio)*100)}%). Graph propagation boosts everything equally — no directionality, no penalties.",
            "why_it_matters": "Typed edges change how retrieval works: depends_on is directional (A pulls in B, not vice versa), contradicts is negative (A pushes B down), supersedes penalizes the old version. Without these, the graph is just 'everything connected to everything' with no intelligence.",
            "action": "elaborate", "focus": "typed_edges",
            "expected_improvement": "+5-10% per round", "rounds": 2,
        })
    elif _in_lower_third(typed_ratio, ed_low, ed_high):
        prescriptions.append({
            "metric": "edge_diversity", "current": round(typed_ratio, 3), "target": list(t["edge_div"]),
            "severity": "optimize",
            "diagnosis": f"Edge diversity {round(typed_ratio*100)}% — inside target but still in the low zone. {relates_to_count}/{total_edges} edges are relates_to. More typed edges would improve retrieval precision.",
            "why_it_matters": "Each additional typed edge (depends_on, caused_by, contradicts, supersedes) adds directional intelligence to the graph. At current levels, most propagation is still undirected.",
            "action": "elaborate", "focus": "typed_edges",
            "expected_improvement": "+5-10% per round", "rounds": 1,
        })

    # ── Contradicts ──────────────────────────────────────────
    contradicts_count = edge_types.get("contradicts", 0)
    if not has_contradicts and maturity in ("mature", "large"):
        prescriptions.append({
            "metric": "contradicts_edges", "current": 0, "target": [1, None],
            "severity": "warning" if maturity == "large" else "info",
            "diagnosis": "No contradicts edges. Conflicting information is not marked — retrieval may return outdated info alongside current with equal relevance.",
            "why_it_matters": "Contradicts edges are negative in the retrieval matrix: when memory A is relevant, contradicting memory B gets pushed DOWN. Without them, old wrong decisions and new correct ones appear side by side.",
            "action": "elaborate", "focus": "contradicts",
            "expected_improvement": "5-15 contradicts per round", "rounds": 1,
        })
    elif has_contradicts and contradicts_count < 5 and maturity in ("mature", "large"):
        prescriptions.append({
            "metric": "contradicts_edges", "current": contradicts_count, "target": [5, None],
            "severity": "optimize",
            "diagnosis": f"Only {contradicts_count} contradicts edge(s). With {n} memories there are likely more conflicts to mark.",
            "why_it_matters": "More contradicts edges = better at suppressing outdated or wrong information during retrieval.",
            "action": "elaborate", "focus": "contradicts",
            "expected_improvement": "+3-8 contradicts per round", "rounds": 1,
        })

    # ── Supersedes ───────────────────────────────────────────
    supersedes_count = edge_types.get("supersedes", 0)
    if not has_supersedes and maturity in ("mature", "large"):
        prescriptions.append({
            "metric": "supersedes_edges", "current": 0, "target": [1, None],
            "severity": "info",
            "diagnosis": "No supersedes edges. Old and new versions of the same knowledge compete equally in retrieval.",
            "why_it_matters": "Supersedes edges are asymmetric: finding the old version boosts the new one, finding the new one suppresses the old. Enables graceful version transitions.",
            "action": "elaborate", "focus": "supersedes",
            "expected_improvement": "5-20 supersedes per round", "rounds": 1,
        })
    elif has_supersedes and supersedes_count < 5 and maturity in ("mature", "large"):
        prescriptions.append({
            "metric": "supersedes_edges", "current": supersedes_count, "target": [5, None],
            "severity": "optimize",
            "diagnosis": f"Only {supersedes_count} supersedes edge(s). With {n} memories spanning multiple development phases, there should be more version chains.",
            "why_it_matters": "More supersedes edges = retrieval naturally prefers current information over outdated.",
            "action": "elaborate", "focus": "supersedes",
            "expected_improvement": "+3-10 supersedes per round", "rounds": 1,
        })

    # ── Access balance ───────────────────────────────────────
    ac_low, ac_high = t["access"]
    if access_balance < ac_low:
        prescriptions.append({
            "metric": "access_balance", "current": round(access_balance, 3), "target": list(t["access"]),
            "severity": "warning",
            "diagnosis": f"Gini {gini:.3f} — retrieval heavily biased. {never_accessed} memories ({never_accessed_pct:.0f}%) never accessed.",
            "why_it_matters": "High Gini means the same memories appear in every query (noise floor). Root causes: generic embeddings, sparse graph, single broad queries instead of targeted multi-query.",
            "action": "improve_graph_and_queries",
            "focus": None,
            "expected_improvement": "Improves with: denser graph, typed edges, multi-query strategy.",
            "rounds": 0,
        })
    elif _in_lower_third(access_balance, ac_low, ac_high):
        prescriptions.append({
            "metric": "access_balance", "current": round(access_balance, 3), "target": list(t["access"]),
            "severity": "optimize",
            "diagnosis": f"Gini {gini:.3f} — access is moderately biased. {never_accessed} memories ({never_accessed_pct:.0f}%) still never accessed.",
            "why_it_matters": "Improving graph density and using multi-query remember strategy will continue to distribute access more evenly.",
            "action": "improve_graph_and_queries",
            "focus": None,
            "expected_improvement": "Gradual improvement with use and graph enrichment.",
            "rounds": 0,
        })

    # ── Graph connectivity ───────────────────────────────────
    cn_low, cn_high = t["conn"]
    if well_connected_pct < cn_low:
        prescriptions.append({
            "metric": "graph_connectivity", "current": round(well_connected_pct, 3), "target": list(t["conn"]),
            "severity": "warning" if well_connected_pct < 0.5 else "info",
            "diagnosis": f"{under_connected} memories have 0-1 edges. Only reachable by direct cosine similarity.",
            "why_it_matters": "Graph propagation finds semantically distant but structurally related memories. Memories with 0-1 edges are invisible to this mechanism.",
            "action": "elaborate", "focus": "connectivity",
            "expected_improvement": "-30-50% under-connected per round", "rounds": 1,
        })
    elif _in_lower_third(well_connected_pct, cn_low, cn_high) and under_connected > 0:
        prescriptions.append({
            "metric": "graph_connectivity", "current": round(well_connected_pct, 3), "target": list(t["conn"]),
            "severity": "optimize",
            "diagnosis": f"{under_connected} memories still have 0-1 edges. Connectivity is in target but can improve.",
            "why_it_matters": "Every memory connected with 3+ edges participates fully in graph propagation, improving retrieval reach.",
            "action": "elaborate", "focus": "connectivity",
            "expected_improvement": "-30-50% under-connected per round", "rounds": 1,
        })

    # ── Component unity ──────────────────────────────────────
    if largest_pct < t["unity"][0]:
        prescriptions.append({
            "metric": "component_unity", "current": round(largest_pct, 3), "target": list(t["unity"]),
            "severity": "warning",
            "diagnosis": f"{len(components)} disconnected components.",
            "action": "elaborate", "focus": "connectivity",
            "expected_improvement": "1 component after 1-2 rounds", "rounds": 1,
        })

    # ── Elaboration depth ────────────────────────────────────
    el_low, el_high = t["elab"]
    if avg_elab < el_low:
        prescriptions.append({
            "metric": "elaboration_depth", "current": round(avg_elab, 2), "target": list(t["elab"]),
            "severity": "info",
            "diagnosis": f"Average elaboration {avg_elab:.1f}× (target: {el_low}×+).",
            "action": "elaborate", "focus": "general",
            "expected_improvement": "+0.3-0.5 avg per round", "rounds": max(1, int((el_low - avg_elab) / 0.4)),
        })

    # ── Never accessed ───────────────────────────────────────
    if never_accessed_pct > t["never_acc"]:
        prescriptions.append({
            "metric": "never_accessed", "current": round(never_accessed_pct, 1), "target": [0, t["never_acc"]],
            "severity": "info",
            "diagnosis": f"{never_accessed} memories ({never_accessed_pct:.0f}%) never retrieved.",
            "action": "investigate", "focus": None,
            "expected_improvement": "Decreases with use", "rounds": 0,
        })

    # ── Hubs ─────────────────────────────────────────────────
    hubs_pct = hubs / n if n else 0
    if hubs_pct > t["hubs_pct"]:
        prescriptions.append({
            "metric": "hubs", "current": hubs, "target": [0, int(n * t["hubs_pct"])],
            "severity": "info",
            "diagnosis": f"{hubs} hub memories (10+ edges) — potential noise floor.",
            "action": "investigate", "focus": None,
            "expected_improvement": "Requires manual review", "rounds": 0,
        })

    # Sort: warning first, then optimize, then info
    severity_order = {"warning": 0, "optimize": 1, "info": 2}
    prescriptions.sort(key=lambda p: (severity_order.get(p["severity"], 3), p.get("rounds", 0) == 0))

    # ── Content gaps ──────────────────────────────────────────
    # Strategy: scan the ACTUAL filesystem (if project_path provided)
    # to find all code modules. Then compare against memory coverage.
    # Modules with code but no memories = content gaps.

    SKIP_DIRS = {
        "node_modules", ".git", ".next", "dist", "build", "__pycache__",
        "coverage", ".cache", ".turbo", ".vscode", ".idea", "public",
        "assets", "static", "migrations", "seeds", "fixtures", "test",
        "tests", "__tests__", "__mocks__", "scripts", ".claude",
    }
    CODE_EXTENSIONS = {
        ".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs", ".java",
        ".vue", ".svelte", ".rb", ".php", ".cs",
    }

    def _extract_module_dir(fpath: str) -> Optional[str]:
        parts = fpath.replace("\\", "/").split("/")
        dirs = [p for p in parts[:-1] if p]
        if len(dirs) < 2:
            return None
        generic_roots = {"src", "app", "lib", "dist", "build", "node_modules",
                         ".next", "__pycache__", "public", "assets", "static",
                         "backend", "frontend", "server", "client", "packages",
                         "api", "web", "mobile", "shared", "common"}
        for i, d in enumerate(dirs):
            if d.lower() not in generic_roots and i + 1 < len(dirs):
                return f"{dirs[i]}/{dirs[i+1]}"
        if len(dirs) >= 2:
            parent, child = dirs[-2], dirs[-1]
            if child.lower() not in generic_roots:
                return f"{parent}/{child}"
        return None

    content_gaps = []

    if project_path:
        import os
        # Scan filesystem: find all module directories with code files
        root = project_path.replace("\\", "/").rstrip("/")
        codebase_modules: dict[str, int] = {}  # module → file count

        for dirpath, dirnames, filenames in os.walk(project_path):
            # Skip unwanted directories
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            rel = dirpath.replace("\\", "/")
            if root in rel:
                rel = rel[len(root):].lstrip("/")
            else:
                continue

            code_files = [f for f in filenames if os.path.splitext(f)[1] in CODE_EXTENSIONS]
            if not code_files:
                continue

            module = _extract_module_dir(rel + "/dummy.ts")
            if module:
                codebase_modules[module] = codebase_modules.get(module, 0) + len(code_files)

        # Count memory coverage per module (file_path + content mentions)
        memory_coverage: dict[str, int] = {}
        for module in codebase_modules:
            leaf = module.split("/")[-1].lower()
            count = 0
            for m in memories:
                # Check file_path
                if m.file_path and module.lower() in m.file_path.replace("\\", "/").lower():
                    count += 1
                    continue
                # Check content mentions
                if leaf in m.content.lower():
                    count += 1
                    continue
                # Check tags
                if any(leaf in tag.lower() for tag in m.tags):
                    count += 1
            memory_coverage[module] = count

        # Build gaps: modules with code but low memory coverage
        if codebase_modules:
            max_coverage = max(memory_coverage.values()) if memory_coverage else 1
            for module, file_count in codebase_modules.items():
                coverage = memory_coverage.get(module, 0)
                # gap_score: high = poorly covered relative to code size
                # Scale by both absolute coverage and relative to best-covered module
                if max_coverage > 0:
                    relative_score = 1 - (coverage / (max_coverage * 0.5))
                else:
                    relative_score = 1.0
                # Also factor in code size — bigger modules need more coverage
                size_factor = min(file_count / 5, 1.0)  # modules with 5+ files are "big"
                gap_score = round(max(0.0, min(1.0, relative_score * size_factor)), 3)

                content_gaps.append({
                    "module": module,
                    "code_files": file_count,
                    "memory_coverage": coverage,
                    "gap_score": gap_score,
                })
            content_gaps.sort(key=lambda g: g["gap_score"], reverse=True)
            # Only report gaps with meaningful score
            content_gaps = [g for g in content_gaps if g["gap_score"] > 0.3]
    else:
        # Fallback: file_path-based detection (less accurate)
        module_file_counts: dict[str, int] = {}
        for m in memories:
            if m.file_path:
                module = _extract_module_dir(m.file_path.replace("\\", "/"))
                if module:
                    module_file_counts[module] = module_file_counts.get(module, 0) + 1
        # Just report the distribution — Claude interprets
        for module, count in sorted(module_file_counts.items(), key=lambda x: x[1]):
            content_gaps.append({
                "module": module, "code_files": 0, "memory_coverage": count,
                "gap_score": 0.0,  # can't compute without filesystem
            })

    health = round(
        well_connected_pct * 0.25 + typed_ratio * 0.20
        + min(avg_elab / 2, 1.0) * 0.20 + access_balance * 0.15 + largest_pct * 0.20, 3
    )

    return {
        "health_score": health, "maturity": maturity,
        "total_memories": n, "total_edges": total_edges,
        "prescriptions": prescriptions,
        "content_gaps": content_gaps,
        "metrics": {
            "edge_diversity": round(typed_ratio, 3), "graph_connectivity": round(well_connected_pct, 3),
            "access_balance": round(access_balance, 3), "elaboration_depth": round(avg_elab, 2),
            "component_unity": round(largest_pct, 3), "gini": round(gini, 3),
            "never_accessed_pct": round(never_accessed_pct, 1), "hubs": hubs,
            "has_contradicts": has_contradicts, "has_supersedes": has_supersedes,
        },
    }


def create_api_router(db: Database, retrieval=None) -> APIRouter:
    """Create API router with all dashboard endpoints."""
    router = APIRouter(prefix="/api")

    # ── Memories ──────────────────────────────────────────────────────────

    @router.get("/memories")
    async def list_memories(
        project: Optional[str] = None,
        type: Optional[str] = None,
        search: Optional[str] = None,
        tags: Optional[str] = None,
        sort: str = "created",
        deprecated: bool = False,
        limit: int = Query(50, ge=1, le=200),
        offset: int = Query(0, ge=0),
    ):
        mem_type = MemoryType(type) if type else None
        tag_list = [t.strip() for t in tags.split(",")] if tags else None
        memories, total = await db.search_memories(
            search=search, project=project, type=mem_type,
            tags=tag_list, deprecated=deprecated,
            sort=sort, limit=limit, offset=offset,
        )
        return {
            "items": [_memory_to_dict(m) for m in memories],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    @router.get("/memories/{memory_id}")
    async def get_memory(memory_id: str):
        m = await db.get_memory(memory_id)
        if not m:
            return JSONResponse(status_code=404, content={"error": "Memory not found"})
        edges = await db.get_edges(memory_id)
        # Enrich edges with connected memory snippet
        enriched_edges = []
        for e in edges:
            ed = _edge_to_dict(e)
            connected_id = e.to_id if e.from_id == memory_id else e.from_id
            connected = await db.get_memory(connected_id)
            if connected:
                ed["connected_memory"] = {
                    "id": connected.id,
                    "content": connected.content[:120],
                    "type": connected.type.value if hasattr(connected.type, "value") else connected.type,
                    "project": connected.project,
                }
            enriched_edges.append(ed)
        return {
            "memory": _memory_to_dict(m),
            "edges": enriched_edges,
        }

    @router.get("/memories/{memory_id}/edges")
    async def get_memory_edges(memory_id: str):
        edges = await db.get_edges(memory_id)
        return {"edges": [_edge_to_dict(e) for e in edges]}

    # ── Stats ─────────────────────────────────────────────────────────────

    async def _compute_stats(project: Optional[str] = None) -> dict:
        memories = await db.get_all_memories(project=project, deprecated=True)
        active = [m for m in memories if not m.is_deprecated]
        edges = await db.get_edges()

        if project:
            mem_ids = {m.id for m in memories}
            edges = [e for e in edges if e.from_id in mem_ids or e.to_id in mem_ids]

        by_type: dict[str, int] = {}
        by_project: dict[str, int] = {}
        never_accessed = 0
        never_elaborated = 0
        oldest_unelaborated: Optional[datetime] = None

        for m in active:
            t = m.type.value if hasattr(m.type, "value") else m.type
            by_type[t] = by_type.get(t, 0) + 1
            p = m.project or "unknown"
            by_project[p] = by_project.get(p, 0) + 1
            if m.access_count == 0:
                never_accessed += 1
            if m.elaboration_count == 0:
                never_elaborated += 1
                if oldest_unelaborated is None or m.created_at < oldest_unelaborated:
                    oldest_unelaborated = m.created_at

        avg_conn = len(edges) * 2 / len(active) if active else 0.0

        # Health alerts
        alerts: list[dict] = []
        if never_elaborated > 0:
            alerts.append({
                "severity": "warning",
                "message": f"{never_elaborated} memories never elaborated",
                "action": "run_elaboration",
            })
        orphans = 0
        mem_ids_in_edges = set()
        for e in edges:
            mem_ids_in_edges.add(e.from_id)
            mem_ids_in_edges.add(e.to_id)
        for m in active:
            if m.id not in mem_ids_in_edges:
                orphans += 1
        if orphans > 0:
            alerts.append({
                "severity": "info",
                "message": f"{orphans} orphan memories (0 edges)",
                "action": "view_orphans",
            })
        low_decay = sum(1 for m in active if m.decay_score < 0.3)
        if low_decay > 0:
            alerts.append({
                "severity": "info",
                "message": f"{low_decay} memories with decay < 0.3",
                "action": "review_decay",
            })

        sessions = await db.get_sessions(project=project)
        last_extraction = sessions[0].started_at if sessions else None
        elab_logs = await db.get_elaboration_logs(limit=1)
        last_elaboration = elab_logs[0].get("started_at") if elab_logs else None

        # Health score (0-1)
        score = 1.0
        if len(active) > 0:
            elab_ratio = 1 - (never_elaborated / len(active))
            orphan_ratio = 1 - (orphans / len(active))
            score = round((elab_ratio * 0.5 + orphan_ratio * 0.3 + min(avg_conn / 3, 1.0) * 0.2), 2)

        # Edge type distribution
        edge_by_type: dict[str, int] = {}
        for e in edges:
            et = e.type.value if hasattr(e.type, "value") else e.type
            edge_by_type[et] = edge_by_type.get(et, 0) + 1

        return {
            "total_memories": len(active),
            "total_deprecated": len(memories) - len(active),
            "by_type": by_type,
            "by_project": by_project,
            "total_edges": len(edges),
            "edge_by_type": edge_by_type,
            "avg_connections_per_memory": round(avg_conn, 2),
            "memories_never_accessed": never_accessed,
            "memories_never_elaborated": never_elaborated,
            "oldest_unelaborated": oldest_unelaborated.isoformat() if oldest_unelaborated else None,
            "last_extraction": last_extraction.isoformat() if isinstance(last_extraction, datetime) else last_extraction,
            "last_elaboration": last_elaboration if isinstance(last_elaboration, str) else (last_elaboration.isoformat() if last_elaboration else None),
            "health_score": score,
            "alerts": alerts,
        }

    @router.get("/stats")
    async def get_stats():
        return await _compute_stats()

    @router.get("/stats/advanced")
    async def advanced_stats_no_project():
        return await _advanced_stats_impl()

    @router.get("/stats/advanced/{project}")
    async def advanced_stats_project(project: str):
        return await _advanced_stats_impl(project=project)

    @router.get("/stats/{project}")
    async def get_project_stats(project: str):
        return await _compute_stats(project=project)

    # ── Graph ─────────────────────────────────────────────────────────────

    async def _build_graph(
        project: Optional[str] = None,
        min_weight: float = 0.0,
        deprecated: bool = False,
    ) -> dict:
        memories = await db.get_all_memories(project=project, deprecated=deprecated)
        mem_ids = {m.id for m in memories}
        all_edges = await db.get_edges()

        edges = [
            e for e in all_edges
            if e.from_id in mem_ids and e.to_id in mem_ids and e.weight >= min_weight
        ]

        nodes = []
        for m in memories:
            nodes.append({
                "id": m.id,
                "label": m.content[:30],
                "type": m.type.value if hasattr(m.type, "value") else m.type,
                "project": m.project,
                "access_count": m.access_count,
                "decay_score": m.decay_score,
                "token_count": m.token_count,
                "is_deprecated": m.is_deprecated,
            })

        graph_edges = []
        for e in edges:
            graph_edges.append({
                "id": e.id,
                "source": e.from_id,
                "target": e.to_id,
                "weight": e.weight,
                "type": e.type.value if hasattr(e.type, "value") else e.type,
            })

        return {"nodes": nodes, "edges": graph_edges}

    @router.get("/graph")
    async def get_graph(
        min_weight: float = Query(0.0, ge=0.0, le=1.0),
        deprecated: bool = False,
    ):
        return await _build_graph(min_weight=min_weight, deprecated=deprecated)

    @router.get("/graph/{project}")
    async def get_project_graph(
        project: str,
        min_weight: float = Query(0.0, ge=0.0, le=1.0),
        deprecated: bool = False,
    ):
        return await _build_graph(project=project, min_weight=min_weight, deprecated=deprecated)

    # ── Sessions ──────────────────────────────────────────────────────────

    @router.get("/sessions")
    async def list_sessions(project: Optional[str] = None):
        sessions = await db.get_sessions(project=project)
        return {"items": [_session_to_dict(s) for s in sessions]}

    @router.get("/sessions/{session_id}")
    async def get_session(session_id: str):
        sessions = await db.get_sessions()
        session = next((s for s in sessions if s.id == session_id), None)
        if not session:
            return JSONResponse(status_code=404, content={"error": "Session not found"})
        # Get memories from this session
        memories, _ = await db.search_memories(limit=200, offset=0)
        session_memories = [m for m in memories if m.source_session == session_id]
        return {
            "session": _session_to_dict(session),
            "memories": [_memory_to_dict(m) for m in session_memories],
        }

    # ── Elaborations ──────────────────────────────────────────────────────

    @router.get("/elaborations")
    async def list_elaborations(limit: int = Query(50, ge=1, le=200)):
        logs = await db.get_elaboration_logs(limit=limit)
        return {"items": logs}

    @router.get("/elaborations/{elab_id}")
    async def get_elaboration(elab_id: str):
        logs = await db.get_elaboration_logs(limit=500)
        log = next((l for l in logs if l.get("id") == elab_id), None)
        if not log:
            return JSONResponse(status_code=404, content={"error": "Elaboration not found"})
        return log

    # ── Projects ──────────────────────────────────────────────────────────

    @router.get("/projects")
    async def list_projects():
        memories = await db.get_all_memories(deprecated=True)
        projects: dict[str, int] = {}
        for m in memories:
            p = m.project or "unknown"
            projects[p] = projects.get(p, 0) + 1
        return {"projects": [{"name": k, "count": v} for k, v in sorted(projects.items())]}

    # ── Diagnose ──────────────────────────────────────────────────────────

    async def _diagnose_impl(project: Optional[str] = None) -> dict:
        return await diagnose_impl_standalone(db, project=project)

    @router.get("/diagnose")
    async def diagnose_all(project_path: Optional[str] = None):
        return await diagnose_impl_standalone(db, project_path=project_path)

    @router.get("/diagnose/{project}")
    async def diagnose_project(project: str, project_path: Optional[str] = None):
        return await diagnose_impl_standalone(db, project=project, project_path=project_path)

    # ── Advanced Stats ────────────────────────────────────────────────────

    async def _advanced_stats_impl(project: Optional[str] = None):
        """Deep statistical analysis of memory quality."""
        memories = await db.get_all_memories(project=project, deprecated=False)
        all_edges = await db.get_edges()
        if project:
            mem_ids = {m.id for m in memories}
            edges = [e for e in all_edges if e.from_id in mem_ids or e.to_id in mem_ids]
        else:
            edges = all_edges

        n = len(memories)
        if n == 0:
            return {"error": "No memories found"}

        # ── Degree distribution ──────────────────────────────────────
        degree: dict[str, int] = {}
        for m in memories:
            degree[m.id] = 0
        for e in edges:
            if e.from_id in degree:
                degree[e.from_id] = degree.get(e.from_id, 0) + 1
            if e.to_id in degree:
                degree[e.to_id] = degree.get(e.to_id, 0) + 1

        degrees = list(degree.values())
        degrees_sorted = sorted(degrees)
        avg_degree = sum(degrees) / n
        median_degree = degrees_sorted[n // 2]
        under_connected = sum(1 for d in degrees if d <= 1)  # 0-1 edges
        hubs = sum(1 for d in degrees if d >= 10)

        # Degree histogram (0, 1, 2, 3, 4, 5, 6-9, 10+)
        degree_hist: dict[str, int] = {
            "0": 0, "1": 0, "2": 0, "3": 0, "4": 0, "5": 0, "6-9": 0, "10+": 0
        }
        for d in degrees:
            if d == 0: degree_hist["0"] += 1
            elif d == 1: degree_hist["1"] += 1
            elif d == 2: degree_hist["2"] += 1
            elif d == 3: degree_hist["3"] += 1
            elif d == 4: degree_hist["4"] += 1
            elif d == 5: degree_hist["5"] += 1
            elif d <= 9: degree_hist["6-9"] += 1
            else: degree_hist["10+"] += 1

        # ── Edge type diversity ──────────────────────────────────────
        edge_types: dict[str, int] = {}
        for e in edges:
            et = e.type.value if hasattr(e.type, "value") else e.type
            edge_types[et] = edge_types.get(et, 0) + 1

        total_edges = len(edges)
        relates_to_count = edge_types.get("relates_to", 0)
        typed_ratio = round(1 - (relates_to_count / total_edges), 3) if total_edges > 0 else 0
        has_contradicts = edge_types.get("contradicts", 0) > 0
        has_supersedes = edge_types.get("supersedes", 0) > 0

        # ── Access distribution (Gini coefficient) ───────────────────
        access_counts = sorted([m.access_count for m in memories])
        total_access = sum(access_counts)
        if total_access > 0:
            cumulative = 0
            gini_sum = 0
            for i, a in enumerate(access_counts):
                cumulative += a
                gini_sum += cumulative
            gini = 1 - (2 * gini_sum) / (n * total_access) + 1 / n
            gini = round(min(max(gini, 0), 1), 3)
        else:
            gini = 0.0

        never_accessed = sum(1 for a in access_counts if a == 0)
        top10_access = sorted(access_counts, reverse=True)[:10]

        # ── Elaboration depth ────────────────────────────────────────
        elab_counts = [m.elaboration_count for m in memories]
        elab_dist: dict[str, int] = {}
        for ec in elab_counts:
            key = f"{ec}x"
            elab_dist[key] = elab_dist.get(key, 0) + 1
        avg_elab = round(sum(elab_counts) / n, 2)

        # ── Connected components (BFS) ───────────────────────────────
        adj: dict[str, set] = {m.id: set() for m in memories}
        for e in edges:
            if e.from_id in adj and e.to_id in adj:
                adj[e.from_id].add(e.to_id)
                adj[e.to_id].add(e.from_id)

        visited: set[str] = set()
        components: list[int] = []
        for mid in adj:
            if mid not in visited:
                # BFS
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
        largest_component = components[0] if components else 0
        num_components = len(components)
        isolated_components = sum(1 for c in components if c == 1)

        # ── Token stats ──────────────────────────────────────────────
        tokens = [m.token_count for m in memories if m.token_count > 0]
        avg_tokens = round(sum(tokens) / len(tokens), 1) if tokens else 0
        min_tokens = min(tokens) if tokens else 0
        max_tokens = max(tokens) if tokens else 0

        # ── Memory type balance ──────────────────────────────────────
        type_counts: dict[str, int] = {}
        for m in memories:
            t = m.type.value if hasattr(m.type, "value") else m.type
            type_counts[t] = type_counts.get(t, 0) + 1

        # ── Decay distribution ───────────────────────────────────────
        decay_scores = [m.decay_score for m in memories]
        decay_buckets = {
            "fresh (>0.9)": sum(1 for d in decay_scores if d > 0.9),
            "healthy (0.5-0.9)": sum(1 for d in decay_scores if 0.5 <= d <= 0.9),
            "fading (0.3-0.5)": sum(1 for d in decay_scores if 0.3 <= d < 0.5),
            "weak (<0.3)": sum(1 for d in decay_scores if d < 0.3),
        }

        # ── Revised Health Score ─────────────────────────────────────
        # Graph connectivity: % memories with 3+ edges (target: 80%)
        well_connected = sum(1 for d in degrees if d >= 3) / n
        # Edge diversity: % non-relates_to (target: 30%+)
        edge_diversity = typed_ratio
        # Elaboration depth: avg elaboration count (target: 2+)
        elab_quality = min(avg_elab / 2, 1.0)
        # Access balance: inverse Gini (target: low Gini = balanced)
        access_balance = 1 - gini
        # Component unity: largest component / total (target: 95%+)
        unity = largest_component / n if n > 0 else 0

        health = round(
            well_connected * 0.25
            + edge_diversity * 0.20
            + elab_quality * 0.20
            + access_balance * 0.15
            + unity * 0.20,
            3
        )

        health_breakdown = {
            "graph_connectivity": round(well_connected, 3),
            "edge_diversity": round(edge_diversity, 3),
            "elaboration_depth": round(elab_quality, 3),
            "access_balance": round(access_balance, 3),
            "component_unity": round(unity, 3),
        }

        # ── Growth timeline (cumulative memories over time) ────────
        from collections import Counter
        growth_by_day: dict[str, int] = {}
        for m in memories:
            if m.created_at:
                day = m.created_at.strftime("%Y-%m-%d") if isinstance(m.created_at, datetime) else str(m.created_at)[:10]
                growth_by_day[day] = growth_by_day.get(day, 0) + 1

        sorted_days = sorted(growth_by_day.keys())
        growth_timeline = []
        cumulative = 0
        for d in sorted_days:
            cumulative += growth_by_day[d]
            growth_timeline.append({"date": d, "total": cumulative, "new": growth_by_day[d]})

        # ── Edge growth (from edge created_at) ───────────────────
        edge_by_day: dict[str, int] = {}
        for e in edges:
            if e.created_at:
                day = e.created_at.strftime("%Y-%m-%d") if isinstance(e.created_at, datetime) else str(e.created_at)[:10]
                edge_by_day[day] = edge_by_day.get(day, 0) + 1
        sorted_edge_days = sorted(edge_by_day.keys())
        edge_cumulative = 0
        for d in sorted_edge_days:
            edge_cumulative += edge_by_day[d]
            # Merge into existing growth timeline entries
            existing = next((g for g in growth_timeline if g["date"] == d), None)
            if existing:
                existing["total_edges"] = edge_cumulative
            else:
                growth_timeline.append({"date": d, "total": cumulative, "new": 0, "total_edges": edge_cumulative})
        # Fill forward edge counts
        last_edge_count = 0
        growth_timeline.sort(key=lambda x: x["date"])
        for entry in growth_timeline:
            if "total_edges" in entry:
                last_edge_count = entry["total_edges"]
            else:
                entry["total_edges"] = last_edge_count

        return {
            "total_memories": n,
            "total_edges": total_edges,
            # Graph
            "graph": {
                "avg_degree": round(avg_degree, 2),
                "median_degree": median_degree,
                "degree_histogram": degree_hist,
                "under_connected_0_1": under_connected,
                "hubs_10_plus": hubs,
                "connected_components": num_components,
                "largest_component": largest_component,
                "largest_component_pct": round(largest_component / n * 100, 1) if n else 0,
                "isolated_nodes": isolated_components,
                "edge_types": edge_types,
                "typed_edge_ratio": typed_ratio,
                "has_contradicts": has_contradicts,
                "has_supersedes": has_supersedes,
            },
            # Access
            "access": {
                "gini_coefficient": gini,
                "never_accessed": never_accessed,
                "never_accessed_pct": round(never_accessed / n * 100, 1) if n else 0,
                "total_accesses": total_access,
                "top_10_access_counts": top10_access,
            },
            # Elaboration
            "elaboration": {
                "avg_count": avg_elab,
                "distribution": elab_dist,
            },
            # Memory quality
            "memory_quality": {
                "type_distribution": type_counts,
                "avg_tokens": avg_tokens,
                "min_tokens": min_tokens,
                "max_tokens": max_tokens,
                "decay_distribution": decay_buckets,
            },
            # Health
            "health_score": health,
            "health_breakdown": health_breakdown,
            "growth_timeline": growth_timeline,
        }

    # ── Health ────────────────────────────────────────────────────────────

    @router.get("/health")
    async def health():
        try:
            stats = await _compute_stats()
            return {
                "status": "ok",
                "service": "mango-brain",
                "health_score": stats["health_score"],
                "total_memories": stats["total_memories"],
                "total_edges": stats["total_edges"],
                "alerts": stats["alerts"],
            }
        except Exception as e:
            return {
                "status": "ok",
                "service": "mango-brain",
                "health_score": 1.0,
                "total_memories": 0,
                "total_edges": 0,
                "alerts": [],
            }

    # ── Setup Progress ─────────────────────────────────────────────────

    @router.get("/setup")
    async def get_all_setup():
        """Get setup progress for all projects."""
        return await db.get_all_projects_setup()

    @router.get("/setup/{project}")
    async def get_setup(project: str):
        """Get setup progress for a specific project."""
        steps = await db.get_setup_progress(project)
        if not steps:
            return JSONResponse(
                status_code=404,
                content={"error": f"Project '{project}' not initialized"},
            )
        summary = await db.get_setup_summary(project)
        summary["steps"] = [
            {
                "phase": s.phase,
                "step": s.step,
                "order_index": s.order_index,
                "title": s.title,
                "description": s.description,
                "status": s.status.value,
                "prompt_file": s.prompt_file,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "result": s.result,
            }
            for s in steps
        ]
        return summary

    @router.put("/setup/{project}/{phase}/{step}")
    async def update_setup(project: str, phase: str, step: str, body: dict):
        """Update a setup step's status."""
        from datetime import datetime as dt
        fields = {}
        if "status" in body:
            fields["status"] = body["status"]
            if body["status"] == "in_progress" and "started_at" not in body:
                fields["started_at"] = dt.utcnow().isoformat()
            if body["status"] == "completed" and "completed_at" not in body:
                fields["completed_at"] = dt.utcnow().isoformat()
        if "result" in body:
            fields["result"] = body["result"] if isinstance(body["result"], str) else __import__("json").dumps(body["result"])
        if "started_at" in body:
            fields["started_at"] = body["started_at"]
        if "completed_at" in body:
            fields["completed_at"] = body["completed_at"]

        ok = await db.update_setup_step(project, phase, step, fields)
        if not ok:
            return JSONResponse(status_code=404, content={"error": "Step not found"})

        # Auto-complete "memory_ready" if all previous steps are done
        if phase != "ready":
            all_steps = await db.get_setup_progress(project)
            non_ready = [s for s in all_steps if s.phase != "ready"]
            if all(s.status.value in ("completed", "skipped") for s in non_ready):
                await db.update_setup_step(project, "ready", "memory_ready", {
                    "status": "completed",
                    "completed_at": dt.utcnow().isoformat(),
                })

        return await db.get_setup_summary(project)

    @router.post("/setup/{project}/init")
    async def init_setup(project: str):
        """Initialize setup progress for a project."""
        count = await db.init_setup_progress(project)
        return {"project": project, "steps_created": count}

    # ── Remember (query) ──────────────────────────────────────────────

    @router.get("/remember")
    async def remember_query(
        query: str = Query("", min_length=0),
        mode: str = "deep",
        project: Optional[str] = None,
    ):
        """Query memories using the retrieval engine (same as MCP remember)."""
        if not retrieval:
            return JSONResponse(
                status_code=503,
                content={"error": "Retrieval engine not available (API started without embeddings)"},
            )
        try:
            if mode == "recent":
                memories, scores, total_tokens = await retrieval.remember_recent(
                    project=project or None,
                    dry_run=True,
                )
            else:
                if not query.strip():
                    return JSONResponse(
                        status_code=400,
                        content={"error": "query is required for deep/quick mode"},
                    )
                memories, scores, total_tokens = await retrieval.remember(
                    query=query.strip(),
                    mode=mode,
                    project=project or None,
                    dry_run=True,
                )
            items = []
            for i, m in enumerate(memories):
                d = _memory_to_dict(m)
                d["score"] = round(float(scores[i]) if i < len(scores) else 0.0, 4)
                items.append(d)
            return {
                "query": query,
                "mode": mode,
                "project": project,
                "count": len(items),
                "total_tokens": total_tokens,
                "results": items,
            }
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": str(e)},
            )

    return router
