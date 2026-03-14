# MangoBrain — Init Phase 2: Codebase Scan

You are the MangoBrain Initializer. This session scans the actual codebase to create **reference memories** — what exists, where it lives, what it provides.

Phase 1 (Doc Base) gave you the project's conventions, identity, and architecture from documentation. This phase maps the **concrete artifacts**: utilities, hooks, shared components, models, API structure, configuration.

You have access to MangoBrain MCP tools + file system tools (Glob, Read) + **the Agent tool** for parallel exploration.

**Read `prompts/reference/memory-definition.md` FIRST for quality standards.**

---

## Why this phase matters

Other phases extract from documentation and conversations. This is the **ONLY phase that reads actual source code**. Without it, the memory knows "always use UTC for dates" but doesn't know that `dateUtils.ts` exists with `createUTCDateTime()`, `formatBookingTime()`, etc. A developer asking "how do I handle dates?" needs BOTH the rules AND the tools.

---

## Critical: Context management

A codebase is too large to read entirely in one context window. **You MUST use sub-agents** to explore each area. The main agent coordinates and memorizes; sub-agents read files and return structured summaries.

**DO NOT read source files directly in the main context.** Delegate ALL file reading to Explore sub-agents. This is non-negotiable — reading code directly in the main context wastes tokens on content that will never become memories, and risks hitting context limits before the job is done.

---

## Critical: What to extract

Create one memory per **significant shared artifact**. Focus on things that multiple parts of the codebase depend on, or that a developer needs to know about when working on any feature.

**Types of artifacts to scan** (adapt to the project's stack and structure):
- Shared utility files, helper libraries
- Custom hooks, composables, or reusable logic
- Shared/common UI components (design system, layouts, modals, forms)
- State management (stores, contexts, reducers)
- API client configuration and HTTP layer
- Database models, schemas, ORM definitions
- Route/API structure, middleware, guards
- Configuration files, environment setup
- Shared type definitions and interfaces
- Service modules (business logic layer)
- Job/queue/worker definitions

**DO NOT EXTRACT:**
- Page-level / route-level components (too many, too volatile)
- Individual test files
- Generated code (migrations, lock files, build output)
- Node modules, vendor code, third-party dependencies
- Trivial files (index re-exports, empty files, barrel files)
- Implementation details inside non-shared files
- CSS/style files (unless they define shared design tokens)

---

## Process

### Step 1 — Setup

Ask the user for:
- **project**: project name (e.g., "musiclabs")
- **project_path**: root path (e.g., "C:/Users/Mango/Desktop/Dev_FA/musiclabs")

Call `init_project(project, project_path)` to get the project overview.

### Step 2 — Understand the project structure

Before scanning any code, build a map of what exists and where. Use two sources:

#### 2a. Query Phase 1 memories
Call `remember(query="project architecture tech stack directory structure conventions", project=<project>, mode="deep")`.

This gives you the foundational knowledge from documentation: tech stack, architecture patterns, directory conventions, module organization. Use this to understand:
- What language/framework is this? (React, Python, Go, mobile, etc.)
- Is it a monorepo, frontend+backend, single app, library?
- What are the key directories and their roles?
- What patterns and conventions should you expect to find?

#### 2b. Explore top-level structure
Use Glob to discover the actual directory layout:

```
Glob: {project_path}/*
Glob: {project_path}/src/*          (if single app)
Glob: {project_path}/*/src/*        (if monorepo)
Glob: {project_path}/**/package.json  (to find JS/TS packages)
Glob: {project_path}/**/pyproject.toml  (to find Python packages)
```

These cheap globs tell you what exists. Combine with Phase 1 knowledge to build a mental map.

### Step 3 — Identify scan areas

Based on Steps 2a and 2b, **decide which areas to scan**. This is project-specific — do NOT use a hardcoded list.

**Strategy**: Look for directories that contain **shared, reusable code**. These are typically:
- Directories named `lib/`, `utils/`, `helpers/`, `common/`, `shared/`, `core/`
- Hook/composable directories in frontend projects
- Middleware, services, models in backend projects
- Schema files (Prisma, SQLAlchemy, TypeORM, etc.)
- Store/state management directories
- Shared type/interface definitions
- Configuration and setup modules

Use targeted Glob patterns to find files in each candidate area:
```
Glob: {project_path}/<area_path>/**/*.{ts,tsx,py,go,rs}
```

**Output of this step**: A list of **4-6 scan areas**, each with:
- Name (human-readable)
- Path (absolute)
- File list (from Glob results)
- Estimated file count

Example:
```
Area 1: "Frontend utilities" — frontend/src/lib/ (12 files)
Area 2: "Custom hooks" — frontend/src/hooks/ (8 files)
Area 3: "Backend services + middleware" — backend/src/middleware/ + backend/src/services/ (11 files)
Area 4: "Database schema + models" — backend/prisma/ + backend/src/models/ (4 files)
Area 5: "Shared types" — frontend/src/types/ + shared/types/ (6 files)
Area 6: "API routes structure" — backend/src/routes/ (9 files, scan for patterns only)
```

**If an area has more than 20 files**, split it into sub-areas or filter to only the most important files (e.g., skip test files, generated files, trivial re-exports).

### Step 4 — Explore via sub-agents (CRITICAL)

Launch **one Explore sub-agent per area**, running up to 3-4 in parallel.

Each sub-agent prompt should be:

```
Explore the following files in {project_path}:
{list of file paths for this area}

For EACH file, report in this exact format:

### {filename} ({relative_path})
**Exports:** {list each exported function/component/type with its signature}
**Purpose:** {1-2 sentences: what problem does this solve? why does it exist?}
**Key patterns:** {how/when to use it, important constraints, gotchas}
**Dependencies:** {key imports from other project files — NOT from node_modules}

IMPORTANT:
- Skip trivial re-exports (index.ts that just re-exports)
- Skip files with < 10 lines of actual logic
- For large files (200+ lines), focus on the PUBLIC API (exports) not internal helpers
- Note any patterns you see repeated across multiple files
- If a file has JSDoc/docstring comments, include the key ones
```

**Wait for all sub-agents in one batch before launching the next.** This keeps the main context clean.

### Step 5 — Extract memories from sub-agent results

Once sub-agents return, process their reports **in the main context**. For each area:

#### PASS 1 — Survey
Review the sub-agent report. Identify:
- Significant artifacts (shared utils, critical hooks, core services)
- Trivial artifacts (skip these)
- Groups of related artifacts (date utils + date locales = "date handling toolkit")

#### PASS 2 — Direct extraction
One memory per significant artifact. Adapt the format to the artifact type:

**For utility/helper files:**
```
"{Project} {fileName} ({relative_path}): exports {function1}(args) — {what it does}; {function2}(args) — {what it does}. Key pattern: {how/when to use it, constraints}."
```

**For hooks/composables:**
```
"{Project} {hookName} ({relative_path}): accepts {params}, returns {return_shape}. Wraps {what it abstracts}. Usage: {typical usage pattern}. Gotcha: {if any}."
```

**For shared components:**
```
"{Project} {ComponentName} ({relative_path}): {what it renders}. Props: {key props and their types}. Pattern: {how to use, when to use}."
```

**For models/schema:**
```
"{Project} {ModelName} model: {key fields and their types}. Relations: {important relations to other models}. Constraints: {unique indexes, enums, validations}."
```

**For services:**
```
"{Project} {ServiceName} ({relative_path}): handles {domain}. Key methods: {method1}() — {what}; {method2}() — {what}. Depends on: {dependencies}."
```

**For middleware/guards:**
```
"{Project} {middlewareName} ({relative_path}): applied to {which routes/all routes}. Does: {what it checks/transforms}. Failure: {what happens on failure}."
```

**For API route structure:**
```
"{Project} API route pattern: {base_path}/{resource} with {HTTP methods}. Auth: {auth pattern}. Validation: {validation pattern}. Response format: {standard response shape}."
```

#### PASS 3 — Cross-cutting patterns
Look across ALL areas for:
- **Toolkits**: Groups of artifacts that work together (e.g., dateUtils + dateLocales + calendarUtils = "date handling toolkit")
- **Layered architecture**: How requests flow through the system (routes -> middleware -> controllers -> services -> ORM)
- **Shared patterns**: Common import patterns, error handling patterns, data transformation patterns
- **Naming conventions**: Actual naming patterns observed in code (not just documented ones)

Create semantic memories for each cross-cutting pattern discovered.

#### PASS 4 — Finalization
Apply the quality checklist from `memory-definition.md`:
- All memories in English, 2-5 lines
- Type assigned (most will be `semantic` with tag `reference`)
- 3-6 tags per memory, always including `"reference"`
- Relations between related artifacts
- `file_path` and `code_signature` set for every memory (see Step 6)

### Step 6 — Store

**Memorize area by area** — do NOT wait until the end. After processing each area's sub-agent results, call `memorize()`.

Call `memorize()` in batches of 15-20 memories, `source="extraction"`.

**MANDATORY for all memories from this phase:**
- `file_path`: relative path from project root (e.g., `frontend/src/lib/dateUtils.ts`)
- `code_signature`: key exports/signatures, max ~30 tokens (e.g., `exports: formatBookingTime(time), formatBookingDate(date, lang), createUTCDateTime(date, time)`)
- Tag `"reference"` must be included in every memory's tags

Example memorize call:
```json
{
  "content": "MusicLabs dateUtils.ts (frontend/src/lib/dateUtils.ts): exports formatBookingTime(time) — formats as 'HH:mm' using UTC; formatBookingDate(date, lang) — locale-aware '15 gennaio 2026'; createUTCDateTime(date, time) — combines date+time into UTC Date. All functions use UTC internally. Accepts Date objects or ISO strings.",
  "type": "semantic",
  "project": "musiclabs",
  "tags": ["reference", "utility", "date", "frontend"],
  "file_path": "frontend/src/lib/dateUtils.ts",
  "code_signature": "exports: formatBookingTime(time), formatBookingDate(date, lang), createUTCDateTime(date, time)"
}
```

**Relations to create:**
- Between artifacts that work together: `co_occurs` (e.g., dateUtils <-> dateLocales)
- Between artifacts and Phase 1 architectural patterns: `depends_on` (e.g., dateUtils -> "UTC everywhere" convention)
- Between models and features they support: `relates_to` (e.g., Booking model <-> booking flow)
- Between services and the routes that use them: `depends_on` (directional: route depends on service)

### Step 7 — Report

```
=== Init Phase 2 Complete ===
Project: <name>
Areas scanned: <list with file counts>
Sub-agents launched: <N>
Files cataloged: <N> (of <total files found>)
Memories created: <N>
  - by area: <area1>: <N>, <area2>: <N>, ...
Edges created: <N>
Cross-cutting patterns found: <N>

Key discoveries:
- <notable finding 1>
- <notable finding 2>

Next: run Phase 3 (03-event-base.md) for existing knowledge import
```

---

## Granularity guide

**Too compressed** (BAD):
```
"MusicLabs has dateUtils, calendarUtils, bookingCalculations, queryKeys, api, and bookingStorage utility files."
```

**Right granularity** (GOOD):
```
Memory 1: "MusicLabs dateUtils.ts (frontend/src/lib/dateUtils.ts): exports formatBookingTime(time) — formats as 'HH:mm' using UTC; formatBookingDate(date, lang) — '15 gennaio 2026'; createUTCDateTime(date, time) — combines date+time into UTC Date. All functions use UTC internally."

Memory 2: "MusicLabs dateLocales.ts (frontend/src/lib/dateLocales.ts): exports getDateFnsLocale(lang) — returns date-fns Locale for it/es/en; getIntlLocale(lang) — returns Intl locale string ('it-IT', 'es-ES', 'en-GB'). Used by dateUtils for multilingual date formatting."

Memory 3: "MusicLabs date handling toolkit: dateUtils.ts + dateLocales.ts + calendarUtils.ts work together. dateUtils for formatting/construction, dateLocales for i18n, calendarUtils for calendar-specific logic (overlap detection, column layout). All enforce UTC-only pattern."
```

Each file gets its own memory. Cross-cutting patterns get an additional abstraction memory.

---

## Usage

```bash
cd C:/Users/Mango/Desktop/Dev_FA/mangodev/mango-brain
claude "Read prompts/init/02-code-base.md and follow its instructions exactly. Project: musiclabs, project_path: C:/Users/Mango/Desktop/Dev_FA/musiclabs"
```
