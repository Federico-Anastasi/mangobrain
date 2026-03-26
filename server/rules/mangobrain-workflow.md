# MangoBrain — Workflow Integration

MangoBrain provides persistent associative memory across Claude Code sessions. This rule describes how and when to use it in daily workflow.

## Server

MangoBrain requires the server to be running. If the user asks to start it or if MCP tools are not responding:
```
mangobrain serve --api    # start server + dashboard (http://localhost:3101)
```
Run it in the background. If the server is already running, no need to restart.

## Overview

MangoBrain is not a file to read at the start. It's an active retrieval system: ask for what you need, when you need it. Memories contain past bugs, architectural decisions, patterns, gotchas, references to utilities and components — knowledge that code alone doesn't communicate.

## Query Language

**All remember() queries MUST use English keywords**, regardless of session language.
Memories are stored in English — queries in other languages degrade retrieval by ~15-20%. The conversation stays in the user's language, but queries go to the DB in English.

## Integration with /discuss

**INTAKE** (start of discussion):
1. `remember(mode="recent")` — recent context, WIP, decisions
2. Identify 2-3 technical areas of the topic
3. `remember(mode="deep", query="[topic in max 10 keywords]")` — big picture
4. 1-2x `remember(mode="quick", query="[specific names per area]")` — targeted details
5. Show relevant memories to the user as context

**EXPLORE** (code analysis):
- The analyzer explores the code, enriched by memory context
- If an unexplored area emerges, do a quick query before responding

**BRAINSTORM** (discussion):
- Memories inform the brainstorm:
  - Past bugs in the same area: "careful, last time..."
  - Architectural decisions: "this was decided because..."
  - Consolidated patterns: "the pattern used elsewhere is..."

## Integration with /task

**ANALYZE** (task start):
1. `remember(mode="recent")` — WIP, context
2. Multi-query strategy (1 deep + N quick) — see mangobrain-remember.md
3. Memories guide the analysis: you already know gotchas, patterns, available utilities

**Mid-task** (during development):
- Before touching a new area: quick query
- When you find a bug: quick query for known patterns
- Before creating a component: quick query to check if something similar exists

**CLOSE** (end of task):
The main orchestrator spawns the **mem-manager** as a sub-agent with:
- Summary of work done
- List of modified files (git diff)
- Decisions made
- WIP/blockers

The mem-manager autonomously:
1. Creates memories for significant work (memorize)
2. Syncs changed files with existing memories (sync_codebase + update_memory)
3. Records WIP if present (memorize with tags "state", "wip")

## Free sessions (without /task)

For sessions without /task (discussions, explorations, quick fixes):
- Use `remember` during the session as described above
- At end of session, use **/memorize** to sync work to memory
- /memorize prepares a summary and spawns the mem-manager

## Periodic maintenance

| Activity | Frequency | Skill | What it does |
|----------|-----------|-------|--------------|
| Elaboration | Weekly | /elaborate | Consolidates, creates edges, abstractions, deprecates duplicates |
| Health check | Monthly | /health-check | Diagnosis of structure + content, targeted fixes |
| Smoke test | Post-init, post-elaboration | /smoke-test | Verifies retrieval quality with test queries |

## The mem-manager agent

The mem-manager is a specialized sub-agent for memory management. It's not interactive — it's spawned by main with precise context and operates autonomously.

**What it does:**
- Creates atomic memories (2-5 lines, English, self-contained)
- Classifies: episodic (events), semantic (facts), procedural (how-to)
- Tags: 3-6 lowercase tags
- Adds relationships between memories (relates_to, depends_on, caused_by)
- Syncs changed files with existing memories
- Records WIP for the next session

**What it does NOT do:**
- Does not interact with the user
- Does not make architectural decisions

## When NOT to use memory

- **Purely mechanical tasks**: "rename this variable", "add an import"
- **One-line fixes**: if the fix is obvious and there's no lesson to learn
- **Routine operations**: npm install, docker restart, git merge
- **When context is entirely in the task**: if the task is self-contained and doesn't touch complex areas

The rule: if the work doesn't produce reusable knowledge, it doesn't need to be memorized.
