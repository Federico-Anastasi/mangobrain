# /smoke-test — Memory Retrieval Quality Verification

Runs test queries against the memory system to verify retrieval quality, coverage, and relevance.

## When to use
- After initialization (step 8 of /brain-init)
- After major memory changes (bulk extraction, elaboration)
- When retrieval feels off and you want to quantify it
- When the user says "/smoke-test", "testa la memoria", "verifica retrieval", or similar

## Input
- **project**: project name (ask if not provided)

## Workflow

### Step 1 — Understand the memory landscape

Call `stats(project="{PROJECT}")` to get:
- Total memories (and by type)
- Total edges
- Average connections per memory
- Health alerts

Also call `remember(mode="recent", project="{PROJECT}", limit=10)` to get a sense of what areas are covered.

### Step 2 — Generate test queries

Design 10-20 diverse queries that cover different areas and access patterns. The goal is breadth, not depth.

**Query categories (generate 2-3 per category):**

1. **Architecture queries** — high-level project knowledge
   - "What is the tech stack?"
   - "How is the project structured?"

2. **Specific component queries** — targeted lookups
   - Use real component/file names from stats or recent memories
   - "How does [specific component] work?"

3. **Bug/gotcha queries** — retrieving known pitfalls
   - "Known issues with [area]"
   - "Common bugs in [module]"

4. **Cross-cutting queries** — testing graph propagation
   - Queries that should pull in related memories from different modules
   - "Payment flow end to end"

5. **Vague/broad queries** — testing relevance filtering
   - "Performance issues"
   - "Authentication"

6. **Edge case queries** — areas with sparse coverage
   - Pick areas that might have few memories
   - These reveal content gaps

**Format each query with expected behavior:**
```
Query N: "{query text}"
Mode: {deep|quick}
Expected: should return memories about {topic area}
```

### Step 3 — Execute queries

For each query, call `remember()` and evaluate:

```
remember(query="{query}", mode="{mode}", project="{PROJECT}")
```

**Evaluation criteria per query:**

| Criterion | Score | Description |
|-----------|-------|-------------|
| RELEVANT | 2 pts | Top results are directly relevant to the query |
| PARTIAL | 1 pt | Some relevant results mixed with noise |
| MISS | 0 pts | No relevant results, or all noise |

**Also check:**
- **Noise ratio**: how many of the returned results are irrelevant?
- **Graph effect**: do results include memories that are textually different but structurally related (via graph edges)?
- **Diversity**: do results come from different clusters or are they all from one area?

### Step 4 — Score and report

Calculate overall metrics:

```
=== Smoke Test Results: {PROJECT} ===

Queries tested: N
Score: X/Y points (Z%)

Per-query breakdown:
| # | Query (abbrev)          | Mode  | Score | Notes              |
|---|-------------------------|-------|-------|--------------------|
| 1 | "tech stack architecture"| deep  | 2/2   | Good coverage      |
| 2 | "booking price bug"     | quick | 2/2   | Graph pulled related|
| 3 | "admin panel routes"    | quick | 0/2   | Content gap         |
| ...                                                              |

Coverage map:
- Architecture/stack: GOOD (N memories found)
- Booking flow: GOOD
- Payment/Stripe: GOOD
- Admin panel: WEAK (content gap)
- Email system: MISSING

Recommendations:
- Content gap: {area} — needs extraction or targeted memorize
- Sparse graph: {area} — memories exist but have few edges, needs elaboration
- Noise: {area} — too many vague memories, needs consolidation
```

### Step 5 — Pass/Fail determination

| Overall score | Verdict |
|--------------|---------|
| >80% | PASS — memory system is working well |
| 60-80% | PARTIAL — usable but has gaps, recommend targeted improvements |
| <60% | FAIL — significant issues, recommend health-check and/or additional init phases |

Report the verdict and specific recommendations.

## Notes

- This skill is non-destructive: it only reads, never writes
- Query design matters: bad test queries give meaningless results. Use real terms from the project.
- The skill is also used as steps 8 and 12 during /brain-init
- When used in /brain-init step 12, compare results with step 8 to show improvement
- Keep the report concise but actionable — the user needs to know what to fix, not just what's broken
