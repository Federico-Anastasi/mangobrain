---
name: memorize-work
description: "End-of-session memory sync for free work sessions (not using /create). Captures decisions, feedback, ideas, and brand refinements into MangoBrain."
user-invocable: true
---

# /memorize-work — Session Sync

You persist the knowledge from the current session into MangoBrain. Use this at the end of any work session that didn't go through /create (which has its own mem-manager step).

---

## STEP 1 — SESSION SUMMARY

Review the conversation and identify:

1. **Decisions made** — brand choices, content direction, strategy changes, tone refinements
2. **Ideas generated** — content ideas, campaign concepts, naming options, angles
3. **Feedback given** — user corrections, preferences expressed, approvals, rejections
4. **Documents created/modified** — any rule files, plans, or content produced
5. **Open items** — WIP, questions to resolve, next steps discussed

---

## STEP 2 — READ MEM-MANAGER PROMPT

Read the mem-manager agent prompt:

```
Read: .claude/agents/mem-manager.md
```

---

## STEP 3 — SPAWN MEM-MANAGER

Spawn the mem-manager as a sub-agent with the session context.

```
Spawn agent: mem-manager
Prompt: [full mem-manager.md + session summary below]

SESSION SUMMARY:
- Project: {PROJECT}
- Session type: free session (not /create)
- Work done: {description}
- Decisions: {list}
- Feedback/corrections: {list}
- Ideas (worth remembering): {list}
- Files modified: {list}
- WIP/next steps: {list}
```

---

## STEP 4 — REPORT

After mem-manager completes:

```
Sessione salvata in memoria:
- Memorie create: {count}
- Memorie aggiornate: {count}
- WIP registrato: {yes/no}

{1-line summary of what was captured}
```

---

## STEP 4b — UPDATE RULES (if needed)

If the session changed something fundamental (brand direction, tone shift, new channel, strategy pivot):

1. Read the relevant rule file in `.claude/rules/`
2. Update it with the new information
3. Tell the user: "Ho aggiornato anche {file} con le nuove decisioni."

---

## RULES

- **Don't over-memorize.** A casual brainstorm where nothing was decided produces 0-2 memories. A strategic session with 5 decisions produces 5-8. Scale to the substance.
- **Feedback is gold.** If the user corrected something ("no, il tono è troppo formale"), that's the most valuable memory type. Always capture corrections.
- **Ideas are fragile.** If a good idea came up but wasn't developed, save it as episodic with tag "idea". It might be useful later.
- **Update rules if needed.** If the session refined something that's in a rule file (e.g., tone changed), update the rule file too — not just memory.
- **WIP is critical.** If work was started but not finished, register it. The next session's `remember(mode="recent")` should surface it.
