# /memorize — End-of-Session Memory Sync

Syncs the work done in a free session (not using /task) into MangoBrain memory.

## When to use
- End of any session where you did meaningful work without /task
- When the user says "sync memory", "/memorize", "salva in memoria", or similar
- Before closing a long discussion session that produced decisions or insights

## Prerequisites
- MangoBrain MCP server running
- Project has been initialized (has memories)

## Input
- **project**: infer from the current working directory or ask
- **project_path**: infer from the current working directory or ask

## Workflow

### Step 1 — Generate session summary

Review the current conversation and produce a structured summary:

**What was done:**
- List the main activities (features built, bugs fixed, discussions had, decisions made)
- Be specific: include component names, file names, concepts discussed

**Decisions made:**
- Architectural decisions with rationale
- Trade-offs evaluated and chosen direction
- Conventions established or changed

**Files changed:**
- Run `git diff --name-only HEAD` (or `git diff --name-only` if no commits) in the project directory
- If no git changes (e.g., discussion-only session), note "no file changes"

**WIP / Blockers:**
- Any incomplete work that the next session needs to know about
- Blockers or open questions
- Things to investigate next

### Step 2 — Read the mem-manager agent prompt

Read the mem-manager agent prompt from the MangoBrain package (installed via `mango-brain install`).

This contains the full mem-manager workflow instructions.

### Step 3 — Spawn the mem-manager as sub-agent

Spawn a general-purpose sub-agent with the following prompt (fill in the variables):

```
You are the mem-manager for project {PROJECT}.

{INSERT FULL CONTENT OF mem-manager.md HERE}

## Input for this session

### Summary
{summary from Step 1}

### Changed files
{file list from Step 1, or "none — discussion session"}

### Decisions
{decisions from Step 1, or "none"}

### WIP
{wip from Step 1, or "none"}

### Project info
- project: {PROJECT}
- project_path: {PROJECT_PATH}
```

The mem-manager sub-agent will autonomously:
1. Create memories for significant work (memorize)
2. Sync changed files with existing memories (sync_codebase + update_memory)
3. Create WIP memories if needed (memorize with tag "state", "wip")

### Step 4 — Report results

When the mem-manager completes, show the user a concise report:

```
=== Memory Sync Complete ===
Memorie create: N
Memorie aggiornate: N
File sincronizzati: N
WIP registrato: si/no
```

If the mem-manager encountered issues (e.g., stale memories it couldn't resolve, orphan files), report those too.

## Notes

- The mem-manager sub-agent does ALL the MangoBrain writes. The main agent only prepares the summary.
- Keep the summary dense but complete. The mem-manager needs enough context to create good memories.
- For discussion-only sessions (no code changes), the mem-manager still creates memories for decisions and insights.
- The mem-manager follows the memory-definition.md quality standards: 2-5 lines, English, self-contained, atomic.
- If the session was trivial (quick question, no decisions, no work), tell the user there's nothing worth memorizing and skip.
