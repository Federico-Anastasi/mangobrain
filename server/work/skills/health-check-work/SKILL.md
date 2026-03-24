---
name: health-check-work
description: "Monthly memory health diagnosis for work projects. Identifies structural issues, content gaps, and stale memories. Prescribes targeted fixes."
user-invocable: true
---

# /health-check-work — Memory Health Diagnosis

You are a memory health specialist. Your job is to diagnose problems in the project's memory and prescribe fixes.

Run this **monthly** or when retrieval quality seems off.

---

## PHASE 1 — DIAGNOSE

```
diagnose(project="{PROJECT}")
```

Returns:
- Health score (0-100)
- Structural metrics (memory count, edge count, avg edges, isolated count)
- Prescriptions (specific issues to fix)

---

## PHASE 2 — CONTENT GAP ANALYSIS

For a work project, check coverage across the 5 brand pillars:

### Run verification queries

```
remember(query="brand identity mission values positioning", mode="quick", project="{PROJECT}")
remember(query="audience persona demographics needs pain points", mode="quick", project="{PROJECT}")
remember(query="tone voice language do dont brand personality", mode="quick", project="{PROJECT}")
remember(query="channel format frequency posting rules hashtags", mode="quick", project="{PROJECT}")
remember(query="goals strategy metrics KPI campaign competition", mode="quick", project="{PROJECT}")
```

### Score each pillar

| Pillar | Memories found | Status |
|--------|---------------|--------|
| Brand & Identity | {n} | STRONG (10+) / ADEQUATE (5-9) / WEAK (1-4) / MISSING (0) |
| Audience & Personas | {n} | ... |
| Voice & Tone | {n} | ... |
| Channels & Formats | {n} | ... |
| Goals & Strategy | {n} | ... |

### Additional checks

```
remember(query="feedback correction preference user", mode="quick", project="{PROJECT}")
```
→ How much user feedback is captured? This is the most valuable memory type for content quality.

```
remember(query="campaign content approved delivered", mode="quick", project="{PROJECT}")
```
→ Is past work being remembered? Content decisions should persist.

---

## PHASE 3 — PRESCRIBE & EXECUTE

Present findings to user and recommend actions in priority order:

### Priority 1: Fill content gaps (WEAK/MISSING pillars)
```
Recommendation: Run /brain-init-work for Phase {n} to fill the {pillar} gap.
Or: Tell me about your {pillar} now and I'll memorize it.
```

### Priority 2: Build graph connections (low avg edges)
```
Recommendation: Run /elaborate-work to build connections between memories.
Target: avg 3+ edges per memory.
```

### Priority 3: Consolidate feedback (many episodic, few semantic)
```
Recommendation: Run /elaborate-work with focus on feedback consolidation.
You have {n} individual feedback memories that could become {n/3} pattern rules.
```

### Priority 4: Clean stale memories (old episodic with no edges)
```
Recommendation: {n} memories are older than 60 days with 0-1 edges.
Review and deprecate if no longer relevant.
```

### Priority 5: Resolve contradictions
```
Recommendation: Found {n} potential contradictions. Review:
- Memory A says "..."
- Memory B says "..."
→ Are both valid (context-dependent)? Add a 'contradicts' edge.
→ Is one outdated? Supersede it.
```

---

## PHASE 4 — VERIFY

If the user chose to execute any fixes:

```
diagnose(project="{PROJECT}")
```

Show before/after comparison:
```
Health check results:
                    Before    After
Health score:       {n}       {n}
Total memories:     {n}       {n}
Avg edges:          {n}       {n}
Isolated memories:  {n}       {n}
Content gaps:       {n}       {n}

Pillar coverage:
  Brand:     {status} → {status}
  Audience:  {status} → {status}
  Voice:     {status} → {status}
  Channels:  {status} → {status}
  Goals:     {status} → {status}

Next health check recommended: {date — 1 month from now}
```

---

## RULES

- **Don't auto-fix everything.** Present the diagnosis, let the user choose what to address
- **Content gaps > structure issues.** Missing brand pillars matter more than low edge counts
- **Feedback density is a health signal.** A project with 100 brand memories but 0 feedback memories will produce generic content. Flag this
- **Goals/strategy memories decay fast.** Quarterly goals from 6 months ago are probably stale. Flag for review
- **Health score thresholds:** >80% healthy, 60-80% needs attention, <60% needs significant work
