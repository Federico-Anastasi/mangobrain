# /brain-init — Memory Initialization for a Project

Orchestrates the full memory initialization process for a new project in MangoBrain.

## When to use
When setting up MangoBrain for a project that has no memories yet, or when resuming an incomplete initialization.

## Input
The user provides:
- **project**: project name (e.g., "myproject")
- **project_path**: root path (e.g., "~/projects/myproject")

If not provided, ask.

## Workflow

### Step 1 — Check current progress

Call `setup_status(project="{PROJECT}", action="get")`.

**If the project is not initialized:**
- Show: "Il progetto {PROJECT} non ha ancora un setup. Lo inizializzo?"
- On confirmation, call `setup_status(project="{PROJECT}", action="init")`
- This creates all 14 steps across 6 phases

**If already initialized:**
- Show the current progress table: which steps are completed, which is next
- Resume from the first non-completed step

### Step 2 — Show the roadmap

Present the full initialization plan to the user. Group by phase:

```
=== Init Roadmap: {PROJECT} ===

INSTALL (preparazione)
  1. [x] Skills & Rules — Copy skills, agents, rules into .claude/
  2. [ ] MCP Config — Verify MCP server is accessible

INIT (estrazione memorie) — OGNI STEP = SESSIONE SEPARATA
  3. [ ] Doc Base — Rules & documentation extraction
  4. [ ] Code Base — Parallel codebase scan (subagents)
  5. [ ] Event Base — Import from PROJECT_MEMORY.jsonl (optional)
  6. [ ] Chat Base — Extract from chat JSONL sessions (multiple runs)
  7. [ ] Elaborate Base — First elaboration pass(es)

SMOKE TEST
  8. [ ] Query Verification — 10-20 test queries

HEALTH CHECK
  9. [ ] Diagnose — Baseline health score
  10. [ ] Content Gap — Coverage analysis + fill
  11. [ ] Elaborate Fix — Structural repair

VALIDATION
  12. [ ] Final Queries — Improved retrieval check
  13. [ ] Final Health — Score confirmation

READY
  14. [ ] Memory Ready — auto-completes when all above are done
```

Mark completed steps with [x]. Highlight the NEXT step.

### Step 3 — Execute the next step

Based on which step is next, follow the appropriate logic:

---

#### Steps WITH prompt_file (3, 4, 5, 6, 7)

These steps have a `prompt_file` field in the setup_status response. The prompt file contains detailed instructions for that phase.

1. Mark step as in_progress: `setup_status(project, action="update", phase="{phase}", step="{step}", status="in_progress")`
2. Read the prompt file using the Read tool (path is relative to the mango-brain package directory)
3. Follow the instructions in the prompt file exactly
4. When done, mark as completed: `setup_status(project, action="update", phase="{phase}", step="{step}", status="completed", result="{JSON with metrics}")`

**IMPORTANT**: Steps 3-7 are heavy operations that should each run in their own session. Tell the user:
- "Questo step richiede una sessione dedicata. Lancio ora oppure ti do il comando per farlo dopo?"
- If the user wants to do it now, proceed in the current session
- If the user wants to defer, provide the command:
  ```
  claude "/brain-init{PROJECT} {PROJECT_PATH}"
  ```
  The skill will resume from where it left off.

**Step 6 (Chat Base)** is special: it may require MULTIPLE sessions (3-5 chat sessions per run). After each run, check if sessions remain. If so, tell the user to run again.

**Step 7 (Elaborate Base)** should be run 2-3 times until coverage is adequate.

---

#### Steps WITHOUT prompt_file — built-in logic

**Step 1 — Install Skills & Rules:**
1. Check if the target project has `.claude/` directory
2. Copy MangoBrain rule files to `{project_path}/.claude/rules/`:
   - `mangobrain-remember.md` — query strategy rules
   - `mangobrain-workflow.md` — workflow integration rules
3. Verify CLAUDE.md mentions MangoBrain or add a section
4. Mark completed

**Step 2 — Verify MCP Config:**
1. Call `stats()` (any simple MCP tool) to verify the server responds
2. If it fails, guide the user through MCP configuration in `~/.claude/settings.json`
3. Call `stats(project="{PROJECT}")` to verify project-level access
4. Mark completed

**Step 8 — Smoke Test (Query Verification):**
Run the `/smoke-test` skill. It generates 10-20 queries, tests retrieval quality, and reports results. If the overall score is acceptable (>70%), mark completed.

**Step 9 — Health Check Diagnose:**
1. Call `diagnose(project="{PROJECT}", project_path="{PROJECT_PATH}")`
2. Show the health score and prescriptions
3. Mark completed with the health score in result

**Step 10 — Content Gap:**
1. Use the content_gaps from the diagnose result (step 9)
2. Follow the content gap workflow from `/health-check`
3. Mark completed when gaps are filled (or user decides to skip)

**Step 11 — Elaborate Fix:**
1. Look at structural prescriptions from diagnose
2. Run 2-3 targeted elaboration rounds with focus from prescriptions
3. Mark completed when structural metrics improve

**Step 12 — Final Queries:**
Run `/smoke-test` again. Compare with step 8 results. Show improvement.

**Step 13 — Final Health:**
1. Re-run `diagnose(project="{PROJECT}", project_path="{PROJECT_PATH}")`
2. Compare with step 9 baseline
3. Show before/after table
4. Mark completed

**Step 14 — Memory Ready:**
Auto-completes when all other steps are completed. Show a celebration message:
```
=== {PROJECT} Memory Initialized ===
Health Score: XX%
Memories: N
Edges: N
Da ora puoi usare /task, /discuss, /memorize nel progetto.
```

### Step 4 — Session boundary advice

After completing a step (or when context is getting full), advise the user:

- "Step {N} completato. Il prossimo step ({title}) richiede una sessione nuova per avere contesto pulito."
- "Lancia: claude '/init {PROJECT} {PROJECT_PATH}' per continuare."
- The skill will auto-detect progress and resume from the right place.

## Notes

- The full init process takes 8-15 sessions depending on project size
- Steps 3-7 are the heaviest (they read code and create memories)
- Steps 8-13 are lighter (diagnosis and targeted fixes)
- The user can skip any step with setup_status(action="update", status="skipped")
- If a step fails, mark it as failed and let the user decide whether to retry or skip
- Always communicate in Italian with the user
