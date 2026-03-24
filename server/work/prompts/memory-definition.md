# Memory Definition — Work Projects

This is the canonical quality standard for all memories in MangoBrain Work projects.
Every agent that creates or updates memories MUST follow these rules.

---

## Hard constraints

### Length
**2-5 lines.** Below 2: too vague, won't match queries well. Above 5: you're compressing multiple facts — split them.

### Language
**English always.** Embedding models are optimized on English. The user communicates in their language, but memories are stored in English for retrieval quality.

### Granularity
**One fact = one memory.** The granularity test: if you remove a sentence from the memory, does it change the topic? If yes, it should be two memories.

**WRONG** (multiple facts compressed):
```
"Brand uses teal colors, targets musicians aged 22-35, posts 3x/week on Instagram, and the tone is casual but premium."
```

**RIGHT** (atomic):
```
Memory 1: "Visual identity: teal/cyan palette (#14b8a6, #06b6d4) on dark backgrounds. Sans-serif typography. Premium but accessible aesthetic."
Memory 2: "Primary audience: musicians aged 22-35 who play in bands and need rehearsal space. Price-sensitive but value quality."
Memory 3: "Instagram posting cadence: 3 posts/week (carousel or Reel). Best engagement on Tuesdays and Thursdays."
Memory 4: "Brand voice: casual but never sloppy. Premium but never elitist. Confident but never arrogant."
```

### Self-containedness
Readable without external context. Someone seeing only this memory should understand what it says.

**BAD:** "Changed to teal after the discussion."
**GOOD:** "Brand primary color changed from blue (#3B82F6) to teal (#14b8a6) — decision driven by competitor differentiation: most music platforms use blue/purple."

---

## Memory types

| Type | What it stores | Decay rate | Example |
|------|---------------|------------|---------|
| **Episodic** | Specific events, decisions, feedback with context | Fast (λ=0.01) | "User rejected formal Instagram caption on 2026-03-22. Reason: 'sounds like a corporate press release, not us.'" |
| **Semantic** | General facts, rules, brand knowledge | Slow (λ=0.002) | "Brand positioning: for independent musicians who need affordable, quality rehearsal space. Differentiator: instant booking without owner approval." |
| **Procedural** | How-to knowledge, processes, format rules | Very slow (λ=0.001) | "Instagram carousel best practice: 3-5 slides. Slide 1: bold question or hook. Last slide: clear CTA. Consistent visual style across all slides." |

### When to use which

- **User made a decision** → episodic (include date, context, reasoning)
- **A brand rule is established** → semantic (the rule itself, no date needed)
- **A process is defined** → procedural (step-by-step, when to use it)
- **User gave feedback** → episodic (what they said, what triggered it)
- **A pattern emerged from multiple feedbacks** → semantic (the abstracted rule)

---

## Tags

**3-6 tags per memory.** Lowercase, hyphenated for multi-word.

Always include:
- **Area tag**: brand, audience, tone, channel, strategy, product, content, feedback
- **Specificity tag**: instagram, email, carousel, pitch-deck, competitor, budget

Common tags for Work projects:
```
brand, identity, visual-identity, colors, logo, values, positioning
audience, persona, pain-point, customer-journey, segment
tone, voice, language, do, dont
channel, instagram, linkedin, tiktok, email, blog, website
strategy, goals, kpi, metrics, competition, budget
content, copy, carousel, reel, story, post, newsletter
feedback, correction, preference, approval, rejection
campaign, launch, editorial, calendar
idea, wip, decision
```

---

## Relations

Edges in the knowledge graph. They make retrieval associative — a query about "tone" also surfaces related audience and brand memories.

### Format
```python
relations=[{
    "target_query": "brand visual identity teal colors palette",  # semantic search string
    "relation_type": "relates_to",
    "weight": 0.7
}]
```

### Relation types

| Type | Meaning | Example |
|------|---------|---------|
| `relates_to` | Topically connected | Instagram tone ↔ brand personality |
| `depends_on` | B needed to understand A | Carousel format spec → brand visual identity |
| `caused_by` | A exists because of B | "Short copy preferred" ← user feedback March 2026 |
| `co_occurs` | Always relevant together | Instagram rules ↔ Instagram hashtag strategy |
| `contradicts` | Tension between A and B | "Casual tone" ↔ "Professional LinkedIn presence" |
| `supersedes` | A replaces B (newer/better) | New tone guide → old tone guide |

### Weight guide
- **0.7-1.0**: Tight connection (same topic, direct dependency)
- **0.4-0.6**: Clear but looser connection (same area, different aspect)
- **0.2-0.4**: Loose association (different areas but related context)

---

## file_path

**MANDATORY for any memory that refers to a document, rule file, or deliverable.** Relative to project root.

This enables `sync_codebase()`: when a file changes, memories linked to it get flagged as potentially stale.

### What counts as a file_path in Work

| Memory about... | file_path |
|---|---|
| Brand rule (from rules) | `.claude/rules/brand.md` |
| Tone guideline (from rules) | `.claude/rules/tone.md` |
| Audience persona (from rules) | `.claude/rules/audience.md` |
| Channel spec (from rules) | `.claude/rules/channels.md` |
| Strategy/goals (from rules) | `.claude/rules/strategy.md` |
| Product info (from rules) | `.claude/rules/product.md` |
| Editorial plan | `docs/editorial-plan-q2.xlsx` |
| Brand guidelines doc | `docs/brand-guidelines.pdf` |
| Produced deliverable | `deliverables/pitch-deck-v2.pptx` |
| Campaign document | `docs/campaign-spring-2026.md` |

**When NOT to set file_path:**
- Pure feedback memories (user correction, not tied to a file)
- Ideas and WIP (no source file)
- Cross-project memories pulled from Code memory

---

## content_signature

**Encouraged for rule-based and document-based memories.** ~30 tokens. A structured fingerprint of what the memory references — makes sync detection precise.

### Format: `{type}: {key} = {value summary}`

```python
# Brand visual identity
content_signature="brand: palette = teal #14b8a6, cyan #06b6d4, dark bg #0a0a0a"

# Tone rule
content_signature="tone: instagram = casual, direct, max 50 words, no formal language"

# Audience persona
content_signature="persona: primary = musicians 22-35, bands, price-sensitive, urban"

# Channel spec
content_signature="channel: instagram = 3x/week, carousel+reel, stories daily"

# Strategy goal
content_signature="goal: Q2-2026 = 1000 followers, 3% engagement, launch campaign"

# Deliverable
content_signature="deliverable: pitch-v2 = 12 slides, investor focus, approved 2026-03-22"

# Budget
content_signature="budget: marketing-Q2 = €500/month, 60% ads 40% content"

# Competitor
content_signature="competitor: studiobook = booking platform, monthly subscription model, no instant booking"
```

### How sync uses content_signature

When `sync_codebase` detects a changed file:
1. Finds all memories with `file_path` pointing to that file
2. Compares `content_signature` against new file content
3. If the signature no longer matches → memory flagged as stale
4. Mem-manager reviews: update, supersede, or deprecate

**Example:**
```
brand.md changes palette from teal to purple
→ Memory with content_signature="brand: palette = teal #14b8a6..." is stale
→ Mem-manager creates new memory with updated signature
→ Adds supersedes relation to old memory
```

---

## Quality checklist (every memory)

- [ ] English, 2-5 lines
- [ ] One fact per memory
- [ ] Self-contained (readable without context)
- [ ] Dense (no filler words)
- [ ] Type correct (episodic / semantic / procedural)
- [ ] Project set
- [ ] Tags: 3-6, lowercase, consistent
- [ ] Relations: ≥1 if related to known topic
- [ ] file_path: set if memory refers to a document or rule file
- [ ] content_signature: set if memory describes a rule, spec, or deliverable
- [ ] Not a duplicate

---

## What NOT to memorize

- Content that was produced (the file exists, don't duplicate it)
- Information already in .claude/rules/ files **unless** the memory adds context the rule doesn't have (reasoning behind a rule, feedback that led to it)
- Vague aspirations ("we want to be the best brand")
- Ephemeral data that changes daily (follower count, trending hashtags)
- Raw conversation without insight
- Intermediate drafts and iterations
