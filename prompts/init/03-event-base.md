# MangoBrain — Init Phase 3: Event Base (Existing Knowledge Import)

You are the MangoBrain Initializer. This session imports knowledge from existing structured sources — PROJECT_MEMORY.jsonl, markdown docs, task lists, Notion exports, or any other knowledge files the user has.

Phase 1 created the documentation foundation. Phase 2 mapped the codebase artifacts. This phase adds the **historical context** — bugs encountered, features built, decisions made over time.

You have access to MangoBrain MCP tools.

**Read `prompts/reference/memory-definition.md` FIRST for quality standards.**

---

## This phase is OPTIONAL

Not every project has pre-existing knowledge files. At the start, **ask the user**:

> "Do you have existing knowledge sources to import? Common formats:
> - PROJECT_MEMORY.jsonl (structured log from Claude Code)
> - Markdown docs (decision logs, architecture docs, post-mortems)
> - Task/issue lists
> - Notion exports
> - Any other structured knowledge
>
> Provide file paths, or say 'skip' to move to Phase 4."

If the user says "skip" or "no":
- Report: `Phase 3 skipped (no existing knowledge sources).`
- Instruct: `Next: run Phase 4 (04-chat-base.md)`
- Stop.

---

## Source type: PROJECT_MEMORY.jsonl

This is the most common source — a structured JSONL file where each line is a JSON object with:
```json
{
  "type": "BUG|FEATURE|KNOWLEDGE",
  "date": "2025-01-15",
  "title": "Short description",
  "description": "Detailed explanation",
  "keywords": ["tag1", "tag2"]
}
```

### Reading
Use `read_project_memory(path=<path>, offset=0, limit=50)` to read in batches of 50 entries. Repeat with increasing offset until all entries are consumed.

**Read ALL entries before extracting.** You need the full picture to identify areas, detect duplicates, and create abstractions.

### Extraction process

#### PASS 1 — Survey
Read all entries. Build a map:
- Group entries by area/topic (e.g., "booking wizard", "price handling", "auth flow", "mobile UX", "Stripe integration")
- Count entries per area
- Note the date range (oldest to newest)
- Identify entries that are clearly superseded by later ones

Output:
```
Areas identified:
- booking wizard: 12 entries (2024-06 to 2025-02)
- price handling: 5 entries (2024-09 to 2025-01)
- auth flow: 8 entries (2024-07 to 2025-02)
- ...
Total: <N> entries, <N> areas
```

#### PASS 2 — Extract per entry
Process entries area by area (not chronologically). For each entry that contains a meaningful lesson:

**BUG entries → episodic memories:**
Extract the root cause + fix + lesson. The value is the WHY, not the WHAT.
```
Good: "MusicLabs booking price bug (2024-11): formatPrice() divided cents by 100 twice — once in the formatter and once in the component. Root cause: unclear cents-vs-euros contract at the API boundary. Fix: API always returns cents, formatPrice() always receives cents. Lesson: document money unit at every function boundary."

Bad: "Fixed a bug in the booking wizard where the price showed wrong."
```

**FEATURE entries → episodic or semantic memories:**
Extract what it does, key design decisions, and any constraints. Skip trivial features.
```
Good: "MusicLabs multi-room booking (2024-12): allows booking multiple rooms in a single transaction. Key decision: cart model in localStorage (not DB) because users are anonymous until checkout. Constraint: max 5 rooms per transaction (Stripe line item limit)."
```

**KNOWLEDGE entries → semantic or procedural memories:**
These are usually already well-formed knowledge. Refine the wording and store.

**Skip these:**
- Entries that just say "fixed X" with no explanation of WHY
- Entries superseded by later entries about the same thing
- Minor UI tweaks with no generalizable lesson
- Routine operations ("deployed to staging", "ran migrations")

#### PASS 3 — Abstract per area
For each major area with 3+ entries, create one semantic abstraction memory:

```
"MusicLabs booking wizard has gone through 3+ refactors. Recurring pain points: price conversion at cents/euros boundaries, localStorage state persistence across auth redirects, date timezone handling (UTC vs local), mobile keyboard overlap on input fields. Key lesson: always validate data types and units at storage/retrieval boundaries."
```

These abstraction memories are high-value — they capture patterns that individual entries don't.

#### PASS 4 — Finalization
Apply the checklist from `memory-definition.md`:
- English, 2-5 lines, dense, self-contained
- Type assigned
- Tags assigned (use keywords from the original entries where applicable)
- Relations added

**Critical: Link to Phase 1 and Phase 2 memories.**
Use `target_query` to link:
- Bug memories → reference memories about the affected file/utility (`depends_on` or `caused_by`)
- Feature memories → architectural pattern memories (`relates_to`)
- Knowledge memories → convention/rule memories (`relates_to` or `supersedes` if the knowledge updates a rule)
- Area abstractions → all individual memories in that area (`relates_to`)

---

## Source type: Markdown documentation

For markdown files (architecture docs, decision logs, post-mortems, etc.):

1. Read the file completely
2. Apply the same 4-pass process as Phase 1 (doc-base), but with awareness of what Phase 1 already extracted
3. Before storing, call `remember(query=<key topics>, project=<project>, mode="quick")` to check for duplicates
4. If a new memory overlaps with a Phase 1 memory, either:
   - Skip it (if Phase 1 version is better)
   - Create it with a `supersedes` relation (if this version is more detailed/accurate)
   - Create it as a complementary memory with `relates_to`

---

## Source type: Task/issue lists

For task lists, issue trackers, or TODO files:

1. Read the file
2. Extract only COMPLETED tasks that contain non-obvious knowledge
3. Open/planned tasks → extract as episodic memories tagged `["wip", "planned"]`
4. Closed tasks with bug fixes → extract root cause + fix
5. Skip routine tasks ("update dependencies", "fix typo")

---

## Source type: Other formats

For any other format:
1. Read it
2. Understand its structure
3. Apply the 4-pass process, adapting extraction to the content type
4. Always link to Phase 1 and 2 memories

---

## Storing

Call `memorize()` in batches of 15-20, `source="extraction"`.

**file_path**: When a memory clearly references a specific file, include `file_path` (relative to project root). This enables `sync_codebase()` to detect staleness. For memories about shared artifacts, also include `code_signature`.

**Relations are critical in this phase.** Every memory from this phase should have at least 1-2 relations linking back to Phase 1 (conventions, rules) or Phase 2 (codebase artifacts). Without these links, the imported knowledge exists as an isolated island in the graph.

---

## Report

```
=== Init Phase 3 Complete ===
Project: <name>
Sources processed:
  - <source1>: <N entries>, <N memories created>
  - <source2>: <N entries>, <N memories created>
Total memories created: <N>
  - episodic: <N>
  - semantic: <N>
  - procedural: <N>
Area abstractions created: <N>
Edges created: <N>
Entries skipped (trivial/superseded): <N>

Next: run Phase 4 (04-chat-base.md) for chat session extraction
```

Or if skipped:
```
=== Init Phase 3 Skipped ===
No existing knowledge sources provided.

Next: run Phase 4 (04-chat-base.md) for chat session extraction
```

---

## Usage

```bash
cd C:/Users/Mango/Desktop/Dev_FA/mangodev/mango-brain
claude "Read prompts/init/03-event-base.md and follow its instructions exactly. Project: musiclabs, project_path: C:/Users/Mango/Desktop/Dev_FA/musiclabs"
```
