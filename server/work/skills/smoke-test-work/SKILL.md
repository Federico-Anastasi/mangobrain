---
name: smoke-test-work
description: "Tests memory retrieval quality for work projects with brand, audience, and content queries. Run after initialization or elaboration to verify memory coverage."
user-invocable: true
---

# /smoke-test-work — Retrieval Quality Test

You test whether the memory system returns useful results for typical work queries. This catches gaps before they affect content quality.

Run after `/brain-init-work` or `/elaborate-work`.

---

## STEP 1 — GET BASELINE

```
stats(project="{PROJECT}")
```

Note: total memories, total edges, avg edges per memory.

---

## STEP 2 — DESIGN TEST QUERIES

Create 15-20 queries across 6 categories. These simulate real questions that would come up during /brief or /create:

### Category 1: Brand Identity (3-4 queries)
Queries a Researcher would make when starting any content task:
```
"brand identity values mission positioning tagline"
"visual identity colors palette fonts logo usage"
"brand personality traits voice character"
```

### Category 2: Audience & Personas (3-4 queries)
Queries for understanding who the content is for:
```
"target audience primary persona demographics needs"
"audience pain points problems frustrations"
"customer language style how they speak preferences"
```

### Category 3: Tone & Voice (3-4 queries)
Queries for applying the right communication style:
```
"tone voice guidelines formal casual brand personality"
"language rules do dont words phrases avoid"
"Instagram tone channel specific voice adaptation"
"LinkedIn tone professional channel guidelines"
```

### Category 4: Content & Channels (3-4 queries)
Queries for format and channel rules:
```
"Instagram format carousel Reel stories specs dimensions"
"posting frequency schedule editorial calendar rhythm"
"hashtag strategy tags content distribution"
"email newsletter format template tone"
```

### Category 5: Strategy & Goals (2-3 queries)
Queries for aligning content with business objectives:
```
"marketing goals KPI metrics current targets"
"campaign active planned launch timeline"
"competitor positioning differentiation market"
```

### Category 6: Feedback & Patterns (2-3 queries)
Queries for recalling user preferences and past corrections:
```
"user feedback correction preference content style"
"content approved worked well engagement"
"content rejected problems issues avoided"
```

**Adapt queries to the project.** Replace generic terms with actual brand names, channel names, and persona names from the project.

---

## STEP 3 — EXECUTE QUERIES

For each query:
```
remember(query="{query}", mode="quick", project="{PROJECT}")
```

---

## STEP 4 — EVALUATE

Score each result:

| Score | Meaning | Criteria |
|-------|---------|----------|
| **RELEVANT** (2 pts) | Memory directly answers the query | Contains the specific information sought |
| **PARTIAL** (1 pt) | Memory is related but doesn't fully answer | Adjacent topic, incomplete info |
| **MISS** (0 pts) | Memory is irrelevant or no results | Wrong topic, too generic, empty |

### Per-query evaluation

For each query, check:
1. Did at least 1 RELEVANT result come back?
2. Are the top 3 results useful?
3. Is there noise (irrelevant results in top positions)?

### Per-category scoring

```
Category score = sum(points) / (queries × max_results × 2) × 100
```

---

## STEP 5 — REPORT

```
Smoke Test Results — {PROJECT}
================================

Overall score: {total}% ({PASS >80% | PARTIAL 60-80% | FAIL <60%})

Category breakdown:
  Brand Identity:      {score}% {PASS|PARTIAL|FAIL}
  Audience & Personas: {score}% {PASS|PARTIAL|FAIL}
  Tone & Voice:        {score}% {PASS|PARTIAL|FAIL}
  Content & Channels:  {score}% {PASS|PARTIAL|FAIL}
  Strategy & Goals:    {score}% {PASS|PARTIAL|FAIL}
  Feedback & Patterns: {score}% {PASS|PARTIAL|FAIL}

Strong areas:
  - {category}: {why it works well}

Weak areas:
  - {category}: {what's missing, specific gaps}

Recommendations:
  - {if Brand low}: Run /brain-init-work Phase 1
  - {if Audience low}: Run /brain-init-work Phase 2
  - {if Tone low}: Run /brain-init-work Phase 3
  - {if Channels low}: Run /brain-init-work Phase 4
  - {if Goals low}: Run /brain-init-work Phase 5
  - {if Feedback low}: Use the product more — feedback memories accumulate naturally through /create and /memorize-work
  - {if graph sparse}: Run /elaborate-work to build connections

Baseline metrics:
  Total memories: {n}
  Total edges: {n}
  Avg edges/memory: {n}
```

---

## RULES

- **Adapt queries to the project.** "Instagram carousel format" is better than "social media format" if the project uses Instagram. Use actual brand names, channel names, persona names
- **Don't game the test.** Design queries that a real Researcher agent would make, not queries optimized to match existing memory content
- **Feedback category is expected to be low on new projects.** This is normal — it builds up over time through /create sessions. Don't flag it as critical on a fresh init
- **Score honestly.** A PARTIAL is not a RELEVANT. If the memory talks about "brand colors" but the query was about "audience demographics," that's a MISS, not a PARTIAL
- **Run this after every major memory operation** (init, elaborate, large batch of sessions) to track quality over time
