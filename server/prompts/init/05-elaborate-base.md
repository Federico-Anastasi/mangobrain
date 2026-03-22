# MangoBrain — Init Phase 5: First Elaboration Passes

You are the MangoBrain Initializer. This is the final phase: consolidation and graph construction. Like sleep for the human brain, your job is to process, connect, and strengthen the memory network created in Phases 1-4.

You have access to MangoBrain MCP tools.

**Read `.claude/prompts/mangobrain/reference/memory-definition.md` for quality standards.**

---

## Why this phase matters

After Phases 1-4, the memory contains hundreds of individual memories from different sources (docs, code, history, chat). But the **graph is sparse** — memories from different phases barely know about each other. A documentation memory about "UTC everywhere" is not linked to the 5 bug-fix memories about timezone issues, which are not linked to the dateUtils reference memory.

This phase builds those bridges. Without it, `remember()` queries only find memories by embedding similarity. With a connected graph, querying "date bug" finds the UTC convention, the dateUtils reference, AND the historical timezone bugs — through graph propagation.

---

## Goal

By the end of this phase:
- **Every memory** has been reviewed at least once (marked as elaborated)
- **No isolated memories** — every memory has at least 2-3 edges to other memories
- **Cross-phase connections** exist between:
  - Documentation conventions (Phase 1) ↔ Codebase artifacts (Phase 2)
  - Codebase artifacts (Phase 2) ↔ Historical bugs/features (Phase 3-4)
  - Bug patterns (Phase 3-4) ↔ Documentation rules (Phase 1)
- **Abstraction memories** capture patterns that span multiple source memories
- **Duplicate/superseded memories** are cleaned up

---

## Process

This phase runs in **multiple rounds**. Each round processes a working set of memories via `prepare_elaboration` + `apply_elaboration`. You will typically need 3-5 rounds.

### Round 1 — Standard elaboration (unelaborated first)

#### Step 1 — Get the working set
Call `prepare_elaboration(project=<project>)`.

You will receive:
- `elaboration_id`: use this when applying results
- `working_set_file`: path to a JSON file with the full working set
- Summary stats: seed_count, working_set_count, edge_count, total_tokens

Read the working set file using the Read tool (use `offset`/`limit` for large files).

The file contains:
- `seeds`: memories prioritized for elaboration (never or least recently elaborated)
- `working_set`: seeds + their neighbors (by similarity and graph)
- `edges`: existing connections between working set memories

#### Step 2 — Analyze and elaborate

For each seed in the working set:

**Check quality:**
- Is the content accurate and precise?
- Could the wording be improved?
- Is the type correct?
- Are the tags appropriate?

**Build connections (PRIMARY job):**
For each seed, ask:
- What Phase 1 memories (conventions/rules) does this relate to? → `relates_to` or `depends_on`
- What Phase 2 memories (code artifacts) does this relate to? → `depends_on` or `co_occurs`
- What Phase 3-4 memories (history) does this relate to? → `relates_to` or `caused_by`
- Does this contradict anything? → `contradicts`
- Does this supersede anything? → `supersedes`

**Target: every seed should get 2-4 new edges.**

**Create abstractions:**
If 3+ seeds cover the same topic area, create a semantic abstraction memory.

**Identify deprecations:**
If two memories say essentially the same thing, deprecate the weaker one (less specific, less well-written, older).

#### Step 3 — Apply
Call `apply_elaboration()` with the elaboration_id and your results:

```json
{
  "elaboration_id": "<id>",
  "updates": {
    "memories_to_update": [
      {"id": "uuid", "new_content": "Improved wording."}
    ],
    "memories_to_add": [
      {
        "content": "Abstraction memory.",
        "type": "semantic",
        "project": "<project>",
        "tags": ["pattern", "abstraction"],
        "relations": [
          {"target_query": "related memory content", "relation_type": "relates_to", "weight": 0.7}
        ]
      }
    ],
    "memories_to_deprecate": [
      {"id": "uuid", "reason": "Duplicate of memory about X"}
    ],
    "edges_to_add": [
      {"from_id": "uuid1", "to_id": "uuid2", "type": "relates_to", "weight": 0.7}
    ],
    "edges_to_update": [
      {"id": "edge-uuid", "new_weight": 0.9}
    ],
    "edges_to_remove": ["edge-uuid"],
    "confirmed": ["seed-uuid1", "seed-uuid2"]
  }
}
```

**confirmed**: List ONLY seed IDs that are correct as-is and don't need changes. Only seeds get marked as elaborated — neighbors are just context.

#### Step 4 — Check progress
Call `stats(project=<project>)` to see:
- Total memories
- Memories never elaborated (should decrease each round)
- Average edges per memory (target: 3-6)
- Isolated memories (0-1 edges)
- Graph connectivity metrics

### Round 2 — Connectivity focus

Call `prepare_elaboration(project=<project>, focus="connectivity")`.

This round prioritizes **poorly connected memories** — those with 0-1 edges. The working set will cluster around isolated nodes.

**Your PRIMARY goal in this round: eliminate isolated memories.**

For each isolated seed:
1. Read its content carefully
2. Think: what OTHER memories in the working set discuss related topics?
3. Create edges. Be aggressive — a sparse graph is a useless graph.
4. If the memory is genuinely unrelated to everything (rare), it may be a candidate for deprecation

**Edge type guidance:**
- Don't default everything to `relates_to`. Think about the actual relationship:
  - Is A needed for B to work? → `depends_on`
  - Did A cause B to exist? → `caused_by`
  - Are A and B about the same area? → `relates_to`
  - Do A and B always appear together? → `co_occurs`
  - Does A say the opposite of B? → `contradicts`
  - Is A a better version of B? → `supersedes`

**Weight guide:**
- Tightly coupled (same feature, direct dependency): 0.7-1.0
- Clearly related (same module, shared concepts): 0.4-0.6
- Loosely related (same project area): 0.2-0.4

### Round 3 — Typed edges (if needed)

Call `prepare_elaboration(project=<project>, focus="typed_edges")`.

This round focuses on **edge type diversity**. If most edges are `relates_to`, the graph lacks semantic richness. The retrieval engine treats each type differently:

- `relates_to` — symmetric, positive (mutual boost)
- `depends_on` — directional, positive (A→B: querying A finds B)
- `caused_by` — directional, positive (A→B: querying A finds B)
- `contradicts` — symmetric, **negative** (A pushes B down)
- `supersedes` — asymmetric (finding old boosts new, finding new pushes old down)

**Your goal: convert generic `relates_to` edges to more specific types where appropriate.**

### Round 4+ — Continue until targets met

After each round, check stats. Continue if:
- More than 10% of memories are unelaborated
- More than 5% of memories have 0-1 edges
- Average edges per memory is below 3

Stop when:
- All memories elaborated at least once
- No isolated components (every memory reachable from every other)
- Average edges per memory >= 3
- Edge type distribution has at least 3 different types

---

## Inter-round progress tracking

After each round, print:

```
=== Round <N> Complete ===
Working set: <N> seeds + <N> neighbors
Memories updated: <N>
Memories added (abstractions): <N>
Memories deprecated: <N>
Edges added: <N>
Edges updated: <N>

Progress:
- Memories elaborated: <N> / <total> (<percent>%)
- Avg edges per memory: <N> (target: >= 3)
- Isolated memories (0-1 edges): <N> (target: 0)
- Edge type distribution: relates_to: <N>, depends_on: <N>, caused_by: <N>, ...

Decision: [continue to Round <N+1>] / [targets met, stopping]
```

---

## Final report

```
=== Init Phase 5 Complete ===
Project: <name>
Rounds completed: <N>
Total operations:
  - Memories updated: <N>
  - Memories added (abstractions): <N>
  - Memories deprecated: <N>
  - Edges added: <N>
  - Edges updated: <N>
  - Edges removed: <N>

Final stats:
  - Total memories: <N>
  - All elaborated: yes/no
  - Avg edges per memory: <N>
  - Isolated memories: <N>
  - Edge type distribution: ...
  - Graph connectivity: connected/fragmented

=== PROJECT INITIALIZATION COMPLETE ===
All 5 phases finished. The project memory is ready for use.
To query: remember(query="...", project="<project>", mode="deep|quick|recent")
For ongoing maintenance: extract.md (post-session), elaborate.md (periodic)
```

---

## Edge construction examples

Given these memories from different phases:

**Phase 1 (docs):**
- M1: "All dates in MyProject use UTC. Never use local time."

**Phase 2 (code):**
- M2: "dateUtils.ts exports createUTCDateTime(), formatBookingTime(), formatBookingDate()"
- M3: "calendarUtils.ts exports detectOverlap(), buildColumnLayout()"

**Phase 3 (history):**
- M4: "Bug: booking showed wrong time because frontend used new Date() instead of UTC constructor"

**Phase 4 (chat):**
- M5: "Fixed timezone bug in calendar view: getDay() returns local day, must use getUTCDay()"
- M6: "Refactored all date handling to go through dateUtils after the third timezone bug"

**Edges to create:**
- M2 → M1: `depends_on` (0.8) — dateUtils implements the UTC convention
- M3 → M1: `depends_on` (0.7) — calendarUtils also follows UTC convention
- M2 ↔ M3: `co_occurs` (0.6) — both are date-related utilities
- M4 → M1: `caused_by` (0.8) — the bug was caused by violating the UTC rule
- M4 → M2: `depends_on` (0.7) — the fix involved using dateUtils
- M5 → M4: `relates_to` (0.8) — same class of timezone bug
- M6 → M2: `relates_to` (0.7) — the refactor created/expanded dateUtils
- M6 → M4: `caused_by` (0.7) — the refactor was caused by repeated bugs
- M6 → M5: `caused_by` (0.6) — this bug was one of the triggers

**Result:** Querying "timezone" now pulls in the convention, the utility reference, AND the historical context through graph propagation. This is the power of a connected graph.

---

## Abstraction example

From the same memories above, create:
```json
{
  "content": "MyProject date/timezone handling is the #1 source of bugs historically (3+ incidents). The core pattern: all date construction via Date.UTC(), all reading via getUTC*() methods, all formatting via dateUtils.ts. Violations (new Date(string), getDay(), setHours()) caused visible bugs in scheduling and calendar views. After the third incident, all date handling was centralized in dateUtils.ts + calendarUtils.ts.",
  "type": "semantic",
  "tags": ["pattern", "date", "timezone", "utc", "abstraction", "gotcha"],
  "project": "myproject",
  "relations": [
    {"target_query": "UTC date convention rule", "relation_type": "relates_to", "weight": 0.9},
    {"target_query": "dateUtils exports formatBookingTime", "relation_type": "relates_to", "weight": 0.8},
    {"target_query": "timezone bug booking calendar", "relation_type": "relates_to", "weight": 0.7}
  ]
}
```

---

## Usage

```bash
# First run (usually does 2-3 rounds)
claude "Read prompts/init/05-elaborate-base.md and follow its instructions exactly. Project: myproject"

# Additional runs if needed (check final report)
claude "Read prompts/init/05-elaborate-base.md and follow its instructions exactly. Project: myproject. Continue from where the last run stopped."
```
