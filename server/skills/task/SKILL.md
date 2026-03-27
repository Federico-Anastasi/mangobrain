---
name: task
description: Orchestrates complete task execution using specialized agents (analyzer, executor, verifier, mem-manager) with MangoBrain memory integration. Use for implementing features, fixing bugs, refactoring.
argument-hint: <task description or path to task.md file>
---

# Skill: /task

Orchestrates task execution using specialized agents. Each agent reads CLAUDE.md +
rules (knows project conventions) and produces structured output. MangoBrain memory
provides persistent context — patterns, gotchas, decisions from past sessions.

Main is the orchestrator. Agents are the specialists.

---

## Operating Principles

### Main vs Agent Responsibilities

| Main does directly                          | ALWAYS delegate to agents            |
|---------------------------------------------|--------------------------------------|
| `Read`, `Grep`, `Glob` — quick lookups      | Modify files → **executor**          |
| User interaction — clarifications            | Build/test → **verifier**            |
| `Task` — coordinate agents                  | Deep analysis → **analyzer**         |
| Create PLAN (atomic task list)               | Memory operations → **mem-manager**  |
| `remember()` — memory retrieval (ANALYZE)    |                                      |

### Phase Rules

- **ANALYZE**: ALWAYS run (skip only if <10 lines, 1 file, obvious pattern). Start with `remember()` multi-query. Spawn analyzer(s). Most tasks → 1 analyzer. Large FE+BE → 2-3 parallel.
- **PLAN**: Create atomic task list + decide agent distribution. Saturate agents (~60k load). Show plan → ask confirmation (text input) or auto-approve (task.md input).
- **EXECUTE**: 1 line across 10 files → 1 executor. 10 files from scratch → 2 executors (if disconnected). Most tasks → 1-2 executors TOTAL. Max 2 retries, then escalate.
- **VERIFY**: Spawn verifier ALWAYS (even for refactoring). Confidence-based retry.
- **CLOSE**: Spawn mem-manager ALWAYS. Memorizes new knowledge, syncs changed files, registers WIP if incomplete.

**Agent model rule**: ALWAYS specify `model: "sonnet"` when spawning ANY agent.

### Agent Tool Access

| Agent | Read | Grep | Glob | Edit | Write | Bash | remember | memorize | sync_codebase | update_memory |
|-------|------|------|------|------|-------|------|----------|----------|---------------|---------------|
| **analyzer** | Y | Y | Y | - | - | - | Y (quick) | - | - | - |
| **executor** | Y | - | - | Y | Y | Y | - | - | - | - |
| **verifier** | Y | - | - | - | - | Y | Y (quick) | - | - | - |
| **mem-manager** | Y | - | - | - | - | - | Y | Y | Y | Y |

Key design:
- **executor** has NO memory tools — 100% code focus, receives all context from Main
- **analyzer** has `remember(quick)` — targeted lookups during exploration
- **verifier** has `remember(quick)` — check for known issues/gotchas
- **mem-manager** has full memory access — sole agent for persisting knowledge

### Saturation Strategy

Each agent should handle ~40-60k tokens of work. Assign multiple tasks to the same
agent rather than spawning many agents with tiny tasks.

| Task Size | Analyzers | Executors | Notes |
|-----------|-----------|-----------|-------|
| Small fix (same pattern, <10 files) | 1 | 1 | Most common case |
| Medium feature (10 files, 30-40k) | 1 | 1 | Saturates 1 executor |
| Large feature, single domain (20 files) | 1 | 1-2 seq | Split only if >60k |
| Large FE + BE (25+ files, domains disconnected) | 2 parallel | 2 parallel | FE and BE independent |
| Migration + dependent update | 1 | 1 | Keep together — executor retains context from migration |

**When to split executors**: Only when domains are truly disconnected (FE vs BE).
If tasks are dependent (migration → backend update), keep them in one executor —
it retains context from the first task and stays coherent. The only exception: if
migration + BE update + FE update are all large, group migration with BE (same
domain) and give FE to a separate executor.

**Never 1 agent per file** — saturate agents with multiple tasks.

---

## Trigger

```
/task <task description>
/task <path-to-task-file.md>
```

Examples:
- `/task Add email validation to registration form`
- `/task Fix bug: price filter not working`
- `/task .claude/tasks/2026-03-14-1430-add-google-oauth.md`

---

## Input Detection

**BEFORE starting, determine input type:**

### Type 1: Text Description

Input does NOT end with `.md`.

**Workflow**: `INTAKE (Q&A) → ANALYZE → PLAN → EXECUTE → VERIFY → CLOSE`

- INTAKE: Ask user questions to clarify requirements
- PLAN: Show plan, ask for confirmation

### Type 2: Task File from /discuss

Input ends with `.md`.

**Workflow**: `INTAKE (read file) → ANALYZE → PLAN → EXECUTE → VERIFY → CLOSE`

- INTAKE: Read and parse task.md (no questions — already answered in /discuss)
- PLAN: Auto-approve (already confirmed in /discuss)

#### INTAKE for Task File

**CRITICAL**: Task.md is a "decisional record" from /discuss. Contains WHAT/WHY
decisions, but /task must do its own ANALYZE and PLAN autonomously.

1. **Validate path**: File must exist
2. **Read and parse** sections: Goal, Context, Memory Context, Chosen Approach,
   Requirements, Constraints, Known Risks, Verification Criteria, Hints
3. **Check freshness**: If >24h old, warn user and ask whether to proceed
4. **No questions to user** (already answered in /discuss)
5. **Task.md is reference, not substitute**: Hints suggest where to look,
   but ANALYZE MUST verify fresh codebase. Code may have changed.

### Comparison

| Phase | Text Input | Task File Input |
|-------|------------|-----------------|
| **INTAKE** | Q&A with user | Read file (no questions) |
| **ANALYZE** | Identical | Identical (task.md = hints, not substitute) |
| **PLAN** | Ask user confirmation | Auto-approve |
| **EXECUTE** | Identical | + Requirements/Constraints from task.md |
| **VERIFY** | Identical | + Verification criteria from task.md |
| **CLOSE** | Identical | Mentions task.md as source |

---

## Pre-condition: MangoBrain Availability Check (MANDATORY)

**BEFORE starting any phase**, call `ping()` to verify MangoBrain is online.

```
ping()
```

**Interpret the response:**
- `{"status": "ok", "model_loaded": true}` → Proceed normally.
- `{"status": "degraded", ...}` → Partially available. Inform user, ask whether to proceed without memory.
- **Timeout / connection error / no response** → MangoBrain is **offline**. **STOP** and inform the user:

```
⚠️ MangoBrain is not responding. Memory context will not be available for this task.

Options:
1. Proceed without memory (analysis and execution will work, but no memory context or sync)
2. Abort and fix MangoBrain first (run: mangobrain serve)

Which do you prefer?
```

**Do NOT silently continue.** The user must explicitly authorize proceeding without memory.

If user authorizes: set `MANGOBRAIN_OFFLINE = true`. Skip all `remember()` calls in ANALYZE, skip `remember()` in agent spawns (pass `mangobrain_available: false` to agents), and skip CLOSE phase entirely (inform user: "Run /memorize later to sync this work to memory.").

---

## Workflow Overview

| Phase | Key Actions | Output |
|-------|-------------|--------|
| **INTAKE** | Parse request. Text: Q&A. Task.md: read file. | Clear task description |
| **ANALYZE** | Main: `remember()` multi-query. Spawn analyzer(s) with memory context. | Files, patterns, risks, memory insights |
| **PLAN** | Create atomic task list. Decide agent distribution. Text: ask confirm. Task.md: auto-approve. | Approved plan |
| **EXECUTE** | Spawn executor(s). Pass analyzer output + memory constraints. | Modified files, status |
| **VERIFY** | Spawn verifier. Build/test/lint. Verifier calls `remember(quick)` for known issues. | Verification report |
| **CLOSE** | Spawn mem-manager. `memorize()`, `sync_codebase()`, `update_memory()`, register WIP. | Memory ops report |

---

## Skip Logic — Strict Rules

| Phase | Can skip? | Only if... |
|-------|-----------|------------|
| **ANALYZE** | Rarely | <10 lines, 1 file, obvious pattern. Must document WHY. |
| **PLAN** | Informal only | 1 step, 1 file. Quick inline confirm. |
| **VERIFY** | NEVER | Not even for refactoring. |
| **CLOSE** | NEVER | Memory is sacred. |

**User says "go/proceed"**: Skips ONLY the post-PLAN confirmation. Does NOT skip
ANALYZE/VERIFY/CLOSE.

**Analysis-only task** (research/exploration): Skip EXECUTE and VERIFY. Go directly
to CLOSE after ANALYZE.

---

## Phase 2: ANALYZE — Memory + Code Exploration

### Step 1: Main retrieves memory context

**This happens BEFORE spawning analyzers.** Main does the retrieval so it can pass
relevant context to agents.

Run the multi-query strategy (see `mangobrain-remember` rule for query formulation):

```
# 1x deep — big picture
remember(query="[max 10 keywords from task]", mode="deep", project="{PROJECT}")

# 2-4x quick — one per technical area
remember(query="[specific names: components, hooks, services, files]", mode="quick", project="{PROJECT}")
```

Filter results by relevance (>0.7) and format as context for analyzers.

### Step 2: Spawn analyzer(s) with memory context

Pass retrieved memories as structured context. Analyzers also have
`remember(mode="quick")` for additional lookups during exploration.

```yaml
subagent_type: "analyzer"
model: "sonnet"
description: "Analyze [area] with memory context"
prompt: |
  Read CLAUDE.md and all .claude/rules/ files first.

  Memory context from MangoBrain (relevant to this task):
  ---
  [Paste high-relevance memories here]
  ---

  Task: [What to analyze]
  Focus: [Specific files/areas]

  You have access to remember(mode="quick") for additional lookups.
  Report findings in structured YAML (see your agent definition).
```

For FE+BE tasks, spawn 2 analyzers in parallel with domain-specific briefs.

---

## Phase 3: PLAN

Based on analyzer output + memory insights, Main creates:

1. **Atomic task list**: Each task = 1-2 files max, clear description
2. **Agent distribution**: How many executors? Parallel or sequential?
3. **Memory-informed constraints**: Relevant gotchas/patterns from memories

### Plan Format

```
PLAN for: {task title}

Memory insights applied:
- [relevant pattern/gotcha that affects the plan]

Atomic Tasks:
1. {description} → {file(s)}
2. {description} → {file(s)}

Agent Distribution:
- executor_1: Tasks 1-3 (~Xk tokens)
```

### Confirmation

**Text input**: Show plan, ask "Proceed? (ok/modify/stop)"
**Task.md input**: Show plan, auto-approve: "Plan approved (from /discuss). Proceeding..."

---

## Phase 4: EXECUTE

### Spawning Executors

**CRITICAL**: Executors have NO memory tools. They receive all context from Main
(analyzer output + memory insights).

```yaml
subagent_type: "executor"
model: "sonnet"
description: "Execute {task_description}"
prompt: |
  Read CLAUDE.md and all .claude/rules/ files first.

  Context from analyzer:
  [Paste analyzer findings for this task]

  Memory-informed constraints (from MangoBrain):
  ---
  [Relevant memories: patterns to follow, gotchas to avoid]
  ---

  Your task:
  task_id: "{task_id}"
  domain: "{frontend|backend|fullstack}"
  instruction: |
    [Detailed instruction]
  [requirements and constraints from task.md if applicable]
```

### Error Handling

```
executor fails → Analyze error → Create fix task → Respawn (retry 1)
Still fails → Ask user
```

---

## Phase 5: VERIFY

### Spawning Verifier

Verifier has `remember(mode="quick")` to check for known issues.

```yaml
subagent_type: "verifier"
model: "sonnet"
description: "Verify task execution"
prompt: |
  Read CLAUDE.md and all .claude/rules/ files first.

  You have access to remember(mode="quick") for known issues.
  Query for: build errors, known gotchas in modified files/areas.

  Files modified: [list]
  Task summary: [what was done]

  Verify: build, typecheck, lint, tests, runtime logs.
  Read CLAUDE.md for exact build/test/lint commands.
  [verification criteria from task.md if applicable]

  If failure: provide diagnostic_opinion with confidence_in_fix.
```

### Verification Retry Logic

| confidence_in_fix | Action |
|-------------------|--------|
| **high** | AUTO RETRY: spawn executor with fix_suggestion. Re-verify. If still fail → ESCALATE. |
| **medium** | RETRY 1x: spawn executor with fix_suggestion. Re-verify. If still fail → ESCALATE. |
| **low** | NO RETRY. ESCALATE to user immediately. |

**Max 2 EXECUTE→VERIFY cycles total.** After 2 failures, ALWAYS escalate.

### Escalation Format

```
VERIFICATION FAILED after {N} attempts.

Last error: {error}
What was tried: {attempts}
Verifier analysis: {root cause}

Options:
1. I can try a different approach: {alternative}
2. You can fix manually and re-run /task
3. Skip verification and proceed to CLOSE (not recommended)
```

---

## Phase 6: CLOSE — Memory Manager

### Spawning mem-manager

**CRITICAL**: mem-manager is the librarian. Full MangoBrain access. Does NOT modify code.

```yaml
subagent_type: "mem-manager"
model: "sonnet"
description: "Update MangoBrain memory for completed task"
prompt: |
  Read the memory definition reference file first
  (.claude/prompts/mangobrain/reference/memory-definition.md or equivalent).

  Task completed: "{task_title}"
  Project: "{PROJECT}"
  Project path: "{PROJECT_PATH}"
  Task source: {text input | task file: {filename}}

  Files modified: [list from executor output]

  What was done: [execution summary]

  Verification result: [pass/fail + details]

  Key decisions/findings: [decisions made during this task]

  WIP (if incomplete): [what remains, blockers]

  Your workflow:
  1. remember(quick) to check existing memories in affected areas
  2. memorize() new knowledge (patterns, gotchas, decisions, bugs)
  3. sync_codebase(changed_files) to detect stale/orphan memories
  4. Handle stale: update_memory() or leave if still accurate
  5. Register session state: completed work + WIP if applicable
```

---

## MangoBrain Failure Handling

MangoBrain tools may fail (server down, DB locked, timeout). When this happens,
**do NOT silently continue** — the user must know and decide.

### How to detect failures

MCP tool failures manifest in three ways:
1. **Timeout / connection error** — the tool call itself fails (no response)
2. **Error JSON** — the tool returns `{"error": "..."}`. Check EVERY remember/memorize/sync response for an `"error"` key.
3. **Unexpected format** — response is not valid JSON or not the expected structure

**CRITICAL**: An empty result `[]` (0 memories) is NOT an error — it means the project has no memories yet. An `{"error": "..."}` response IS an error. Never confuse the two.

### Phase-by-phase handling

| Phase | If MangoBrain fails | Action |
|-------|---------------------|--------|
| Pre-condition (ping) | Server offline | **STOP**. Inform user. Ask to proceed without memory or fix first. |
| ANALYZE (Main remember) | Stop and inform user | "MangoBrain is not responding. Proceed without memory context? (yes/no)" |
| ANALYZE (analyzer remember) | Analyzer reports failure in output | Main informs user, asks whether to continue with code-only analysis |
| VERIFY (verifier remember) | Verifier reports failure in output | Main informs user, continues verification (memory is secondary here) |
| CLOSE (mem-manager) | Stop and inform user | "Memory sync failed. Run /memorize later to sync manually." |

### What agents must do on failure

When an agent (analyzer, verifier, mem-manager) encounters a MangoBrain tool failure:
1. **Do NOT silently skip it** — include the failure prominently in the output YAML
2. Add a `mangobrain_status: "error"` field with the error message
3. Continue the rest of their work (code analysis, verification, etc.) but clearly mark that memory context was unavailable

Main MUST check agent output for `mangobrain_status: "error"` and inform the user.

**Rationale**: Working without memory context means missing gotchas, patterns, and
past decisions. The user should make an informed choice, not discover later that
memory was silently skipped.

---

## Decision Trees — Quick Reference

### How many analyzers?

```
FE + BE?
  YES → 2 parallel (1 FE, 1 BE)
  NO  → 50+ files, 3+ domains?
          YES → 2-3 parallel
          NO  → 1 analyzer
```

### How many executors?

```
Estimated work?
  < 40k tokens  → 1 executor
  40-80k tokens → 1-2 executors
  > 80k tokens  → 2-3 executors

Tasks dependent?
  YES → keep in SAME executor (retains context)
  NO  → can split to parallel executors

Touch same files?
  YES → MUST be same executor or sequential
  NO  → can be parallel
```

### Auto-retry or escalate?

```
confidence_in_fix?
  high   → AUTO RETRY (1x max)
  medium → RETRY 1x, then ESCALATE
  low    → ESCALATE immediately

Already retried twice?
  YES → ESCALATE regardless
```

---

## Output to User

### Task Summary Template

```markdown
## Task Execution Summary

**Task**: [title]
**Source**: [text input | task file: {filename}]

### What Was Done
- File 1: [changes]
- File 2: [changes]

### Verification Results
- Build: [PASS/FAIL]
- Tests: [X passed / Y failed]
- Lint: [PASS/FAIL]
- Runtime: [Clean/Errors]

### Memory Updated (MangoBrain)
- Memories created: [N]
- Files synced: [N]
- WIP registered: [yes/no]

### Notes
[Important observations, known issues, recommendations]
```

### Incomplete Task

Same template but with: **Status: Partially completed**, **What Remains** section,
**Why Incomplete** section, **WIP memory registered: yes**.

---

## User Commands During Workflow

| Command | Effect |
|---------|--------|
| `ok` / `proceed` / `go` | Approve and continue |
| `stop` / `halt` | Interrupt, register WIP in MangoBrain, report status |
| `skip analyze` | Skip ANALYZE (use with caution) |
| `modify plan` | Allow plan modification |
| `retry` | Retry last failed step |

### User Interrupts (`stop`)

1. Complete current agent if possible
2. Spawn mem-manager with WIP context (what's done, what remains, file state)
3. Report status with next-step instructions

---

## Phase Transition Checklist

| Before... | Must be true |
|-----------|-------------|
| ANALYZE | Input parsed. `remember()` multi-query done. Analyzer count decided. Memory context formatted. |
| PLAN | Analyzer outputs synthesized. Memory insights cross-referenced. Confirm strategy set (ask vs auto). |
| EXECUTE | Plan approved. Executor prompts assembled with context + memory constraints. NO memory tools for executor. |
| VERIFY | All executors done. Files list compiled. Build commands from CLAUDE.md ready. Verifier has remember access. |
| CLOSE | Verification result available. Completion status determined. Findings summarized. mem-manager has full MangoBrain access. |

---

**End of /task Skill Prompt**
