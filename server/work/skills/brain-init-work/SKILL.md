---
name: brain-init-work
description: "Guided project initialization for MangoBrain Work. Adapts to available sources (existing memory, documents, live site, or from scratch). Generates CLAUDE.md, rules files, and populates MangoBrain memory. Tracks progress with setup_status."
user-invocable: true
---

# /brain-init-work — Project Initialization

Orchestrates the full initialization of a MangoBrain Work project.

**Project name**: use the current folder name as the MangoBrain project name. This is a hard convention — the project name MUST match the folder name. Never use the brand/product name as the project name.

## When to use
When setting up MangoBrain Work for a project that has no memories yet, or when resuming an incomplete initialization.

## Input
The user provides:
- **project**: project name (= folder name)
- **project_path**: root path

If not provided, use the current folder name and path.

## Workflow

### Step 1 — Check current progress

Call `setup_status(project="{PROJECT}", action="get")`.

**If not initialized:**
Use the AskUserQuestion tool:

```
AskUserQuestion(questions=[{
  question: "Il progetto {PROJECT} non ha ancora un setup MangoBrain Work. Vuoi che lo inizializzi?",
  header: "Setup",
  options: [
    {label: "Sì, inizializza", description: "Crea il setup e mostra la roadmap"},
    {label: "No, non ora", description: "Annulla l'inizializzazione"}
  ],
  multiSelect: false
}])
```

Only after the user confirms, call `setup_status(project="{PROJECT}", action="init")`.

**If already initialized:**
- Show current progress, resume from first non-completed step

### Step 2 — Show the roadmap

After user confirms initialization, show the roadmap and then **STOP again** before Step 2. Wait for the user to say to proceed.

```
=== Init Roadmap: {PROJECT} ===

SETUP
  1. [ ] Install & Verify — MCP check, project init

INIT
  2. [ ] Gather Sources — Collect from memory/docs/site/conversation
  3. [ ] Generate Files — CLAUDE.md + .claude/rules/
  4. [ ] Populate Memory — Create memories from gathered context

VERIFY
  5. [ ] Smoke Test — Query verification
  6. [ ] Health Check — Diagnose + fix gaps

READY
  7. [ ] Project Ready — auto-completes when all above are done
```

Mark completed steps with [x]. Highlight the NEXT step.

### Step 3 — Execute the next step

---

#### Step 1 — Install & Verify

1. Call `stats(project="{PROJECT}")` to verify MCP server responds — ONLY check this project, do NOT explore other projects in the database
2. Call `init_project(project="{PROJECT}", path="{PATH}")`
3. Verify rules are in place (`.claude/rules/mangobrain-remember-work.md`, `.claude/rules/mangobrain-workflow-work.md`)
4. Mark completed

**IMPORTANT:** Do NOT look at other projects' data. Do NOT assume connections to other projects. Cross-project memory is configured in Step 2 based on what the user tells you.

---

#### Step 2 — Gather Sources

Use the AskUserQuestion tool for ALL questions in this step. Do NOT write questions as plain text.

**First question — what the project does:**

```
AskUserQuestion(questions=[{
  question: "Di cosa si occupa il progetto? Descrivilo in una frase.",
  header: "Progetto",
  options: [
    {label: "App / piattaforma web", description: "SaaS, marketplace, tool online"},
    {label: "Prodotto / servizio", description: "Prodotto fisico o servizio offline"},
    {label: "Brand / personal brand", description: "Identità personale o aziendale"},
    {label: "Altro", description: "Qualcos'altro"}
  ],
  multiSelect: false
}])
```

**Second question — available sources:**

```
AskUserQuestion(questions=[{
  question: "Cosa abbiamo a disposizione per configurare il progetto?",
  header: "Risorse",
  options: [
    {label: "Memoria MangoBrain Code", description: "Un progetto Code con memoria esistente — specifica il nome nel campo 'Other'"},
    {label: "Documenti", description: "Brand guidelines, piani, presentazioni, pitch deck"},
    {label: "Sito web", description: "Un sito online da analizzare — specifica l'URL nel campo 'Other'"},
    {label: "Partiamo da zero", description: "Niente di tutto questo, facciamo tutto con le domande"}
  ],
  multiSelect: true
}])
```

Ask follow-up questions with AskUserQuestion based on what the user selected (e.g., project name for Code memory, URL for website, document location).

**Do NOT assume connections to other MangoBrain projects.** Do NOT auto-detect projects in the database. Only use what the user explicitly tells you.

After the user answers all questions, configure sources:

**From MangoBrain Code memory (if available):**
```
remember(mode="deep", query="product feature user flow value proposition UX", project="{CODE_PROJECT}")
remember(mode="quick", query="brand visual identity colors palette fonts", project="{CODE_PROJECT}")
remember(mode="quick", query="user types audience target customer", project="{CODE_PROJECT}")
```
CRITICAL: translate everything to non-technical language. Extract WHAT and WHY, never HOW (technical).

**From documents (if available):**
```
Glob: **/*.{md,docx,pdf,xlsx,pptx,txt}
```
Search ONLY inside THIS project folder. Read and extract brand, audience, tone, strategy, content.

**From website (if available):**
Browse/WebFetch: extract visual identity, copy, tone, features, CTA.
Save the URL in CLAUDE.md (under a "## Riferimenti" section) AND as a memory:
```
memorize(content="Project website: {URL}. Use for visual identity reference, copy analysis, and feature discovery.",
  memory_type="semantic", tags=["reference", "website", "product"], project="{PROJECT}")
```

**From scratch:** rely on conversation only.

**IMPORTANT — Boundaries:**
- Do NOT read source code files. Ever. Not even if they are accessible on this machine. The codebase is not your domain.
- Do NOT explore folders outside this project. The Code project lives elsewhere and may not be on this machine.
- Your sources are: MangoBrain memory (via remember), documents in THIS folder, website (via web), and the user's answers. Nothing else.

**Present findings to the user**, then use AskUserQuestion for gap questions.

**Be thorough.** Ask as many questions as needed to build a complete picture — don't rush. Use multiple rounds of AskUserQuestion. Cover ALL areas: product, brand, audience, tone, channels, strategy. Go beyond the obvious — ask about competitor positioning, content that inspired them, what tone they'd never use, their ideal customer's daily life, budget constraints, team resources.

The quality of the init depends on the quality of the questions. Superficial questions → superficial rules → superficial content later. Deep questions → deep understanding → great content from day one.

Use AskUserQuestion with relevant options for each area. Include smart options that show you understand the domain — not just generic choices.

Mark completed with result summary.

---

#### Step 3 — Generate Files

Read templates from `.claude/templates/` and fill them in.

**3a. Generate CLAUDE.md** in project root (from `templates/CLAUDE.md`)

**3b. Generate rule files** in `.claude/rules/` (from `templates/rules/*.md`):
- product.md, brand.md, tone.md, audience.md, channels.md, strategy.md
- Only generate rules you have content for. Skip empty areas.

Show the user what was generated. Wait for approval before proceeding.

Mark completed.

---

#### Step 4 — Populate Memory

For each rule file generated, extract atomic memories:
- **2-5 lines**, English, self-contained
- **One fact per memory** (granularity test)
- **Tags**: 3-6, lowercase, area tag required
- **file_path**: mandatory for rule-linked memories (e.g., `.claude/rules/brand.md`)
- **content_signature**: encouraged (e.g., `"brand: palette = teal #14b8a6, cyan #06b6d4"`)
- **Relations**: connect memories across areas

Use `memorize()` in batches of 10-15.

**Volume calibration:**

| Source richness | Expected memories |
|---|---|
| From scratch | 20-40 |
| Documents OR site | 40-70 |
| Code memory + site + conversation | 60-100 |
| Full documentation set | 80-120 |

Run `stats(project="{PROJECT}")` and report:

```
Memorie create: {count}
Connessioni: {edges}

Copertura:
  Prodotto:  {n} {✓ | ⚠}
  Brand:     {n} {✓ | ⚠}
  Tono:      {n} {✓ | ⚠}
  Audience:  {n} {✓ | ⚠}
  Canali:    {n} {✓ | ⚠}
  Strategia: {n} {✓ | ⚠}
```

Mark completed.

---

#### Step 5 — Smoke Test

Run `/smoke-test-work`. It generates test queries, evaluates retrieval, reports score.
- Score >70%: mark completed
- Score <70%: flag weak areas, suggest targeted memory additions

This step should run in a **new session** for clean context.

---

#### Step 6 — Health Check

Run `/health-check-work`. Diagnose + fix:
1. `diagnose(project="{PROJECT}")`
2. Show health score + prescriptions
3. Execute fixes (elaborate, fill gaps)
4. Re-diagnose, show before/after

Mark completed with final health score.

This step should run in a **new session** for clean context.

---

#### Step 7 — Project Ready

Auto-completes when all steps are done. Show:

```
=== {PROJECT} Inizializzato ===

Health Score: {n}%
Memorie: {n}
Connessioni: {n}
Rule files: {list}

Il progetto è pronto. Usa:
- /brief per iniziare un nuovo lavoro
- /create per produrre contenuti
- /memorize-work a fine sessione libera
- /elaborate-work settimanalmente
```

---

## Session boundary

After completing a step, advise:
```
Step {N} completato. Il prossimo step ({title}) funziona meglio in una sessione nuova.
Lancia /brain-init-work per continuare — riparte da dove siamo rimasti.
```

## Notes

- Full init: 2-4 sessions depending on sources
- Steps 2-4 can run in one session if sources are light
- Steps 5-6 should each be a separate session
- User can skip any step with setup_status(action="update", status="skipped")
- Always communicate in Italian
