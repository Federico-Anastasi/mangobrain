"""MangoBrain — Core verification test.

Run from mango-brain/ directory:
    python test_core.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid

import numpy as np


async def test_database():
    """Test database CRUD operations."""
    from server.config import count_tokens
    from server.database import Database
    from server.models import Edge, EdgeType, Memory, MemorySource, MemoryType

    print("\n=== Testing Database ===")

    db = await Database.create("data/test_mangobrain.db")
    print("✓ Database created")

    # Insert memories
    memories = []
    for i in range(5):
        m = Memory(
            content=f"Test memory {i}: This is a test memory about topic {i}",
            embedding=np.random.randn(1024).astype(np.float32).tobytes(),
            type=MemoryType.semantic,
            project="test",
            tags=["test", f"topic{i}"],
            token_count=count_tokens(f"Test memory {i}: This is a test memory about topic {i}"),
            source=MemorySource.manual,
        )
        await db.insert_memory(m)
        memories.append(m)
    print(f"✓ Inserted {len(memories)} memories")

    # Get memory
    fetched = await db.get_memory(memories[0].id)
    assert fetched is not None
    assert fetched.content == memories[0].content
    print("✓ get_memory works")

    # Get all
    all_mems = await db.get_all_memories(project="test")
    assert len(all_mems) >= 5
    print(f"✓ get_all_memories returned {len(all_mems)} memories")

    # Update
    await db.update_memory(memories[0].id, {"access_count": 5})
    updated = await db.get_memory(memories[0].id)
    assert updated.access_count == 5
    print("✓ update_memory works")

    # Insert edge
    edge = Edge(
        from_id=memories[0].id,
        to_id=memories[1].id,
        weight=0.7,
        type=EdgeType.relates_to,
    )
    await db.insert_edge(edge)
    print("✓ insert_edge works")

    # Get edges
    edges = await db.get_edges(memories[0].id)
    assert len(edges) >= 1
    print(f"✓ get_edges returned {len(edges)} edges")

    # Search
    results, total = await db.search_memories(search="topic 2", project="test")
    assert total >= 1
    print(f"✓ search_memories found {total} results for 'topic 2'")

    # Cleanup
    await db.close()
    import os
    os.remove("data/test_mangobrain.db")
    print("✓ Database test complete\n")


async def test_graph():
    """Test graph manager."""
    from server.graph import GraphManager
    from server.models import Edge, EdgeType

    print("=== Testing Graph Manager ===")

    gm = GraphManager()

    memory_ids = ["a", "b", "c", "d"]
    edges = [
        Edge(from_id="a", to_id="b", weight=0.8, type=EdgeType.relates_to),
        Edge(from_id="b", to_id="c", weight=0.6, type=EdgeType.depends_on),
        Edge(from_id="c", to_id="d", weight=0.4, type=EdgeType.relates_to),
    ]

    A = gm.build_adjacency_matrix(memory_ids, edges)
    assert A.shape == (4, 4)
    print(f"✓ Adjacency matrix built: {A.shape}")

    phi_0 = np.array([1.0, 0.0, 0.0, 0.0])
    phi = gm.propagate(phi_0, A, alpha=0.3)
    assert phi[0] > phi[1] > 0  # a should be highest, b should get some from propagation
    print(f"✓ Propagation: φ = {np.round(phi, 3)}")
    print(f"  (a=1.0 propagates to b via edge, b to c, c to d)")

    neighbors = gm.get_neighbors("a", edges, hops=2)
    assert "b" in neighbors
    assert "c" in neighbors
    print(f"✓ Neighbors of 'a' (2 hops): {neighbors}")

    print("✓ Graph test complete\n")


async def test_embeddings_mock():
    """Test embedding utilities without loading the actual model."""
    from server.embeddings import Embedder

    print("=== Testing Embeddings (mock) ===")

    # Test serialization round-trip
    emb = np.random.randn(1024).astype(np.float32)
    emb = emb / np.linalg.norm(emb)  # normalize
    b = Embedder.embedding_to_bytes(emb)
    recovered = Embedder.bytes_to_embedding(b)
    assert np.allclose(emb, recovered)
    print("✓ embedding_to_bytes / bytes_to_embedding round-trip")

    # Test cosine similarity
    q = np.random.randn(1024).astype(np.float32)
    q = q / np.linalg.norm(q)
    matrix = np.random.randn(10, 1024).astype(np.float32)
    matrix = matrix / np.linalg.norm(matrix, axis=1, keepdims=True)
    sims = Embedder.cosine_similarity(q, matrix)
    assert sims.shape == (10,)
    assert all(-1.01 <= s <= 1.01 for s in sims)
    print(f"✓ Cosine similarity: shape={sims.shape}, range=[{sims.min():.3f}, {sims.max():.3f}]")

    print("✓ Embeddings mock test complete\n")


async def test_config():
    """Test config loading."""
    from server.config import (
        ALPHA, DB_PATH, DECAY_LAMBDAS, DEEP_BUDGET, DEDUP_THRESHOLD,
        EMBEDDING_MODEL, QUICK_BUDGET, count_tokens,
    )

    print("=== Testing Config ===")
    print(f"  DB_PATH: {DB_PATH}")
    print(f"  EMBEDDING_MODEL: {EMBEDDING_MODEL}")
    print(f"  ALPHA: {ALPHA}")
    print(f"  DEDUP_THRESHOLD: {DEDUP_THRESHOLD}")
    print(f"  BUDGETS: deep={DEEP_BUDGET}, quick={QUICK_BUDGET}")
    print(f"  DECAY_LAMBDAS: {DECAY_LAMBDAS}")

    tokens = count_tokens("Hello, this is a test of the token counter.")
    print(f"  count_tokens('Hello, this is a test...') = {tokens}")
    assert tokens > 0

    print("✓ Config test complete\n")


async def main():
    print("=" * 60)
    print("  MangoBrain — Core Verification")
    print("=" * 60)

    await test_config()
    await test_embeddings_mock()
    await test_graph()
    await test_database()

    print("=" * 60)
    print("  ALL TESTS PASSED ✓")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
