"""Test: Initialize MusicLabs memory via direct Python calls."""
import asyncio
import json
import sys
sys.path.insert(0, ".")

from server.config import DB_PATH, EMBEDDING_MODEL, EMBEDDING_DEVICE
from server.database import Database
from server.embeddings import Embedder
from server.graph import GraphManager
from server.retrieval import RetrievalEngine


async def main():
    print("=== MangoBrain Init Test ===\n")

    # 1. Init components
    print("[1/4] Initializing database...")
    db = await Database.create(DB_PATH)

    print("[2/4] Loading embedding model (GPU)...")
    embedder = Embedder(EMBEDDING_MODEL, EMBEDDING_DEVICE)
    embedder.load()
    print(f"  Model loaded, dim={embedder.dim}")

    graph = GraphManager()
    retrieval = RetrievalEngine(db, embedder, graph)

    # 2. Register tools and call init_project
    from mcp.server.fastmcp import FastMCP
    server = FastMCP("test")
    from server.mcp_tools import register_tools
    register_tools(server, db, embedder, graph, retrieval)

    # Call init_project directly via the internal function
    # We need to call the tool function directly
    from server.mcp_tools import _split_into_sections, _tags_from_filename
    from server.models import Memory, Edge, EdgeType, MemoryType, MemorySource
    from server.config import DEDUP_THRESHOLD, count_tokens
    from pathlib import Path
    import numpy as np

    project = "musiclabs"
    project_path = "C:/Users/Mango/Desktop/Dev_FA/musiclabs"
    root = Path(project_path)

    print(f"\n[3/4] Importing rules from {project_path}...")

    rule_files = []
    claude_md = root / "CLAUDE.md"
    if claude_md.exists():
        rule_files.append(("CLAUDE.md", claude_md.read_text(encoding="utf-8")))
        print(f"  Found CLAUDE.md")

    rules_dir = root / ".claude" / "rules"
    if rules_dir.exists():
        for f in sorted(rules_dir.iterdir()):
            if f.is_file() and f.suffix in (".md", ".txt"):
                rule_files.append((f.name, f.read_text(encoding="utf-8")))
                print(f"  Found rule: {f.name}")

    total_memories = 0
    total_edges = 0

    for filename, content in rule_files:
        sections = _split_into_sections(content, filename)
        file_memory_ids = []

        for section_title, section_content in sections:
            if not section_content.strip():
                continue

            mem_content = f"[{project}] {filename}"
            if section_title:
                mem_content += f" > {section_title}"
            mem_content += f"\n{section_content.strip()}"

            emb = embedder.encode(mem_content)
            emb_bytes = Embedder.embedding_to_bytes(emb)

            # Dedup check
            existing = await db.get_all_memories(project=project, deprecated=False)
            skip = False
            if existing:
                existing_embs = np.array([
                    Embedder.bytes_to_embedding(m.embedding) for m in existing
                ])
                sims = Embedder.cosine_similarity(emb, existing_embs)
                if sims.max() > DEDUP_THRESHOLD:
                    skip = True

            if skip:
                print(f"    SKIP (duplicate): {section_title[:50]}")
                continue

            memory = Memory(
                content=mem_content,
                embedding=emb_bytes,
                type=MemoryType.procedural,
                project=project,
                tags=_tags_from_filename(filename),
                token_count=count_tokens(mem_content),
                source=MemorySource.manual,
            )
            await db.insert_memory(memory)
            file_memory_ids.append(memory.id)
            total_memories += 1

        # Create edges between memories from same file
        for i, id1 in enumerate(file_memory_ids):
            for id2 in file_memory_ids[i + 1:]:
                edge = Edge(
                    from_id=id1, to_id=id2,
                    weight=0.4, type=EdgeType.relates_to,
                    source=MemorySource.manual,
                )
                await db.insert_edge(edge)
                total_edges += 1

        print(f"  {filename}: {len(file_memory_ids)} memories, edges created")

    print(f"\n  Total: {total_memories} memories, {total_edges} edges")

    # 3. Find sessions
    print(f"\n[4/4] Finding JSONL sessions...")
    from server.jsonl_parser import find_all_sessions
    sessions = find_all_sessions(project)
    print(f"  Found {len(sessions)} session files")
    for s in sessions[:5]:
        print(f"    {s}")
    if len(sessions) > 5:
        print(f"    ... and {len(sessions) - 5} more")

    # 4. Test remember
    print(f"\n=== Testing remember ===")
    memories, tokens = await retrieval.remember(
        query="project setup, architecture, tech stack",
        mode="deep", project="musiclabs",
    )
    print(f"  Query returned {len(memories)} memories ({tokens} tokens)")
    for m in memories[:3]:
        print(f"  - [{m.type}] {m.content[:80]}...")

    await db.close()
    print("\n=== Done! ===")


if __name__ == "__main__":
    asyncio.run(main())
