# What is a Memory?

A memory is **one autonomous unit of knowledge**. It must make sense on its own when returned by `remember()` — if you read it out of context, you understand what it says, why it matters, and how to act on it.

This document is the **canonical reference** for memory quality. All prompts that create, update, or evaluate memories MUST follow these standards.

---

## Length

**2-5 lines.** This is a hard constraint.

- **Below 2 lines**: likely too vague or missing context. A memory that says "use UTC for dates" is useless — WHERE? WHY? WHAT happens if you don't?
- **Above 5 lines**: likely contains multiple facts compressed together. Split into multiple memories.
- **Sweet spot**: 3-4 lines. Enough for the fact + its context + actionable implication.

---

## Language

**English. Always.** Even if the project's documentation or conversations are in Italian or another language.

Reason: embedding models (bge-large-en-v1.5) perform best on English text. Semantic search quality degrades significantly with mixed languages. All memories in English ensures consistent retrieval quality.

---

## Granularity

**One fact, one decision, one bug, one pattern = one memory.**

This is the most critical quality attribute. Embedding-based retrieval works on semantic similarity. A memory about "booking wizard price conversion bug: cents vs euros double-division in BookingSidebar" will match a query about price bugs FAR better than a memory that lists 5 unrelated bugs.

**The granularity test:** If removing a sentence from the memory would make it about a different topic, that sentence should be its own memory.

If two facts are related but independently useful, make two memories and connect them with a `relates_to` relation.

---

## Self-containedness

A memory must be readable WITHOUT external context. It should not assume the reader has seen the source document, the chat session, or any other memory.

**Bad:** "The fix was to use the UTC version instead."
→ Fix of what? UTC version of what? Instead of what?

**Good:** "MusicLabs booking time display bug: getDay() returns local timezone day-of-week, causing bookings to show on the wrong day for users in non-UTC timezones. Fix: use getUTCDay() instead. This pattern applies to all Date getter methods — always use the UTC variant."

---

## Types

### Episodic
A specific event that happened — a bug found, a decision made in a specific session, a refactor done on a specific date. Has temporal context (when it happened matters).

**Decay:** fastest. Episodic memories lose relevance as the codebase evolves. A bug fixed 6 months ago may no longer be relevant if the component was rewritten.

**Examples:**
- "In the Feb-12 session, discovered that the booking sidebar double-divided the price (cents -> euros -> euros/100). Root cause: formatPrice() expected cents but received euros from the updated API."
- "Decision (2025-01): switched from REST to tRPC for internal admin API. Motivation: type safety across frontend/backend without manual OpenAPI sync."

### Semantic
General knowledge, facts, architecture, patterns — true regardless of when. "MusicLabs uses PostgreSQL with Prisma ORM" is semantic. Conventions, rules, architecture descriptions, technology facts.

**Decay:** slowest. These remain valid until the architecture changes.

**Examples:**
- "MusicLabs frontend stack: React 18 + TypeScript + Vite + Tailwind CSS. Mobile-first approach, 90%+ users expected on mobile."
- "All Reverbia API endpoints follow the pattern: /api/v1/{resource}. Auth via JWT in Authorization header. Validation via Zod schemas at the route level."

### Procedural
How-to knowledge, step-by-step processes, conventions to follow — "Always run docker-compose up -d before testing API locally" is procedural. These are instructions, not facts.

**Decay:** medium. Procedures change when tooling or workflow changes.

**Examples:**
- "To add a new API endpoint in MusicLabs: 1) Create route in backend/src/routes/{resource}.ts, 2) Add Zod validation schema, 3) Create service method in backend/src/services/, 4) Add route to router in index.ts. Always test with Postman collection first."
- "MusicLabs price convention: API always returns and accepts cents (integer). Frontend formats to euros only for display using formatPrice(cents). Never store or transmit euros — only cents."

---

## Tags

**3-6 tags per memory.** Lowercase, hyphenated for multi-word tags.

Tags serve two purposes:
1. **Filtering**: `remember(query=..., tags=["booking"])` narrows results
2. **Clustering**: memories with shared tags form natural topic groups

**Tag vocabulary conventions:**
- Use consistent, project-wide tag names. Don't use "stripe" in one memory and "payments" in another for the same concept.
- Include at least one **area tag** (e.g., "booking", "auth", "calendar", "payments")
- Include at least one **type tag** (e.g., "bug", "convention", "reference", "gotcha", "architecture")
- Optionally include **tech tags** (e.g., "react", "prisma", "stripe", "redis")

**Common tags:**
- `reference` — for code artifact memories (utilities, hooks, components, models)
- `convention` — for rules and coding standards
- `gotcha` — for known pitfalls and traps (HIGH VALUE)
- `bug` — for bug root causes and fixes
- `architecture` — for system design decisions
- `wip` — for work-in-progress state
- `state` — for current project state snapshots
- `pattern` — for recurring patterns
- `abstraction` — for memories synthesized from multiple sources

---

## Relations

Relations are **edges in the knowledge graph**. They connect memories to each other and enable graph-based retrieval — finding memories that are semantically distant but structurally related.

### Format
```json
{
  "target_query": "description that semantically matches the target memory",
  "relation_type": "relates_to",
  "weight": 0.7
}
```

### target_query
A short description (5-15 words) that will be used for **semantic search** to find the target memory. It does NOT need to be an exact match — it needs to be close enough in embedding space.

**Good:** `"dateUtils UTC formatting booking time"`
**Bad:** `"memory #47"` or `"the one about dates"`

### Relation types and their retrieval semantics

| Type | Direction | Effect in retrieval | When to use |
|------|-----------|-------------------|-------------|
| `relates_to` | symmetric | Both boost each other | Same topic area, complementary information |
| `depends_on` | directional (A->B) | Querying A finds B, not vice versa | A needs B to work: component->utility, feature->config |
| `caused_by` | directional (A->B) | Querying A finds B, not vice versa | A exists because of B: bug->decision, refactor->incident |
| `co_occurs` | symmetric | Both boost each other | Always appear together. Usually auto-created, rarely manual |
| `contradicts` | symmetric | **Negative**: A pushes B DOWN | Conflicting information, outdated-vs-current (when keeping both) |
| `supersedes` | asymmetric | Finding old boosts new; finding new pushes old down | One memory is clearly more current/complete than another |

### Weight
- **0.7-1.0**: Tightly coupled (same feature, direct dependency)
- **0.4-0.6**: Clearly related (same module, shared concepts)
- **0.2-0.4**: Loosely related (same project area, tangential connection)

### When to add relations
- **Always** when two memories discuss the same file, component, or feature
- **Always** when one memory explains the WHY behind another
- **Always** when a bug memory relates to a convention memory (the bug violated the convention)
- **Usually** when memories share 2+ tags
- **Sometimes** when memories are about the same project area but different aspects

---

## file_path

**Mandatory for code-related memories.** Relative path from project root.

```
file_path: "frontend/src/lib/dateUtils.ts"
file_path: "backend/src/routes/bookings.ts"
file_path: "prisma/schema.prisma"
```

Purpose: enables `sync_codebase()` to detect when the referenced file changes and flag the memory as potentially stale.

**When to include:**
- Reference memories about utilities, hooks, components, services, models
- Bug memories about specific files
- Feature memories that modified specific files

**When NOT to include:**
- Abstract pattern memories not tied to a specific file
- Convention memories that apply project-wide
- Architecture memories about the overall system

---

## code_signature

**Encouraged for reference memories.** Captures the public API of a code artifact in ~30 tokens.

```
code_signature: "exports: formatBookingTime(time), formatBookingDate(date, lang), createUTCDateTime(date, time)"
code_signature: "hook: useBookingWizard(initialData) -> {step, setStep, data, updateData, reset}"
code_signature: "model: Booking {id, studioId, userId, startTime, endTime, status, paymentId}"
```

Purpose: enables `sync_codebase()` to detect when exports/signatures change, indicating the memory content may be stale.

---

## What makes a GOOD memory

- **Self-contained**: readable without any external context
- **Specific**: answers a concrete question someone might ask
- **Actionable**: helps a future session make a better decision or avoid a mistake
- **Dense**: no filler words, no "it is important to note that...", just the knowledge
- **Correctly typed**: episodic for events, semantic for facts, procedural for processes
- **Well-tagged**: 3-6 relevant, consistent tags
- **Connected**: has relations to related memories in the graph

## What makes a BAD memory

- **Generic**: "The booking system has had many bugs" — which bugs? why? what to avoid?
- **Aggregated**: "Fixed bugs in booking wizard, room detail page, payment flow, and calendar" — this is 4 memories compressed into 1, none of which is retrievable individually
- **Too long**: More than 5 lines. Split it.
- **Raw code**: "File: BookingWizardPage.tsx, line 42, uses useState with lazy initializer" — this is a code observation, not knowledge
- **Orphaned**: No relations, no file_path, vague tags — will never be found by retrieval
- **Duplicative**: Says the same thing as another memory in different words
- **Filler-heavy**: "It should be noted that an important consideration is that..." — cut to the fact

---

## Quality checklist (use before every memorize call)

For each memory, verify:

- [ ] **English**, 2-5 lines
- [ ] **One fact** per memory (granularity test passed)
- [ ] **Self-contained** (makes sense without context)
- [ ] **Dense** (no filler words)
- [ ] **Type** correctly assigned (episodic/semantic/procedural)
- [ ] **Project** name set
- [ ] **Tags**: 3-6, lowercase, consistent vocabulary
- [ ] **Relations**: at least 1 if the memory relates to any known topic
- [ ] **file_path**: set if the memory references a specific file
- [ ] **code_signature**: set if the memory is a reference to a code artifact
- [ ] **Not a duplicate**: does not repeat an existing memory

---

## Examples

### Good: Bug root cause (episodic)
```json
{
  "content": "MusicLabs booking price display bug (2025-01): BookingSidebar showed price divided by 100 twice. Root cause: formatPrice() expects cents (integer), but the BookingSidebar was pre-dividing to euros before calling it. API contract: all prices in cents. Lesson: never convert cents->euros before passing to formatPrice().",
  "type": "episodic",
  "project": "musiclabs",
  "tags": ["bug", "booking", "price", "gotcha"],
  "file_path": "frontend/src/components/booking/BookingSidebar.tsx",
  "relations": [
    {"target_query": "formatPrice cents euros conversion utility", "relation_type": "depends_on", "weight": 0.8},
    {"target_query": "API price convention cents integer", "relation_type": "caused_by", "weight": 0.7}
  ]
}
```

### Good: Convention (semantic)
```json
{
  "content": "MusicLabs uses UTC everywhere for dates. Construction: Date.UTC(year, month-1, day). Reading: getUTCHours(), getUTCDay(). Local time methods (setHours, getDay, new Date(string)) caused 12+ timezone bugs across frontend and backend. All date formatting goes through dateUtils.ts.",
  "type": "semantic",
  "project": "musiclabs",
  "tags": ["convention", "date", "timezone", "utc"],
  "relations": [
    {"target_query": "dateUtils exports formatBookingTime createUTCDateTime", "relation_type": "relates_to", "weight": 0.8}
  ]
}
```

### Good: Reference (semantic)
```json
{
  "content": "MusicLabs dateUtils.ts (frontend/src/lib/dateUtils.ts): exports formatBookingTime(time) — formats as 'HH:mm' using UTC; formatBookingDate(date, lang) — locale-aware '15 gennaio 2026'; createUTCDateTime(date, time) — combines date+time into UTC Date. All functions use UTC internally. Accepts Date objects or ISO strings.",
  "type": "semantic",
  "project": "musiclabs",
  "tags": ["reference", "utility", "date", "frontend"],
  "file_path": "frontend/src/lib/dateUtils.ts",
  "code_signature": "exports: formatBookingTime(time), formatBookingDate(date, lang), createUTCDateTime(date, time)",
  "relations": [
    {"target_query": "UTC date convention timezone pattern", "relation_type": "depends_on", "weight": 0.8},
    {"target_query": "dateLocales getDateFnsLocale multilingual", "relation_type": "co_occurs", "weight": 0.6}
  ]
}
```

### Good: Process (procedural)
```json
{
  "content": "MusicLabs price handling convention: API always returns and accepts cents (integer). Frontend displays euros only via formatPrice(cents). Never store, transmit, or calculate with euros — only cents. When creating a price: Math.round(euros * 100). When displaying: formatPrice(cents) handles the /100 + locale formatting.",
  "type": "procedural",
  "project": "musiclabs",
  "tags": ["convention", "price", "money", "api"],
  "relations": [
    {"target_query": "formatPrice utility function money display", "relation_type": "relates_to", "weight": 0.8},
    {"target_query": "booking price bug cents euros double division", "relation_type": "relates_to", "weight": 0.7}
  ]
}
```

### Bad: Too vague
```
"The booking system has had many bugs."
```
Which bugs? What patterns? What to watch out for?

### Bad: Too aggregated
```
"Fixed bugs in booking wizard, room detail page, payment flow, and calendar component."
```
Four topics compressed. None is individually retrievable. Split into 4 memories.

### Bad: Raw code observation
```
"File: BookingWizardPage.tsx, line 42, uses useState with lazy initializer."
```
This is a code fact, not knowledge. Extract the WHY: why lazy initializer? What happens without it?

### Bad: Meta/conversational
```
"The user asked me to fix the booking price, and I found the bug was in formatPrice."
```
Remove the conversation wrapper. Just state the knowledge.

### Bad: Too long (>5 lines)
```
"MusicLabs uses React 18 with TypeScript and Vite for the frontend build system. Tailwind CSS is used for styling with a mobile-first approach. The backend runs on Node.js 20 with Express and uses Prisma as the ORM connecting to PostgreSQL 16. Redis 7 is used for caching and session storage. Docker containerizes everything with Nginx as a reverse proxy. There are three environments: local development, a test server on Hetzner CX23, and production on Hetzner CX33. The CI/CD pipeline runs on GitHub Actions."
```
This is 7+ facts compressed. Split into: frontend stack, backend stack, database+cache, infrastructure, environments, CI/CD.
