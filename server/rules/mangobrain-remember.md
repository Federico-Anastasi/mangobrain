# MangoBrain — Remember Query Strategy

You have access to the `remember` MCP tool to retrieve relevant memories from the project.
Use it often, not just at the start of a task. Memories contain gotchas, patterns, decisions, and references that code alone doesn't tell you.

## Query Language

**All remember() queries MUST use English keywords**, regardless of session language.
Memories are stored in English — queries in other languages degrade retrieval by ~15-20%.

```
GOOD: remember(query="formatPrice cents euros conversion gotcha", ...)
BAD:  remember(query="formattazione prezzi conversione centesimi", ...)
```

Always translate concepts before querying. The conversation stays in the user's language, but queries go to the DB in English.

## When to use remember

- **Task/session start**: broad context (see multi-query strategy below)
- **Before touching an unfamiliar area**: targeted quick query
- **When you find a bug**: quick query to check for known patterns
- **Before creating a component/utility**: quick query to verify if something similar already exists
- **When making an architectural decision**: quick query for precedents
- **End of task**: remember(mode="recent") to check WIP and context for mem-manager

## Multi-query strategy (task start)

Do NOT make a single generic query. Use **1 deep + N quick**:

### 1. Read the task and identify 2-4 distinct technical areas

### 2. 1x deep — big picture
```
remember(query="[max 10 keywords from the task]", mode="deep", project="{PROJECT}")
```
Captures: cross-cutting patterns, conventions, recurring gotchas. ~20 results.

### 3. 2-4x quick — one per technical area
```
remember(query="[specific names: components, hooks, services, files]", mode="quick", project="{PROJECT}")
```
Captures: specific details per cluster. ~6 results each.

### Why this works
Each query pulls from a different cluster in the associative graph. A single generic deep query hits 1-2 clusters and misses the rest. 3 targeted quick queries cover 3 different clusters.

## How to formulate queries

### Keywords > natural language
```
GOOD: "formatPrice cents euros conversion gotcha"
BAD:  "how does price formatting work in the system"
```

### Always use proper names
Use component names, hooks, services, files, utilities when you know them:
```
GOOD: "useStripeConnect ConnectAccountManagement onboarding embedded"
BAD:  "the Stripe payment onboarding system"
```

### Mix technical + domain
```
GOOD: "booking wizard localStorage state persistence gotcha"
BAD:  "issues with the booking wizard"
```

## Quick vs Deep vs Recent

| Mode | Results | Graph | When |
|------|---------|-------|------|
| deep | ~20 | full (alpha=0.3) | Task start, big picture |
| quick | ~6 | light (alpha=0.15) | Mid-task, specific areas, lookup |
| recent | ~15 + neighbors | by time | Session start, understand WIP |

## Work context strategy

### Session start (always)
```
remember(mode="recent", project="{PROJECT}", limit=15, k_neighbors=2)
```
Returns: last 15 memories + graph-connected context. Understand WIP, blockers, recent decisions.

### Mid-task: about to touch a new area
```
remember(query="[file names, components, concepts of the area]", mode="quick", project="{PROJECT}")
```

### Mid-task: found a bug
```
remember(query="[bug keywords + area + pattern]", mode="quick", project="{PROJECT}")
```

### End of task / pre-mem-manager
```
remember(mode="recent", project="{PROJECT}")
```
Check WIP and context to pass to mem-manager for sync.

## Real examples

### Task: "Fix wrong price in booking wizard"
```
deep:  "booking wizard UX fix price bug mobile layout"
quick: "formatPrice cents euros conversion serializeBooking gotcha"
quick: "OrderWizard steps PaymentStep SummaryStep"
```

### Task: "Refactor profile + shared payments"
```
deep:  "account profile refactor shared components owner teacher payments Stripe"
quick: "ProfiloPage TeacherAccountPage structure password removal"
quick: "Stripe Connect onboarding useStripeConnect ConnectAccountManagement"
quick: "User model schema getMe provider stripeAccountId Prisma"
quick: "Google Calendar routes sync disconnect auth calendarSyncJob"
```

### Mid-task: about to touch the email system
```
quick: "email Resend templates transactional React Email service"
```

### Mid-task: found a price bug
```
quick: "price double-division cents euros formatPrice formatMoneyValue"
```

### Generic session start
```
recent: limit=15, k_neighbors=2
deep:   "project overview architecture current state WIP"
```

## How to interpret results

Each memory returned by `remember` has:
- **type**: episodic (specific event, dated), semantic (fact/architecture, stable), procedural (how-to, instructions)
- **tags**: thematic cluster (bug, gotcha, convention, reference, pattern, decision, state, wip...)
- **relevance score**: semantic proximity to query (>0.7 high, 0.4-0.7 medium, <0.4 low)
- **file_path**: if present, the file it refers to — verify it still exists before trusting it
- **age**: old episodic memories may be stale, semantic ones stay valid longer

### How to weigh memories by tag

| Tag | Priority | How to use |
|-----|----------|------------|
| **gotcha**, **bug** | High | Warnings from past experience. Read carefully before touching that area. |
| **convention**, **pattern** | High | Follow them unless current code explicitly contradicts them. |
| **reference** | Medium | Point to utilities/hooks/services. Verify they still exist before using. |
| **decision** | Medium | Contain the WHY. Respect the decision or discuss with user if you want to change it. |
| **state**, **wip** | Context | Inform about ongoing work. Most recent ones are most relevant. |

### Stale memory signals

- Memory says "file X uses pattern Y" but code shows otherwise → flag as potentially stale
- Old episodic memory (months) about an area that was rewritten → probably no longer relevant
- Memory with file_path that no longer exists → file was renamed or removed
