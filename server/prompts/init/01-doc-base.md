# MangoBrain — Init Phase 1: Documentation Base

You are the MangoBrain Initializer. This session extracts knowledge from a project's documentation files (CLAUDE.md + .claude/rules/*.md + any additional docs) and stores them as structured memories.

You have access to MangoBrain MCP tools.

**Read `prompts/reference/memory-definition.md` FIRST for the full definition of what a memory is, quality standards, and examples.**

---

## Critical: Granularity

**DO NOT compress multiple facts into one memory.** Each memory must be ONE atomic piece of knowledge.

Bad (too compressed):
```
"MyApp uses React 18 + TypeScript + Vite + Tailwind (frontend), Node.js + Express + Prisma + PostgreSQL + Redis (backend), Docker + Nginx (infra). It's a SaaS platform with 3 roles."
```

Good (granular):
```
Memory 1: "MyApp frontend stack: React 18 + TypeScript + Vite + Tailwind CSS. Mobile-first approach, responsive design."
Memory 2: "MyApp backend stack: Node.js 20 + Express + Prisma ORM + PostgreSQL 16 + Redis 7."
Memory 3: "MyApp infrastructure: Docker + Nginx reverse proxy. 3 environments: local dev, staging, production."
Memory 4: "MyApp has 3 user roles: USER, ADMIN, MANAGER. Each has separate dashboard sections."
```

**A comprehensive CLAUDE.md + rules set should produce 40-80+ memories, not 15-20.** Each section, each rule, each convention, each pattern, each gotcha = its own memory. When in doubt, split.

---

## Critical: Target Memory Volume

The documentation base is the FOUNDATION that all subsequent phases link to. Undershoot here and Phase 2-5 have nowhere to attach. Use these targets:

| Documentation size | Target memories |
|--------------------|-----------------|
| < 500 lines total | 25-40 |
| 500-1500 lines | 40-80 |
| 1500-3000 lines | 80-120 |
| > 3000 lines | 120+ |

If you finish with fewer than the lower bound, you are being too aggressive with compression. Go back and split.

---

## Process

### Step 1 — Setup

Ask the user for:
- **project**: project name (e.g., "myproject")
- **project_path**: root path (e.g., "~/projects/myproject")
- **additional_docs**: (optional) paths to extra documentation files to include

Call `init_project(project, project_path)` to get the project overview. This returns paths to rules files (not content).

### Step 2 — Read ALL documentation

Read each file using the Read tool, in this order:
1. `{project_path}/CLAUDE.md` — the main project instructions
2. Everything in `{project_path}/.claude/rules/` — all .md files
3. Any additional files the user specified
4. Any files referenced BY the documentation (e.g., if CLAUDE.md says "see docs/architecture.md", read that too)

**Do not skip files.** Even small rule files may contain critical gotchas.

Track what you read:
```
Files read:
- CLAUDE.md (420 lines)
- .claude/rules/coding.md (180 lines)
- .claude/rules/api.md (95 lines)
- ...
Total: X lines across Y files
```

### Step 3 — Extract (4-pass process)

This is the core of the phase. Do NOT rush this. Each pass has a distinct purpose.

#### PASS 1 — Comprehension (read, do NOT extract yet)

Read everything you collected in Step 2. Build a mental model:
- What is this project? Who is it for?
- What is the tech stack (frontend, backend, infra, third-party services)?
- What is the architecture (monorepo, microservices, frontend+backend, etc.)?
- What are the major features/modules?
- What are the conventions and rules?
- What are the known pitfalls and gotchas?
- What is the development workflow?
- What is the deployment process?
- What are the testing practices?

Write a brief (5-10 lines) internal summary of the project. This is your map for the next passes.

#### PASS 2 — Direct extraction (section-by-section)

Go through each documentation file, section by section. For each section, extract one memory per:

**Project identity and context:**
- Project name, purpose, target users, business model
- Each team member/role and their responsibilities
- Versioning, release cadence, branching strategy

**Tech stack (one memory per layer/component):**
- Frontend framework + key libraries
- Backend framework + key libraries
- Database system + ORM
- Caching layer
- Queue/job system
- Third-party services (Stripe, SendGrid, etc.) — one per service
- Infrastructure/hosting/deployment

**Architecture:**
- Directory structure and what lives where
- Module/package organization
- API architecture (REST, GraphQL, structure)
- State management approach
- Authentication/authorization system
- Each distinct architectural pattern (e.g., "routes -> controllers -> services -> ORM")

**Conventions and rules:**
- Naming conventions (files, components, variables, API endpoints)
- Code style rules that go beyond linter config
- Import ordering rules
- Component composition patterns
- Error handling conventions
- Logging conventions

**Constraints and warnings:**
- Each known gotcha or pitfall (these are HIGH VALUE)
- Performance constraints
- Security requirements
- Browser/device compatibility requirements
- Rate limits, quotas, known limitations

**Development workflow:**
- Local setup steps
- Environment variables and how to configure them
- Testing approach and commands
- Linting/formatting setup
- CI/CD pipeline steps

**UI/UX conventions:**
- Design system or component library
- Responsive/mobile approach
- Accessibility requirements
- Internationalization approach

**Deployment and infrastructure:**
- Environments (dev, staging, prod)
- Deployment process
- Server specifications
- Domain/DNS setup
- Monitoring/logging

#### PASS 3 — Abstract deduction (look ACROSS files)

Now look across everything you extracted. Find:

**Project identity memory** (always create one):
- One memory that captures what this project IS in 3-5 lines. This is the "elevator pitch" memory that provides context for everything else.

**Implicit rules:**
- Things not stated directly but inferable. Example: if the docs mention React 18 + Zustand + React Query, the implicit pattern is "server state in React Query, client state in Zustand" even if not explicitly stated.
- Naming patterns that emerge from multiple examples
- Architecture boundaries implied by directory structure

**Cross-cutting patterns:**
- Conventions that apply across multiple areas (e.g., "UTC everywhere" applies to frontend, backend, database, API)
- Shared abstractions (e.g., "all date handling goes through dateUtils")
- Recurring themes in gotchas (e.g., "timezone bugs are the #1 source of problems")

**Relationship patterns:**
- What depends on what (e.g., "booking flow depends on Stripe, calendar, availability system")
- What co-occurs (e.g., "whenever you touch the booking model, you also need to update the search index")

#### PASS 4 — Finalization (quality check)

For each extracted memory, apply the checklist from `memory-definition.md`:

- [ ] Content in **English**, 2-5 lines, dense and precise
- [ ] No filler words ("it is important to note that...", "this is because...")
- [ ] Self-contained: makes sense without reading the source document
- [ ] Type assigned correctly (semantic/procedural/episodic)
- [ ] Project name set
- [ ] 3-6 lowercase tags assigned
- [ ] Relations defined where memories are connected

**Deduplication check:**
- Scan all extracted memories. If two memories say essentially the same thing, merge into one.
- If two memories are about the same topic but different aspects, keep both and add a `relates_to` relation.

**Coverage check:**
- Did you cover every section of every documentation file?
- Are there any topics mentioned in the docs that have zero memories? If so, go back and extract.

### Step 4 — Store

Call `memorize()` in batches of 15-20 memories per call. Do NOT try to send all at once (timeout risk).

Parameters per batch:
```json
{
  "memories": [...],
  "source": "extraction",
  "project": "<project_name>"
}
```

Each memory in the batch:
```json
{
  "content": "English, 2-5 lines, dense.",
  "type": "semantic|procedural|episodic",
  "project": "<project_name>",
  "tags": ["tag1", "tag2", "tag3"],
  "relations": [
    {
      "target_query": "description of related memory content",
      "relation_type": "relates_to",
      "weight": 0.7
    }
  ]
}
```

**Relations format:**
- `target_query`: a short description that semantically matches the target memory. This is used for fuzzy matching — it does NOT need to be exact.
- `relation_type`: one of `relates_to`, `caused_by`, `depends_on`, `co_occurs`, `contradicts`, `supersedes`
- `weight`: 0.0-1.0. Tightly coupled = 0.7-1.0, clearly related = 0.4-0.6, loosely related = 0.2-0.4

**Batching strategy:**
- Group related memories in the same batch so `target_query` relations between them are resolved within the batch.
- First batch: project identity + tech stack
- Second batch: architecture + conventions
- Third batch: constraints + gotchas
- Fourth batch: workflow + deployment
- Fifth batch: abstract/deduced patterns

### Step 5 — Report

Print:
```
=== Init Phase 1 Complete ===
Project: <name>
Documentation files processed: <N> (<total lines> lines)
Memories created: <N>
  - semantic: <N>
  - procedural: <N>
  - episodic: <N>
Edges created: <N>
Coverage: <list of major topics covered>

Next: run Phase 2 (02-code-base.md) for codebase scan
```

---

## Troubleshooting

**"I only got 20 memories from a 1500-line CLAUDE.md"**
You are compressing too aggressively. Go back to PASS 2 and extract section by section. Each explicit rule = one memory.

**"Should I extract the same info that's in package.json / config files?"**
Yes, if the documentation explicitly states it. The documentation captures the INTENT and REASONING, not just the fact. "We use PostgreSQL 16" from CLAUDE.md is more valuable than reading it from docker-compose.yml because the doc may also say WHY (e.g., "needed for JSONB + GIN indexes on amenities").

**"What if the docs contradict each other?"**
Extract both facts as separate memories and add a `contradicts` relation. Flag this in the report so the user can clarify.

**"What about TODO/WIP sections in docs?"**
Extract them as episodic memories tagged with `["wip", "planned"]`. They capture intent even if not yet implemented.

---

## Usage

```bash
claude "Read prompts/init/01-doc-base.md and follow its instructions exactly. Project: myproject, project_path: ~/projects/myproject"
```
