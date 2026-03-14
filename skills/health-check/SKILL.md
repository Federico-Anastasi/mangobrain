# /health-check — Memory Health Diagnosis and Optimization

Diagnoses the health of a project's memory system and guides targeted improvements.

## When to use
- Monthly maintenance (recommended cadence)
- When retrieval quality feels poor
- After a large batch of new memories (post-init, post-extraction)
- When the user says "/health-check", "controlla la memoria", "ottimizza mangobrain", or similar

## Input
- **project**: project name (ask if not provided)
- **project_path**: project root path (ask if not provided)

## Workflow

### PHASE 1 — Diagnose structure (automatic)

Call: `diagnose(project="{PROJECT}", project_path="{PROJECT_PATH}")`

Show the user a readable summary:

```
Health Score: XX% (maturity: {mature|growing|young})

Prescrizioni struttura:
1. {severity} [{metric}] current -> target | Azione: {action} (focus: {focus})
   Diagnosi: {diagnosis}
   Perche conta: {why_it_matters}

2. {severity} [{metric}] ...
```

Severity icons:
- WARN = sotto target, intervento necessario
- OPTIMIZE = in target ma migliorabile
- INFO = informativo, tutto ok
- INVESTIGATE = richiede analisi manuale

Then ask: **"Vuoi anche un check del contenuto (content gap analysis)?"**
- If no: skip to Phase 3
- If yes: proceed to Phase 2

### PHASE 2 — Content gap analysis (on request)

The `diagnose()` response includes `content_gaps` — modules with few memories relative to their codebase presence.

**Step 2a**: Show the raw content_gaps from diagnose.

**Step 2b**: For each gap with `gap_score > 0.5`, verify it's real:
```
remember(query="{module keywords}", mode="quick", project="{PROJECT}")
```
- If results are weak (score < 0.6 or < 3 results): gap CONFIRMED
- If results are strong: false positive, skip

**Step 2c**: Present confirmed gaps:
```
Content gap confermati:
- modules/reviews (gap_score 0.7 — 1 memoria, 8 file nel codebase)
- components/search (gap_score 0.6 — 2 memorie generiche)
- routes/admin (gap_score 0.9 — 0 memorie)

Vuoi procedere con tutti i topic oppure qualcuno in particolare?
```

### PHASE 3 — Execute (user's choice)

The user sees the full list: structural prescriptions + content gaps (if Phase 2 was done).

**IMPORTANT**: Recommend filling content gaps FIRST, then structural prescriptions. Rationale: new memories created for gaps will be integrated into the graph during the subsequent structural elaboration. Doing it in reverse leaves new memories disconnected.

---

#### If the user chooses content gap fill:

1. Evaluate gap size (file count per topic, estimated coverage)
2. Decide agent distribution:
   - Few small topics (<20 files total): 1 sub-agent for all
   - Medium topics (20-40 files): 2 sub-agents in parallel
   - Large topics: 3 sub-agents max
   The main agent decides allocation — no 1:1 topic-to-agent rule.

3. Spawn investigator sub-agents:
   ```
   Analyze the following modules in the {PROJECT} codebase at {PROJECT_PATH}:
   - {module_1}: search in {directory_1}
   - {module_2}: search in {directory_2}

   For each functional area, propose memories following standard format:
   - content: 2-5 lines, English, self-contained, atomic
   - type: episodic/semantic/procedural
   - tags: 3-6 keywords
   - file_path: main file of the module
   - relations: suggest connections with existing memories (by topic, not ID)

   DO NOT write anything to the database — return ONLY structured proposals.
   Focus on: module architecture, API endpoints, main components,
   gotcha/patterns, user flows, design decisions.
   ```

4. Collect all proposals from sub-agents
5. For each proposal, run `remember(mode="quick")` with keywords to check for duplicates
6. Consolidate: merge similar proposals, normalize format, add relations
7. Present to user: "Propongo N nuove memorie per colmare i gap. Ecco le prime 5: [...]. Procedo con tutte?"
8. On confirmation, write with `memorize()` for each memory
9. Report: "Create N memorie, M relazioni"

---

#### If the user chooses a structural prescription:

**action = "elaborate":**
1. Call `prepare_elaboration(project="{PROJECT}", focus="{rx.focus}", focus_instructions="{rx.diagnosis} — {rx.why_it_matters}", seed_count=50)`
2. Read the working set file
3. Follow the `/elaborate` skill workflow with the focus from the prescription
4. Call `apply_elaboration(elaboration_id, updates)`
5. Show report

**action = "improve_graph_and_queries":**
1. Explain that this improves with: denser graph (elaborate), typed edges (elaborate focus: typed_edges), and multi-query strategy (see mangobrain-remember.md)
2. Suggest running "elaborate" prescriptions first
3. If user wants to investigate: `list_memories(sort="accessed", limit=15, project="{PROJECT}")` to see most-accessed memories

**action = "investigate":**
1. Call `list_memories` with appropriate filters
2. Show results and discuss with user what to do (deprecate, update, split)

### PHASE 4 — Verify

After each action (content gap fill OR structural prescription):

1. Re-run `diagnose(project="{PROJECT}", project_path="{PROJECT_PATH}")`
2. Show before/after comparison table:
   ```
   Metrica              Prima    Dopo     Target
   health_score         72%      81%      80%+
   avg_edges            2.1      3.4      3.0+
   typed_edge_ratio     0.15     0.35     0.30+
   ...
   ```
3. If prescriptions or gaps remain: "Vuoi continuare con un'altra azione?"

## Notes

- A single health-check session can execute 1-3 actions
- Recommended order: content gaps -> elaborate -> investigate
- Elaboration has the most impact on structural metrics
- Access balance (Gini) does NOT improve in one session — it improves with natural use over time
- Each elaboration round processes ~50 seeds + ~150 neighbors
- Sub-agents for content gaps DO NOT write to DB — only the main agent writes after user confirmation
