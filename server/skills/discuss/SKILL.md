---
name: discuss
description: Memory-enhanced interactive task planning and brainstorming. Explores codebase with MangoBrain context, proposes approaches, generates task.md for /task.
argument-hint: <task description to plan>
---

# Skill: /discuss - Memory-Enhanced Task Brainstorming & Planning

Interactive exploration and planning for complex tasks BEFORE code execution.
MangoBrain persistent memory provides context-aware planning — past decisions,
known gotchas, established patterns inform every phase.

---

## Core Rules

**Your role is to PLAN, not execute.** Explore with patience, propose alternatives,
let the user choose the best approach before any code is touched.

### Allowed Tools

| You CAN use                                    | DO NOT use (reserved for /task)      |
|------------------------------------------------|--------------------------------------|
| `Read`, `Grep`, `Glob` — explore code          | `Edit`, `Write` — modify files       |
| MCP `remember` — query persistent memory        | `Bash` — run commands                |
| `Task` → **analyzer** (explore codebase)        | `Task` → **executor** (modify code)  |
|                                                | `Task` → **verifier** (build/test)   |

### Workflow

`INTAKE → EXPLORE → BRAINSTORM → DOCUMENT`

**Output**: File `.claude/tasks/{YYYY-MM-DD-HHMM}-{slug}.md` ready for `/task`.

**Agent rule**: ALWAYS specify `model: "sonnet"` when spawning analyzer.

If during exploration you find something to fix, document it in task.md — `/task`
will implement it.

---

## When to Use

Use `/discuss` for:
- Complex tasks (3+ files, architectural decisions)
- Tasks with multiple valid approaches
- When requirements are unclear
- When the user wants to explore options before committing
- Multi-step features that need breakdown
- Refactoring planning

**DO NOT use** for:
- Simple tasks (<10 lines, 1 file) → Use `/task` directly
- Obvious bug fixes with clear solutions
- Typo corrections
- Tasks with clear, unambiguous requirements

---

## Special Case: Post-Task Review

**FIRST: Check for `.claude/post-task-review.flag`**

If this file exists, this is the automation loop returning from `/task` execution.

**Workflow**:

1. **Read `.claude/post-task-review.flag`** to get task name, then **delete the file**
2. **Query memory for recent context**:
   ```
   remember(mode="recent", project="{PROJECT}")
   ```
3. **Summarize** combining memory + git status:
   ```
   I see we just completed: [task name from marker file]

   What was done:
   - [list changes from recent memories and/or git status]

   Verification status:
   - [build/tests status if available in memory]

   Open items:
   - [WIP or follow-up notes from memory, or "None"]
   ```
4. **Ask user for next steps**:
   ```
   The task is complete. What would you like to do next?
   - Continue with next task?
   - Address any issues you noticed?
   - Review something specific?
   ```
5. **Proceed with normal /discuss workflow** based on user response

---

## Workflow Phases

### Phase 1: INTAKE

**Duration**: Interactive, as long as needed
**Goal**: Understand user intent and load memory context before exploring code

#### Step 0: MangoBrain Availability Check (MANDATORY)

**BEFORE any memory retrieval**, call `ping()` to verify MangoBrain is online.

```
ping()
```

**Interpret the response:**
- `{"status": "ok", "model_loaded": true}` → MangoBrain is online. Proceed to Step 1A.
- `{"status": "degraded", ...}` → MangoBrain is partially available (DB issue). Inform user and ask whether to proceed without memory.
- **Timeout / connection error / no response** → MangoBrain is **offline**. **STOP** and inform the user:

```
⚠️ MangoBrain is not responding. Memory context will not be available for this session.

Options:
1. Proceed without memory (code exploration only, no past context)
2. Abort and fix MangoBrain first (run: mangobrain serve)

Which do you prefer?
```

**Do NOT silently continue without memory.** The user must explicitly choose to proceed.

If user chooses option 1, set a mental flag: `MANGOBRAIN_OFFLINE = true`. Skip all `remember()` calls for the rest of this /discuss session and note in the task.md output that memory was unavailable.

#### Step 1A: Memory Bootstrap

Start IMMEDIATELY with memory retrieval. Do not wait for clarifying questions.

Run the multi-query strategy (see `mangobrain-remember` rule for query formulation):

```
# 1. Recent context (always first)
remember(mode="recent", project="{PROJECT}")

# 2. Deep query on the topic (1x)
remember(query="[max 10 keywords from user request]", mode="deep", project="{PROJECT}")

# 3. Quick queries per technical area (2-4x)
remember(query="[area 1: specific component/file/hook names]", mode="quick", project="{PROJECT}")
remember(query="[area 2: specific names]", mode="quick", project="{PROJECT}")
```

#### Step 1B: Clarifying Questions

While memories load (or immediately after), engage the user:

1. **Greet and explain**:
   ```
   I'll help you plan [task description]. This is an exploration phase —
   we'll discuss approaches and create a detailed task document.
   No code will be modified yet.

   [If relevant memories found]:
   From memory, I see that [relevant context]. This will inform our planning.
   ```

2. **Ask clarifying questions** (adapt based on task + memory context):
   - **Goal**: What is the end result?
   - **Scope**: What should NOT change? Constraints?
   - **Context**: Which user flows are affected?
   - **Non-functional**: Performance? Mobile optimization?
   - **Memory-informed**: "Last time we worked on [area], we hit [issue].
     Should we account for that here?"

3. **Identify domain**: Frontend / Backend / Fullstack / Database changes?

4. **Assess complexity**: Simple (1-2 files) / Medium (3-5 files) / Complex (multi-domain)

#### Step 1C: Surface Memory Context

Before moving to EXPLORE, briefly tell the user what memory found:

```
Memory context for this task:
- [Pattern/convention]: [brief description]
- [Past decision]: [what was decided and why]
- [Known gotcha]: [warning from past experience]
```

If no relevant memories: "No directly relevant memories found. We'll work from codebase exploration only."

This lets the user correct stale memories and builds shared context for BRAINSTORM.

#### How Many Analyzers to Spawn

**Practical question: How much work is there?**

Analyzers have 200k context. Most tasks need 1.

| Situation | Analyzers |
|-----------|-----------|
| Specific flow (1 bug, 1 feature, even 10-20 files) | 1 |
| Frontend + Backend together | 2 parallel (1 FE, 1 BE) |
| Large analysis (50+ files, multi-domain) | 2-3 parallel |

**Never**: 5 analyzers for 5 files (micro-tasking is wasteful).

---

### Phase 2: EXPLORE (1-3 Analyzer Agents)

**Duration**: 30-60 seconds per agent (parallel)
**Goal**: Map existing code, patterns, dependencies — enriched by memory context

#### Spawning Analyzers

**ALWAYS specify `model: "sonnet"`**. Pass memory context and grant `remember` tool access.

```yaml
subagent_type: "analyzer"
model: "sonnet"
description: "Explore [area] with memory context"
prompt: |
  Read CLAUDE.md and all .claude/rules/ files first.

  Memory context from MangoBrain (relevant to this task):
  ---
  [Paste high-relevance memories from INTAKE here]
  ---

  Task: [What to explore]
  Focus: [Specific files/areas]

  You have access to remember(mode="quick") for additional lookups.
  Report findings in structured YAML (see your agent definition).
```

For multiple analyzers (FE+BE), spawn in parallel with domain-specific briefs.

#### After Analyzer Completion

1. **Read all analyzer outputs**
2. **Cross-reference with memory**: Note confirmations and contradictions
3. **Synthesize and present** to user:
   ```
   Based on exploration (code + memory):

   **Current Setup**: [summary]

   **Confirmed from Memory**: [patterns validated by code]

   **New Findings** (not in memory): [discoveries]

   **Key Finding**: [main insight for the task]
   ```

---

### Phase 3: BRAINSTORM

**Duration**: Interactive, iterative
**Goal**: Agree on implementation approach with user, informed by memory

#### Memory-Enhanced Brainstorming

During brainstorming, memory provides context that pure code exploration cannot:

- **Past bugs**: "Attention, last time we modified [area], we hit [issue]."
- **Architectural decisions**: "This pattern was chosen because [reason]."
- **Established patterns**: "Similar features use [pattern]. Aligning would be consistent."
- **Known constraints**: "[Component] has a performance sensitivity — approach B avoids it."

If a new area comes up during discussion, query before responding:
```
remember(query="[new area keywords]", mode="quick", project="{PROJECT}")
```

#### Your Responsibilities

1. **Propose 2-3 approaches** based on analyzer findings + memory
2. **For each**, discuss:
   - Pros / Cons
   - Complexity (files count, risk level)
   - Alignment with existing patterns (memory-informed)
   - History: has something similar been tried before?
3. **Use `AskUserQuestion`** for critical decisions:
   ```typescript
   AskUserQuestion({
     questions: [{
       question: "Which approach do you prefer?",
       header: "Approach Selection",
       multiSelect: false,
       options: [
         {
           label: "Approach A: [Name] (Recommended)",
           description: "[files count], [complexity], [key advantage]"
         },
         {
           label: "Approach B: [Name]",
           description: "[files count], [complexity], [key advantage]"
         },
         {
           label: "Explore other options",
           description: "I want to see more alternatives"
         }
       ]
     }]
   })
   ```
4. **Iterate until user is satisfied**

If user says "explore other options" or wants modifications:
1. Ask what to change
2. If it touches a new area, run `remember(mode="quick")` first
3. Refine and present updated plan
4. Repeat until confirmed

---

### Phase 4: DOCUMENT

**Duration**: Quick — you already have all the context
**Goal**: Generate structured `task.md` file for `/task` execution

#### Task.md Philosophy

**CRITICAL**: The task.md is a **DECISIONAL RECORD** (output of brainstorming),
NOT a step-by-step implementation plan.

- Captures **WHAT** was decided and **WHY**
- `/task` will do its own ANALYZE and PLAN autonomously
- Hints are high-level areas, NOT exact files/lines
- NO code snippets
- Include "Memory Context" section with relevant memories found

#### Generate Task.md Directly

After user confirms the chosen approach, write the task.md yourself using the `Write` tool.
You have all the context from INTAKE + EXPLORE + BRAINSTORM — no need to delegate.

**File path**: `.claude/tasks/{YYYY-MM-DD-HHMM}-{slug}.md`

**Task.md Template**:

```markdown
# {Task Title}

## User Request
{Original user input, cleaned up}

## Chosen Approach
**{Approach Name}**

{Why this approach was chosen. Reference rejected alternatives briefly.}

## Requirements
- [ ] {Functional requirement 1}
- [ ] {Functional requirement 2}
- ...

## Constraints
- {Design/technical constraint — from discussion or memory}
- ...

## Memory Context
{Relevant memories discovered during INTAKE. Format:}
- **[type]**: {brief content} {known gotcha or decision}
- **[type]**: {brief content}
{If no memories: "No relevant memories found. First implementation in this area."}

## Known Risks
| Risk | Severity | Source |
|------|----------|--------|
| {risk description} | high/medium/low | code/memory |

## Verification Criteria
- {Build commands to run}
- {Test scenarios to verify}
- {Edge cases to check}

## Hints for /task ANALYZE
- {High-level area 1 to explore}
- {High-level area 2}
{Optional. Do NOT include exact files/lines — /task's analyzer will find them.}
```

**Rules for task.md**:
- No code snippets — `/task` will read the code itself
- No step-by-step instructions — `/task` creates its own PLAN
- Filename includes hour+minute to avoid conflicts
- Focus entirely on WHAT and WHY

#### After Writing Task.md

1. **Verify** the file was written successfully
2. **Present summary to user**:
   ```
   Task document created: `.claude/tasks/{filename}.md`

   Summary:
   - Title: [title]
   - Areas involved: [count]
   - Complexity: [level]
   - Key risks: [top 2-3]
   - Memory context: [N] relevant memories included

   To execute: /task .claude/tasks/{filename}.md
   To review first: open the file above
   To refine: edit the file manually or re-run /discuss
   ```

---

## Multi-Task Scenarios

If discussion reveals **multiple independent tasks**:

1. **Identify natural breakpoints**:
   ```
   This feature can be broken into 3 independent tasks:
   1. Database schema changes
   2. Backend API endpoints
   3. Frontend UI components

   Should I create 3 separate task.md files?
   ```

2. **Generate separate task.md files** (one per task):
   - Each is self-contained with its own memory context
   - Name: `{timestamp}-{slug}-part1.md`, `part2.md`, `part3.md`

3. **Document execution order** if dependencies exist:
   ```
   1. .claude/tasks/...-part1-database.md  (execute first)
   2. .claude/tasks/...-part2-backend.md   (depends on 1)
   3. .claude/tasks/...-part3-frontend.md  (depends on 2)
   ```

---

## Edge Cases

### No MangoBrain Memories Available

**Distinguish between these cases:**

1. **`remember` returns empty results (0 memories)** → Legitimate. The project has no memories yet.
   ```
   No memories found for this project. Proceeding with codebase exploration only.
   ```

2. **`remember` returns `{"error": "..."}` or times out** → MangoBrain tool failure mid-session.
   **STOP and inform the user:**
   ```
   ⚠️ MangoBrain remember() failed: [error message].
   Memory context is unavailable. Proceed without memory? (yes/no)
   ```
   Do NOT silently continue. The user must decide.

3. **`ping()` already confirmed offline (MANGOBRAIN_OFFLINE = true)** → Skip remember calls silently (user already authorized proceeding without memory in Step 0).

### Stale Memories Detected

If analyzer finds code contradicts what memory says:
```
Note: Memory says [X] but code shows [Y]. This memory may be stale.
I'll flag it in the task.md so /task is aware.
```
Include stale memories with `[STALE?]` marker in task.md. Do NOT call
`update_memory` from /discuss — that is the mem-manager's job during /task CLOSE.

### Conflicting Memories

If memory returns contradictory information:
```
Memory shows conflicting info:
- Memory A (date): [X]
- Memory B (date): [Y]
The more recent one is likely current. Let me verify against code...
```
Present both to user and let them clarify.

### Analyzer Finds Nothing

```
Analyzer didn't find clear patterns for [feature X].
Let me check memory for more context...
[Run remember(mode="quick")]

Options:
- Spawn another analyzer with different search terms
- Proceed with best-guess and document uncertainty
- You provide more context about existing implementation
```

### User Wants to Skip EXPLORE

```
User: "I already know the code, just help me plan"

Understood. Skipping code exploration but still checking memory.
[Run memory queries]
Based on memory: [relevant patterns/decisions found]
Let me propose approaches...
```
Even when skipping EXPLORE, always run memory queries.

### User Changes Mind After DOCUMENT

Regenerate task.md with updated context. Rewrite the file.

---

## Project Detection

The `{PROJECT}` placeholder in memory queries must match MangoBrain's project name.
Determine it from: CLAUDE.md project name > `.claude/rules/` > directory name.
Verify with `remember(mode="recent", project="{PROJECT}")` — if it returns results, the name is correct.

---

## Verification Before Exit

Before completing `/discuss`, ensure:

1. Task.md created and written successfully
2. File path shown to user
3. Next step clear: `/task {file.md}`
4. Memory context included in task.md
5. User satisfied: "Any refinements needed?"

---

## Quick Reference: Phase Checklist

### INTAKE
- [ ] `remember(mode="recent")` — WIP context
- [ ] `remember(mode="deep")` — broad topic context
- [ ] 2-4x `remember(mode="quick")` — per technical area
- [ ] Clarifying questions asked
- [ ] Domain identified (FE/BE/fullstack)
- [ ] Complexity assessed
- [ ] Memory context surfaced to user

### EXPLORE
- [ ] Analyzer count decided (1-3)
- [ ] Analyzers spawned with `model: "sonnet"` + memory context + remember access
- [ ] Findings synthesized (code + memory cross-reference)
- [ ] Findings presented to user

### BRAINSTORM
- [ ] 2-3 approaches proposed (memory-informed)
- [ ] Pros/cons for each (including memory insights)
- [ ] User chose approach
- [ ] Quick memory queries for any new areas discussed

### DOCUMENT
- [ ] Task.md written directly with `Write` tool
- [ ] Task.md is decisional record (WHAT/WHY, not HOW)
- [ ] Task.md includes Memory Context section
- [ ] No code snippets in task.md
- [ ] Filename: `YYYY-MM-DD-HHMM-slug.md`
- [ ] File path shown to user
- [ ] Next steps communicated

---

**End of /discuss Skill Prompt**
