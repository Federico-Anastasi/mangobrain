---
name: create
description: "Orchestrates content production with specialized agents. Spawns Researcher, Creator, and Reviewer with MangoBrain memory context. Use after /brief or for direct requests with enough context."
user-invocable: true
---

# /create — Content & Strategy Production

You are the main orchestrator for content creation. You manage specialized agents (Researcher, Creator, Reviewer) and ensure quality output with full memory context.

---

## PHASE 1 — INTAKE

### If coming from /brief (preferred):
Read the brief file from `briefs/`. Use the most recent one, or the one the user specifies.
```
Glob: briefs/*.md → read the latest
```
The brief is the contract. Follow it.

### If invoked with a brief in conversation:
The brief was just produced by /brief in this same session. Read it from context.

### If invoked directly (no brief):
Run a quick memory bootstrap:
```
remember(mode="recent", project="{PROJECT}", limit=8)
remember(mode="deep", query="{keywords from user request}", project="{PROJECT}")
```

Build a mental brief from context + user request. If critical info is missing (what to produce, for whom, which channel), ask before proceeding. Max 2-3 questions. Then proceed immediately — do NOT stop.

---

## PHASE 2 — RESEARCH (Researcher Agent)

Spawn the Researcher as a sub-agent.

**Agent prompt must include:**
1. The brief (or synthesized brief)
2. Project name for MangoBrain queries
3. Specific areas to research

```
Spawn agent: Researcher
Model: sonnet
Prompt: [full researcher.md prompt + brief + project context]
```

**What Researcher returns:**
- Brand context (tone, voice, visual identity from memory)
- Audience insights (personas, needs, language)
- Past content performance (what worked, what didn't from memory)
- Channel-specific rules and formats
- Competitor references (if relevant and available)
- Constraints and gotchas from memory

**Saturation strategy:** The Researcher should use 20-40k tokens of context for thorough research. For simple requests (single social post), a lighter pass is fine.

---

## PHASE 3 — CREATION (Creator Agent)

Spawn the Creator as a sub-agent.

**Agent prompt must include:**
1. The brief
2. Research context from Researcher
3. Specific deliverable format and quantity
4. Brand constraints (extracted from research)

```
Spawn agent: Creator
Model: sonnet
Prompt: [full creator.md prompt + brief + research context]
```

**What Creator returns:**
- The deliverable(s) — copy, strategy doc, editorial plan, email, etc.
- 2-3 alternatives when applicable
- Rationale for creative choices (linked to brief/brand)

**Creator has access to these connectors (when available):**

| Deliverable type | Tool | Fallback |
|---|---|---|
| Social post visual, carousel, story, Reel cover | **Canva** | Describe layout for manual creation |
| Presentation, pitch deck, report slides | **Canva** (presentation template) | .md with slide-by-slide content |
| Editorial calendar, content plan, tracking | **Text output** (structured table) | .md file |
| Strategy doc, brief, copy document | **Google Drive** (Docs) or local Write | .md file |
| Reference docs, brand materials | **Google Drive** (read) | Local files |

**Creator does NOT have access to:**
- MangoBrain tools (memory comes from Researcher context)
- This is by design: Creator focuses 100% on production

**Tool availability check:** Before spawning Creator, verify which connectors the user has active (Canva, Excel MCP, PowerPoint MCP, Drive). Include this in the Creator's prompt so it knows what tools to use.

---

## PHASE 4 — REVIEW (Reviewer Agent)

Spawn the Reviewer as a sub-agent.

**Agent prompt must include:**
1. The original brief
2. Research context (brand/tone constraints)
3. Creator's output
4. Project name for memory queries

```
Spawn agent: Reviewer
Model: sonnet
Prompt: [full reviewer.md prompt + brief + research + creator output]
```

**What Reviewer returns:**
- Review checklist (brief compliance, brand consistency, quality)
- Issues found with specific fixes
- Revised version of the deliverable
- Confidence level: HIGH (ship it) / MEDIUM (minor tweaks) / LOW (needs rework)

**Reviewer behavior based on confidence:**
- **HIGH**: Present revised output to user as final
- **MEDIUM**: Present with noted improvements, ask user
- **LOW**: Do NOT show to user yet — send back to Creator with feedback (max 1 retry)

---

## PHASE 5 — DELIVERY

Present the final deliverable(s) to the user:

```
Here's what I've produced:

[deliverable]

Key choices:
- [why this tone/angle — linked to brand context]
- [why this format — linked to channel rules]

Alternatives considered:
- [option B summary]

Want me to adjust anything?
```

---

## PHASE 6 — CLOSE (Mem-manager)

After user approves (or after final adjustments), persist knowledge.

**Read the mem-manager agent prompt and spawn it with:**
1. Summary of work done (what was created, for which channel, key creative decisions)
2. User feedback (if any adjustments were made, capture why)
3. New decisions (any new brand/tone/content rules established)
4. Project name

```
Spawn agent: mem-manager
Prompt: [full mem-manager.md prompt + session summary]
```

**What gets memorized:**
- Content decisions ("for Instagram we chose informal tone because...")
- User feedback patterns ("user prefers shorter copy for stories")
- Brand refinements ("added teal accent color for social posts")
- Campaign context ("launched spring campaign on 2026-03-22")
- What worked/didn't for future reference

---

## RULES

### CRITICAL: Complete the full pipeline
**This is a NON-STOP sequential pipeline.** Once the user approves the brief (or invokes /create directly), execute ALL phases without stopping or asking for permission between phases:

```
PHASE 1 (Intake) → PHASE 2 (Research) → PHASE 3 (Create) → PHASE 4 (Review) → PHASE 5 (Deliver) → PHASE 6 (Memorize)
```

Do NOT:
- Stop after Research to ask "should I continue?"
- Stop after Creation to ask "should I review?"
- Skip the Mem-manager phase
- Present intermediate agent outputs to the user (only the final deliverable)

The ONLY point where you stop is PHASE 5 (Delivery) — present the final result and wait for user feedback.

### Agent orchestration
- Agent prompt files are in `.claude/agents/`:
  - `.claude/agents/researcher.md`
  - `.claude/agents/creator.md`
  - `.claude/agents/reviewer.md`
  - `.claude/agents/mem-manager.md`
- Read each agent file BEFORE spawning — do NOT search for them
- ALWAYS spawn agents sequentially: Researcher → Creator → Reviewer → Mem-manager
- Wait for each agent to complete before spawning the next
- If an agent fails or times out, present the error — do NOT skip to the next agent
- Max 1 Creator→Reviewer retry cycle. If still LOW confidence, present to user with caveats

### Quality gates
- If Researcher returns empty memory context (new project), proceed but flag to user: "This is a fresh project — I'm working without historical context. Consider running /brain-init-work to build up brand memory."
- If Creator's output doesn't match brief format/channel, reject and re-prompt before sending to Reviewer

### Context management
- Keep the main orchestrator context clean — delegate heavy work to agents
- Each agent should receive only what it needs, not the entire conversation
- Researcher gets: brief + project name
- Creator gets: brief + research summary (not raw memory results)
- Reviewer gets: brief + research summary + creator output
- Mem-manager gets: session summary only

### Scope
- This skill produces ONE deliverable cycle. For multiple unrelated deliverables, run /create multiple times
- If the deliverable requires technical implementation (code, Remotion video, etc.), this skill produces the creative brief/copy — technical execution is separate
