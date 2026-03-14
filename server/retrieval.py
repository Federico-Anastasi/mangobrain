"""MangoBrain — Retrieval pipeline (remember)."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

import numpy as np

from server.config import (
    ALPHA, DEEP_BUDGET, QUICK_BUDGET, SESSION_QUICK_BUDGET,
    DEEP_MAX_RESULTS, QUICK_MAX_RESULTS,
    RELEVANCE_THRESHOLD_RATIO, QUICK_RELEVANCE_THRESHOLD_RATIO,
)
from server.database import Database
from server.embeddings import Embedder
from server.graph import GraphManager
from server.models import Edge, EdgeType, Memory, MemorySource

logger = logging.getLogger(__name__)


class RetrievalEngine:
    """Semantic + graph retrieval with knapsack selection."""

    def __init__(self, db: Database, embedder: Embedder, graph: GraphManager) -> None:
        self.db = db
        self.embedder = embedder
        self.graph = graph
        # Session budget tracking: {session_id: tokens_used}
        self._session_budgets: dict[str, int] = {}

    async def remember(
        self,
        query: str,
        mode: str = "deep",
        project: Optional[str] = None,
        budget: Optional[int] = None,
        session_id: Optional[str] = None,
        dry_run: bool = False,
    ) -> tuple[list[Memory], int]:
        """Retrieve relevant memories for a query.

        Returns:
            (selected_memories, total_tokens)
        """
        # Budget
        if budget is None:
            budget = DEEP_BUDGET if mode == "deep" else QUICK_BUDGET

        # Enforce session budget for quick mode
        if mode == "quick" and session_id:
            used = self._session_budgets.get(session_id, 0)
            remaining = SESSION_QUICK_BUDGET - used
            if remaining <= 0:
                raise ValueError("Session micro-query budget exhausted")
            budget = min(budget, remaining)

        # 1. Embed query
        query_emb = self.embedder.encode(query)

        # 2. Load all non-deprecated memories (filtered by project)
        memories = await self.db.get_all_memories(project=project, deprecated=False)
        if not memories:
            return [], 0

        # 3. Cosine similarity → φ₀
        all_embs = np.array([
            Embedder.bytes_to_embedding(m.embedding) for m in memories
        ])
        phi_0 = Embedder.cosine_similarity(query_emb, all_embs)

        # Apply decay as a multiplier
        decay_scores = np.array([m.decay_score for m in memories])
        phi_0 = phi_0 * decay_scores

        # 4. Graph propagation (both modes — the graph IS the differentiator)
        # Deep: full propagation (α=0.3). Quick: lighter (α=0.15).
        memory_ids = [m.id for m in memories]
        edges = await self.db.get_all_edges(memory_ids)
        A = self.graph.build_adjacency_matrix(memory_ids, edges)
        alpha = ALPHA if mode == "deep" else ALPHA * 0.5
        phi = self.graph.propagate(phi_0, A, alpha=alpha)

        # 5. Knapsack greedy selection (with mode-specific threshold)
        max_results = DEEP_MAX_RESULTS if mode == "deep" else QUICK_MAX_RESULTS
        threshold_ratio = RELEVANCE_THRESHOLD_RATIO if mode == "deep" else QUICK_RELEVANCE_THRESHOLD_RATIO
        selected, scores = self._knapsack_select(phi, memories, budget, max_results, threshold_ratio)

        # 7. Update access stats (skip in dry_run mode — dashboard queries)
        if not dry_run:
            now = datetime.utcnow()
            for m in selected:
                await self.db.update_memory(m.id, {
                    "last_accessed": now,
                    "access_count": m.access_count + 1,
                })

            # 8. Reinforce existing co_occurs edges between co-selected memories
            # NOTE: Only reinforce edges that already exist — do NOT create new ones.
            # Creating co_occurs edges on every retrieval causes edge explosion and
            # destroys ranking by making graph propagation uniform.
            for i, m1 in enumerate(selected):
                for m2 in selected[i + 1:]:
                    existing = [
                        e for e in edges
                        if e.type == EdgeType.co_occurs
                        and {e.from_id, e.to_id} == {m1.id, m2.id}
                    ]
                    if existing:
                        e = existing[0]
                        new_weight = min(e.weight + 0.05, 1.0)
                        await self.db.update_edge(e.id, {
                            "weight": new_weight,
                            "last_reinforced": now,
                            "reinforce_count": e.reinforce_count + 1,
                        })

        total_tokens = sum(m.token_count for m in selected)

        # Track session budget
        if mode == "quick" and session_id:
            self._session_budgets[session_id] = (
                self._session_budgets.get(session_id, 0) + total_tokens
            )

        return selected, scores, total_tokens

    async def remember_recent(
        self,
        project: Optional[str] = None,
        limit: int = 15,
        k_neighbors: int = 2,
        budget: int = 8000,
        dry_run: bool = False,
    ) -> tuple[list[Memory], list[float], int]:
        """Retrieve recent memories + their graph neighbors.

        Returns: (memories, scores, total_tokens)
        Scoring: recency-based (1.0 for newest, decaying linearly) + neighbor bonus.
        """
        # 1. Get N most recent
        recent = await self.db.get_recent_memories(project, limit)
        if not recent:
            return [], [], 0

        # 2. Assign recency scores (1.0 → 0.3 linear)
        recency_scores: dict[str, float] = {}
        for i, m in enumerate(recent):
            recency_scores[m.id] = 1.0 - (i / max(len(recent) - 1, 1)) * 0.7

        # 3. Expand via graph: k-hop neighbors for each recent memory
        all_memories = await self.db.get_all_memories(project=project, deprecated=False)
        all_edges = await self.db.get_all_edges([m.id for m in all_memories])

        recent_ids = {m.id for m in recent}
        neighbor_ids: set[str] = set()
        for m in recent:
            neighbors = self.graph.get_neighbors(m.id, all_edges, hops=k_neighbors)
            neighbor_ids.update(neighbors)

        # Remove already-included IDs
        neighbor_ids -= recent_ids

        # 4. Score neighbors by connection strength to recent memories
        id_to_mem = {m.id: m for m in all_memories}
        for nid in neighbor_ids:
            if nid in id_to_mem:
                max_weight = 0.0
                for e in all_edges:
                    if (e.from_id == nid and e.to_id in recency_scores) or \
                       (e.to_id == nid and e.from_id in recency_scores):
                        connected_recent = e.to_id if e.from_id == nid else e.from_id
                        score = e.weight * recency_scores[connected_recent] * 0.5
                        max_weight = max(max_weight, score)
                if max_weight > 0:
                    recency_scores[nid] = max_weight

        # 5. Knapsack selection within budget
        candidates = []
        for mid, score in recency_scores.items():
            m = id_to_mem.get(mid)
            if m and not m.is_deprecated:
                candidates.append((score / max(m.token_count, 1), score, m))
        candidates.sort(key=lambda x: x[0], reverse=True)

        selected: list[Memory] = []
        scores: list[float] = []
        total_tokens = 0
        for _, score, m in candidates:
            if total_tokens + m.token_count > budget:
                continue
            selected.append(m)
            scores.append(score)
            total_tokens += m.token_count

        # 6. Update access stats (skip in dry_run mode — dashboard queries)
        if not dry_run:
            now = datetime.utcnow()
            for m in selected:
                await self.db.update_memory(m.id, {
                    "last_accessed": now,
                    "access_count": m.access_count + 1,
                })

        return selected, scores, total_tokens

    @staticmethod
    def _knapsack_select(
        phi: np.ndarray,
        memories: list[Memory],
        budget: int,
        max_results: int = 30,
        threshold_ratio: float = RELEVANCE_THRESHOLD_RATIO,
    ) -> tuple[list[Memory], list[float]]:
        """Greedy knapsack: maximize relevance within token budget.

        Uses dynamic threshold: only memories with score >= max_score * threshold_ratio
        are considered. Also caps total results.

        Returns:
            (selected_memories, relevance_scores)
        """
        max_score = float(phi.max()) if len(phi) > 0 else 0.0
        min_threshold = max_score * threshold_ratio

        scored = [
            (phi[i] / max(m.token_count, 1), phi[i], m)
            for i, m in enumerate(memories)
            if not m.is_deprecated and phi[i] >= min_threshold
        ]
        scored.sort(key=lambda x: x[0], reverse=True)

        selected: list[Memory] = []
        scores: list[float] = []
        total_tokens = 0
        for _, relevance, memory in scored:
            if len(selected) >= max_results:
                break
            if total_tokens + memory.token_count <= budget:
                selected.append(memory)
                scores.append(float(relevance))
                total_tokens += memory.token_count

        return selected, scores
