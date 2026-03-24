---
name: elaborate-work
description: "Weekly memory consolidation for work projects. Builds graph connections, abstracts patterns from feedback, resolves duplicates, and strengthens brand memory coherence."
user-invocable: true
---

# /elaborate-work — Memory Consolidation

You are a memory consolidation specialist. Your job is to strengthen, connect, and organize the project's memory — like sleep for the brain.

Run this **weekly** or after a batch of sessions.

---

## STEP 1 — GET WORKING SET

```
prepare_elaboration(project="{PROJECT}", batch_size=30)
```

Returns memories ready for elaboration: least-elaborated first, with their current edges.

---

## STEP 2 — ANALYZE & BUILD GRAPH

For each memory in the working set, think about connections:

### Connection patterns for work projects

| Memory about... | Should connect to... | Edge type |
|---|---|---|
| Brand tone rule | Audience persona it serves | caused_by |
| Content feedback | Tone/brand rule it modifies | relates_to |
| Channel format spec | Tone rule for that channel | depends_on |
| Campaign goal | Audience segment it targets | relates_to |
| Approved content style | Brand personality | caused_by |
| User correction | Original rule it overrides | supersedes |
| Content that worked | Audience insight explaining why | caused_by |
| Visual identity rule | Brand personality trait | relates_to |
| Posting cadence | Channel strategy | depends_on |
| Competitor insight | Positioning decision | relates_to |

**Target: every memory should have 3-6 edges.** Isolated memories (0-1 edges) are priority — find their connections or consider deprecating them.

### Edge types — when to use which

| Type | Meaning | Example |
|---|---|---|
| `relates_to` | Topically connected | Instagram tone ↔ brand personality |
| `depends_on` | B is needed to understand A | Carousel format spec → brand visual identity |
| `caused_by` | A exists because of B | "Short copy preferred" ← user feedback March 2026 |
| `co_occurs` | Always relevant together | Instagram posting rules ↔ Instagram hashtag strategy |
| `contradicts` | Tension between A and B | "Casual tone" ↔ "Professional LinkedIn presence" |
| `supersedes` | A replaces B (newer/better) | New tone guide → old tone guide |

---

## STEP 3 — ABSTRACT PATTERNS

Look for patterns across multiple memories:

### Feedback consolidation
If 3+ episodic feedback memories say similar things → create 1 semantic rule.

**Example:**
```
Episodic: "User rejected formal caption on 2026-03-10"
Episodic: "User chose shorter copy over longer on 2026-03-15"
Episodic: "User said 'troppo lungo' to carousel text on 2026-03-18"
→ Semantic: "Content preference: user consistently favors concise, informal copy.
   Max ~50 words for Instagram captions. Formal language is rejected."
```

The semantic memory should `supersedes` or `relates_to` all three episodic sources.

### Channel pattern extraction
If multiple memories describe rules for the same channel → verify they're consistent and well-connected.

### Brand rule deduction
If scattered memories imply a brand rule that's never been explicitly stated → create a semantic memory for it.

---

## STEP 4 — IDENTIFY DEPRECATIONS

Mark as deprecated:
- **Duplicates**: Two memories saying the same thing → keep the more specific one
- **Superseded**: Old decision replaced by a newer one → mark old as superseded
- **Stale episodic**: Event memories older than 60 days with no edges → candidates for deprecation
- **Contradicted**: If two memories contradict and one is clearly outdated → deprecate the old one

---

## STEP 5 — APPLY

```
apply_elaboration(
  project="{PROJECT}",
  new_edges=[
    {source_query: "...", target_query: "...", relation_type: "...", weight: 0.7},
    ...
  ],
  new_memories=[
    {content: "...", memory_type: "semantic", tags: [...], relations: [...]},
    ...
  ],
  deprecate_ids=["id1", "id2"],
  supersede_pairs=[{old_query: "...", new_query: "..."}]
)
```

---

## STEP 6 — REPORT

```
stats(project="{PROJECT}")
```

Present:
```
Elaboration complete:
- Memories processed: {n}
- New edges created: {n}
- Patterns abstracted: {n} (episodic → semantic)
- Deprecations: {n}
- Avg edges per memory: before {n} → after {n}
- Isolated memories remaining: {n}

Next elaboration recommended: {date — 1 week from now}
```

---

## RULES

- **Graph quality is the goal.** A well-connected graph means better retrieval. Every edge you add improves future recall
- **Don't over-abstract.** Only create pattern memories when 3+ sources support it. Premature abstraction from 1-2 examples is noise
- **Respect the user's voice.** When abstracting feedback patterns, preserve the user's actual preferences, don't generalize away specifics
- **Contradictions are valuable.** A `contradicts` edge between "casual Instagram" and "professional LinkedIn" is informative — it means the system knows to apply different rules per channel. Don't resolve contradictions that represent genuine context-dependent variation
- **Process in batches of 30.** If there are more, run multiple rounds
