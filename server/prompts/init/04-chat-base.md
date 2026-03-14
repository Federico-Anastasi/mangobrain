# MangoBrain — Init Phase 4: Chat Session Extraction

You are the MangoBrain Initializer. This session extracts knowledge from past Claude Code chat sessions (JSONL files in the project's .claude directory).

Phase 1 captured documentation, Phase 2 mapped the codebase, Phase 3 imported existing knowledge. This phase mines the **raw development history** — actual coding sessions where bugs were debugged, features were built, and decisions were made in real time.

You have access to MangoBrain MCP tools.

**Read `prompts/reference/memory-definition.md` FIRST for quality standards.**

---

## Important: Context Window Limits

Chat sessions can be very large (100KB+ each). **Do NOT try to process all sessions in one run.** Process **3-5 sessions per run**, then stop. The user will launch additional runs until all sessions are covered.

---

## Process

### Step 1 — Setup

Ask the user for:
- **project**: project name (e.g., "myproject")
- **project_path**: root path (e.g., "~/projects/myproject")
- **batch**: which sessions to process (e.g., "first batch", "next batch", "sessions 10-15", or "all remaining")

Call `init_project(project, project_path)` to get the session list with sizes and dates.

### Step 2 — Select sessions

From the session list returned by init_project:

**Sorting strategy:**
- Sort sessions by date (newest first)
- Within similar dates, prefer larger sessions (more content = richer extraction)

**Session selection for this batch:**
- Pick **3-5 sessions** based on the user's request
- **Prioritize RECENT sessions** (last 2-4 weeks) — these contain the most current knowledge
- If doing the first batch: select 3 recent + 1-2 older random sessions for historical breadth
- If doing subsequent batches: continue chronologically

**Skip these sessions:**
- Sessions smaller than 5KB (likely trivial interactions — "read this file", "what does X do?")
- Sessions already processed (check `init_project` output for processed flags)

**Report your selection:**
```
Selected sessions (batch N):
1. session_abc123.jsonl — 2025-02-28, 85KB (recent, large)
2. session_def456.jsonl — 2025-02-25, 62KB (recent)
3. session_ghi789.jsonl — 2025-02-20, 45KB (recent)
4. session_jkl012.jsonl — 2025-01-15, 110KB (historical, very large)
5. session_mno345.jsonl — 2024-12-03, 73KB (historical, random)

Remaining unprocessed: <N> sessions
```

### Step 3 — Process each session

For each selected session, follow this exact workflow:

#### 3a. Extract session data
Call `extract_session(session_jsonl_path=<full_path>, project=<project>)`.

This returns:
- `session_id`: unique identifier
- `chat_file_path`: path to a readable text file with the filtered conversation
- `metadata`: date, size, message count

#### 3b. Read the chat file
Use the Read tool with the `chat_file_path` returned by extract_session.

**For large files (>500 lines):** Read in chunks using `offset` and `limit` (200-300 lines per chunk). Process each chunk before reading the next.

**For very large files (>1000 lines):** Use PASS 1 on the first 300 lines to understand the goal, then skim the middle (read every other chunk), then read the last 200 lines for the resolution.

#### 3c. Apply 4-pass extraction

**PASS 1 — Comprehend (read, do NOT extract yet)**

Build context:
- What was the goal of this session? (new feature, bug fix, refactor, exploration?)
- What was the outcome? (success, partial, abandoned?)
- What files were modified?
- What were the major phases? (investigation -> attempt 1 -> failure -> attempt 2 -> success)
- Were there any "aha moments" — places where a non-obvious insight changed the approach?

Write a brief (3-5 line) session summary. This is your guide for extraction.

**PASS 2 — Direct extraction**

Re-read with extraction focus. Create one memory per:

- **Architectural decision**: any choice about structure, patterns, dependencies. Extract the decision AND the rationale (why this over alternatives).
- **Bug root cause + fix**: the WHY matters, not the WHAT. "Booking price showed double" is useless. "formatPrice() divided by 100 twice because the component assumed euros but received cents" is valuable.
- **Non-obvious configuration**: setup steps that required trial and error, environment quirks, version-specific workarounds.
- **Performance discovery**: bottlenecks found and how they were resolved.
- **Integration pattern**: how two systems connect (e.g., Stripe webhook -> booking confirmation -> email notification).
- **Design trade-off**: when multiple approaches were evaluated, capture which was chosen and why the others were rejected.
- **Shared utility created or modified**: if the session creates, modifies, or heavily uses a shared file (lib/, hooks/, helpers/, shared components), create a reference memory with: file path, key exports, what each does, usage pattern. Tag with `"reference"`. Include `file_path` and `code_signature`.
- **Gotcha / trap**: anything that caused confusion or wasted time. These are EXTREMELY valuable — they prevent future sessions from falling into the same trap.

**PASS 3 — Abstract deduction**

Look across the session for:
- Reusable patterns that emerged (not just the specific fix, but the generalizable principle)
- Implicit rules that emerged from debugging (e.g., "always check cents vs euros at boundaries" is a rule that emerges from a price bug)
- Connections to Phase 1-3 memories (does this session confirm, refine, or contradict existing knowledge?)

**PASS 4 — Finalization**

For each memory:
- Content in **English**, 2-5 lines, dense and specific
- Type: episodic (for specific session events), semantic (for generalized knowledge), procedural (for how-to patterns)
- Tags: 3-6 lowercase tags
- `session_id`: from extract_session (so the memory is linked to its source)
- `file_path`: when the memory references a specific file, include relative path
- `code_signature`: for reference memories about shared artifacts
- Relations: link to relevant Phase 1-3 memories using `target_query`

#### 3d. Store memories for this session

Call `memorize()` with:
```json
{
  "memories": [...],
  "session_id": "<session_id from extract_session>",
  "source": "extraction",
  "project": "<project>"
}
```

Batch size: 15-20 memories per call.

### What NOT to extract

- Raw code that was just read (unless it's a shared utility → create a reference memory)
- File contents that were just displayed
- Routine operations ("created file X", "ran npm install", "committed changes")
- Intermediate debugging dead-ends — extract ONLY the final insight, not every wrong turn
- Trivial facts that live in the code itself ("this file has 200 lines")
- Conversation meta ("the user asked me to...", "I suggested...")
- Changes that were immediately reverted or abandoned

### Quality calibration

| Session type | Expected memories |
|-------------|-------------------|
| Trivial (read files, answer questions) | 0-2 |
| Simple bug fix | 2-5 |
| Feature implementation | 5-12 |
| Major refactor | 8-15 |
| Architecture exploration / spike | 3-8 |
| Complex debugging session | 5-10 |

If you're extracting more than 15 from a single session, you may be too granular. If fewer than 3 from a large session, you may be missing things.

---

## Linking to previous phases

Every memory from this phase should have **at least 1 relation** to a Phase 1, 2, or 3 memory. If a chat session memory exists in isolation, it's poorly connected.

Common link patterns:
- Bug fix → reference memory for the affected utility file (`caused_by` or `depends_on`)
- Feature work → convention/rule memory that applies (`depends_on`)
- Architecture decision → project identity or tech stack memory (`relates_to`)
- Gotcha discovered → existing gotcha pattern memory (`relates_to` or `supersedes`)

Use `target_query` with descriptive keywords to match:
```json
{
  "target_query": "dateUtils UTC formatting booking time",
  "relation_type": "depends_on",
  "weight": 0.7
}
```

---

## Report (per batch)

```
=== Init Phase 4 — Batch <N> Complete ===
Project: <name>
Sessions processed: <N>
  - <session_id_1> (<date>, <size>) → <N> memories
  - <session_id_2> (<date>, <size>) → <N> memories
  - ...
Total memories created: <N>
  - episodic: <N>
  - semantic: <N>
  - procedural: <N>
Edges created: <N>

Sessions remaining unprocessed: <N>

Key themes from this batch:
- <theme 1>
- <theme 2>

Next:
- If sessions remain: run again for next batch
- If all done: run Phase 5 (05-elaborate-base.md) for elaboration
```

---

## Multi-run coordination

Since this phase requires multiple runs:

**At the START of each run after the first:**
1. Call `remember(query="init phase 4 sessions processed batch status", project=<project>, mode="recent")` to check what was already done
2. Ask `init_project()` for the full session list and compare with processed ones
3. Select the next unprocessed batch

**At the END of each run:**
1. Create one WIP memory summarizing progress:
```json
{
  "content": "Init Phase 4 progress: processed <N> of <total> sessions across <batch_count> batches. Remaining: <N> sessions. Last batch covered sessions from <date_range>. Key areas covered so far: <areas>.",
  "type": "episodic",
  "tags": ["init", "phase4", "wip", "state"],
  "project": "<project>"
}
```

---

## Usage

```bash
# First batch
claude "Read prompts/init/04-chat-base.md and follow its instructions exactly. Project: myproject, project_path: ~/projects/myproject. Process the first batch."

# Subsequent batches (repeat until all done)
claude "Read prompts/init/04-chat-base.md and follow its instructions exactly. Project: myproject, project_path: ~/projects/myproject. Process the next batch."
```
