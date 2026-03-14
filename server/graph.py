"""MangoBrain — Graph manager (adjacency matrix & propagation)."""

from __future__ import annotations

import numpy as np
from scipy import sparse
from scipy.sparse.linalg import spsolve

from server.models import Edge, EdgeType


# Edge type semantics for the adjacency matrix:
# - SYMMETRIC: both directions get the same weight (A↔B)
# - DIRECTIONAL: only from→to gets the weight (A→B)
# - NEGATIVE: weight is inverted (pushes relevance away)

_SYMMETRIC_TYPES = {EdgeType.relates_to, EdgeType.co_occurs}
_NEGATIVE_TYPES = {EdgeType.contradicts}
# supersedes: A supersedes B means A→B is negative (B should lose relevance
# when A is relevant), but B→A is positive (if B is relevant, A is too)
_SUPERSEDES = EdgeType.supersedes
# directional types: from→to only (A depends_on B, A caused_by B)
_DIRECTIONAL_TYPES = {EdgeType.depends_on, EdgeType.caused_by}


class GraphManager:
    """Builds sparse adjacency matrix and propagates relevance scores."""

    @staticmethod
    def build_adjacency_matrix(
        memory_ids: list[str],
        edges: list[Edge],
    ) -> sparse.csr_matrix:
        """Build weighted adjacency matrix from edges with type-aware semantics.

        Edge type handling:
        - relates_to, co_occurs: symmetric (A↔B, same weight)
        - depends_on, caused_by: directional (from→to only)
        - contradicts: symmetric with negative weight
        - supersedes: A supersedes B → A→B negative, B→A positive

        Args:
            memory_ids: ordered list of memory IDs (defines row/col indices)
            edges: list of Edge objects

        Returns:
            Sparse CSR matrix (n x n) with signed edge weights.
        """
        n = len(memory_ids)
        if n == 0:
            return sparse.csr_matrix((0, 0))

        id_to_idx = {mid: i for i, mid in enumerate(memory_ids)}
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []

        for edge in edges:
            i = id_to_idx.get(edge.from_id)
            j = id_to_idx.get(edge.to_id)
            if i is None or j is None:
                continue

            w = edge.weight

            if edge.type in _SYMMETRIC_TYPES:
                # Bidirectional, positive
                rows.extend([i, j])
                cols.extend([j, i])
                data.extend([w, w])

            elif edge.type in _DIRECTIONAL_TYPES:
                # from→to only: if "A depends_on B", querying A should
                # pull in B (the dependency), not vice versa
                rows.append(i)
                cols.append(j)
                data.append(w)

            elif edge.type in _NEGATIVE_TYPES:
                # Symmetric negative: contradictions push each other down
                rows.extend([i, j])
                cols.extend([j, i])
                data.extend([-w, -w])

            elif edge.type == _SUPERSEDES:
                # A supersedes B:
                # A→B: negative (B is outdated when A is relevant)
                # B→A: positive (if someone finds B, A is the better version)
                rows.extend([i, j])
                cols.extend([j, i])
                data.extend([-w, w])

        if not rows:
            return sparse.csr_matrix((n, n))

        return sparse.csr_matrix((data, (rows, cols)), shape=(n, n))

    @staticmethod
    def propagate(
        phi_0: np.ndarray,
        A: sparse.csr_matrix,
        alpha: float = 0.3,
    ) -> np.ndarray:
        """Propagate relevance: φ = (I - αA_norm)⁻¹ φ₀

        Handles signed adjacency matrices (negative weights from contradicts/
        supersedes edges). Row-normalization uses absolute values to preserve
        sign semantics while keeping the system stable.

        Args:
            phi_0: initial relevance vector (cosine similarities)
            A: weighted adjacency matrix (may contain negative entries)
            alpha: propagation factor (0 = no propagation, 1 = maximum)

        Returns:
            Propagated relevance vector, clamped to [0, 1].
        """
        n = A.shape[0]
        if n == 0:
            return phi_0

        I = sparse.eye(n, format="csr")

        # Row-normalize by absolute row sums to preserve sign semantics
        # This ensures negative edges push relevance DOWN, not flip direction
        abs_row_sums = np.array(np.abs(A).sum(axis=1)).flatten()
        abs_row_sums[abs_row_sums == 0] = 1.0
        D_inv = sparse.diags(1.0 / abs_row_sums)
        A_norm = D_inv @ A

        # Solve (I - αA_norm)φ = φ₀
        phi = spsolve(I - alpha * A_norm, phi_0)
        return np.clip(phi, 0.0, 1.0)

    @staticmethod
    def get_neighbors(
        memory_id: str,
        edges: list[Edge],
        hops: int = 1,
    ) -> list[str]:
        """Get neighbor IDs up to N hops away."""
        # Build adjacency list
        adj: dict[str, set[str]] = {}
        for e in edges:
            adj.setdefault(e.from_id, set()).add(e.to_id)
            adj.setdefault(e.to_id, set()).add(e.from_id)

        visited: set[str] = set()
        frontier = {memory_id}

        for _ in range(hops):
            next_frontier: set[str] = set()
            for nid in frontier:
                for neighbor in adj.get(nid, set()):
                    if neighbor not in visited and neighbor != memory_id:
                        next_frontier.add(neighbor)
            visited.update(frontier)
            frontier = next_frontier

        visited.update(frontier)
        visited.discard(memory_id)
        return list(visited)
