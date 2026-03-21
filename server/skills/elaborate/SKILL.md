# /elaborate — Memory Elaboration Cycle

Runs a memory elaboration cycle: consolidates, reorganizes, and strengthens the memory network. Like sleep for the brain.

## When to use
- Weekly maintenance (recommended cadence)
- After a burst of new memories (e.g., post-init, after several sessions)
- When /health-check prescribes structural improvements
- When the user says "/elaborate", "elabora", "consolida memorie", or similar

## Input
- **project**: project name (ask if not provided)
- **focus** (optional): specific area to focus on (e.g., "typed_edges", "contradicts", "booking module")
- **focus_instructions** (optional): additional context for the focus (e.g., from diagnose prescriptions)
- **seed_count** (optional): number of seed memories to process (default: 50)

## Setup

**BEFORE analyzing or creating any memory**, read the quality reference:
- `.claude/prompts/mangobrain/reference/memory-definition.md` — canonical definition of what a memory is, quality standards, types, tags, relations, examples

This is especially important for Step 4 when creating abstracted patterns and updating existing memories.

## Workflow

### Step 1 — Get the working set

Call `prepare_elaboration()` with the provided parameters:

```
prepare_elaboration(
    project="{PROJECT}",
    seed_count={seed_count or 50},
    focus="{focus}",                    # if provided
    focus_instructions="{focus_instructions}"  # if provided
)
```

You will receive:
- `elaboration_id`: ID for apply_elaboration
- `working_set_file`: path to a JSON file with the full working set
- Summary stats: seed_count, working_set_count, edge_count, total_tokens

If the working set is empty or too small (<5 seeds), report that and stop.

### Step 2 — Read the working set

Read the working set file with the Read tool. Use `offset` and `limit` to read in chunks if needed (large files).

The file contains:
- `seeds`: memories prioritized for elaboration (never or least recently elaborated)
- `working_set`: seeds + their neighbors (by similarity and graph connections)
- `edges`: existing connections between working set memories
- `focus` (optional): prioritized instructions for this round

### Step 3 — Check focus

If the working set contains a `focus` section:
- Read both `focus.template_instructions` (system-generated) and `focus.custom_instructions` (from Claude/user)
- Allocate **70% of effort** to the focus area
- Remaining 30% follows general elaboration

If no focus, proceed with general elaboration.

### Step 4 — Analyze the working set

Group memories into thematic clusters. For each cluster:

**Re-evaluate each memory:**
- Is the content still accurate and precise?
- Could the wording be improved for clarity?
- Is the type correct (episodic/semantic/procedural)?
- Are the tags appropriate?

**Build the graph — PRIMARY job:**

The graph is what makes MangoBrain different from generic RAG. A well-connected graph enables retrieval to find memories that are semantically distant but structurally related. **Every memory should have 3-6 edges.** If a memory has 0-1 edges, actively search for connections.

For each memory, ask:
- What does this **depend on**? (`depends_on` — directional)
- What **caused** this to exist? (`caused_by` — directional)
- What other memories discuss the **same topic area**? (`relates_to` — symmetric)
- Does this **contradict** anything? (`contradicts` — symmetric, negative in retrieval)
- Does this **replace** an older memory? (`supersedes` — asymmetric)

**Edge type guide:**
| Type | Direction | Retrieval effect | Use for |
|------|-----------|-----------------|---------|
| `relates_to` | symmetric | mutual boost | same-topic connections |
| `depends_on` | A -> B | querying A finds B | component->utility, feature->config |
| `caused_by` | A -> B | querying A finds B | bug->decision, refactor->incident |
| `co_occurs` | symmetric | auto-managed | DO NOT create manually |
| `contradicts` | symmetric | negative (A pushes B down) | conflicting info, outdated vs current |
| `supersedes` | asymmetric | old boosts new, new pushes old down | one memory clearly more current |

**Weight guide:**
- Tightly coupled (same feature, direct dependency): 0.7-1.0
- Clearly related (same module, shared concepts): 0.4-0.6
- Loosely related (same project area): 0.2-0.4

**Abstract patterns:**
- Do 3+ episodic memories point to a common pattern? Create a semantic memory.
- Are there procedural sequences spread across multiple memories? Consolidate.
- Can domain-specific knowledge be generalized?

**Identify deprecations:**
- Superseded by newer, more complete versions
- Factually wrong based on later discoveries
- Duplicates (keep the better one)

### Step 5 — Apply results

Call `apply_elaboration()` with:
```json
{
  "elaboration_id": "<from step 1>",
  "updates": {
    "memories_to_update": [
      { "id": "uuid", "new_content": "Improved version." }
    ],
    "memories_to_add": [
      {
        "content": "New abstracted pattern.",
        "type": "semantic",
        "project": "projectname",
        "tags": ["tag1", "tag2"],
        "relations": [
          { "target_query": "search string", "relation_type": "relates_to", "weight": 0.8 }
        ]
      }
    ],
    "memories_to_deprecate": [
      { "id": "uuid", "reason": "Superseded by newer version" }
    ],
    "edges_to_add": [
      { "from_id": "uuid1", "to_id": "uuid2", "type": "relates_to", "weight": 0.7 }
    ],
    "edges_to_update": [
      { "id": "edge-uuid", "new_weight": 0.9 }
    ],
    "edges_to_remove": ["edge-uuid"],
    "confirmed": ["uuid1", "uuid2"]
  }
}
```

**Rules:**
- `confirmed` should list ONLY seed IDs that are correct as-is. Only seeds get marked as elaborated. Neighbors are context — do NOT confirm them.
- Confirm generously: well-written seeds that need no changes should be confirmed so they don't keep coming back.

### Step 6 — Report

Show a summary to the user:

```
=== Elaboration Complete ===
Memorie revisionate: N
Memorie aggiornate: N (with what changed)
Nuove memorie create: N (abstractions)
Memorie deprecate: N
Edge aggiunti: N
Edge aggiornati: N
Edge rimossi: N
Pattern scoperti:
- {pattern 1}
- {pattern 2}
```

## Guidelines

- **Be conservative with deprecation.** Only deprecate when truly outdated or redundant.
- **Be aggressive with edges.** A sparse graph is useless. Target 3-6 edges per memory. The graph is the core differentiator.
- **Use typed edges correctly.** Don't default everything to `relates_to`. Think about the relationship.
- **Abstracted memories must be self-contained.** Readable without the source episodic memories.
- **Confirm generously.** Well-written seeds should be confirmed so they rotate out.
- One elaboration round processes ~50 seeds + ~150 neighbors. Multiple rounds may be needed for large backlogs.
