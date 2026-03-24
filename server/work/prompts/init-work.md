# Brain Init — Work Mode: Reference Guide

This document supplements `/brain-init-work` with detailed extraction guidelines for each phase.

---

## Extraction principles (all phases)

### Granularity
One fact = one memory. The granularity test: if you remove a sentence from the memory, does it change the topic? If yes, split.

**WRONG** (multiple facts compressed):
```
"Reverbia targets musicians aged 22-35, uses teal colors, posts 3x/week on Instagram, and Pablo handles business."
```

**RIGHT** (atomic):
```
Memory 1: "Reverbia primary audience: musicians aged 22-35 who play in bands and need rehearsal space. Price-sensitive but value quality over bargain."
Memory 2: "Reverbia visual identity: teal/cyan palette (#14b8a6, #06b6d4) on dark backgrounds. Sans-serif typography. Premium but accessible aesthetic."
Memory 3: "Reverbia Instagram posting cadence: 3 posts/week (carousel or Reel) plus daily stories. Best engagement on Tuesdays and Thursdays."
Memory 4: "Pablo (co-founder) handles business development and studio owner acquisition. Federico handles all technical development."
```

### Volume calibration

| Input | Expected memories |
|-------|-------------------|
| Verbal answers only (no docs) | 15-20 per phase |
| Verbal + 1 brand document | 20-30 per phase |
| Comprehensive brand kit + docs | 25-40 per phase |

### Relation strategy

Every memory should have 1-3 relations. Use these patterns:

| Scenario | Relation type | Weight |
|----------|--------------|--------|
| Persona ↔ pain point | relates_to | 0.7 |
| Brand value ↔ tone rule | caused_by | 0.6 |
| Channel ↔ format spec | depends_on | 0.8 |
| Do rule ↔ don't rule (same topic) | co_occurs | 0.7 |
| Old decision → new decision | supersedes | 0.9 |
| Two channel rules (different channels) | relates_to | 0.5 |

Use `target_query` with specific keywords for fuzzy matching:
```
relations=[{
  target_query: "Reverbia visual identity teal colors palette",
  relation_type: "relates_to",
  weight: 0.7
}]
```

### What NOT to extract

- Vague aspirations without substance ("we want to be the best")
- Information that will change within days (today's follower count)
- Duplicate of what another phase will cover
- Raw data without interpretation (a full spreadsheet dump)

### Quality checklist (every memory)

- [ ] English, 2-5 lines
- [ ] One fact per memory
- [ ] Self-contained (readable without context)
- [ ] Dense (no filler words)
- [ ] Type correct: semantic (fact/rule), episodic (event/decision), procedural (how-to)
- [ ] Tags: 3-6, lowercase, consistent across project
- [ ] Relations: ≥1, using target_query for fuzzy match
- [ ] Not a duplicate of existing memory

---

## Phase-specific extraction guides

### Phase 1: Brand & Identity

**Semantic memories (most common):**
- Project name, tagline, mission statement
- Visual identity elements (each element = separate memory)
- Brand values and personality traits
- Competitive positioning
- Founding story (if relevant to brand narrative)

**Procedural memories:**
- Logo usage rules
- Color application rules (primary, secondary, accent)
- Brand naming conventions

**Key tags:** brand, identity, positioning, visual-identity, colors, logo, values, mission

### Phase 2: Audience & Personas

**Semantic memories:**
- Each persona (demographics, needs, behavior)
- Pain points (one per memory if distinct)
- Audience segments and their differences
- Market size/opportunity notes

**Episodic memories:**
- Customer feedback or quotes that reveal needs
- Market research findings with dates

**Key tags:** audience, persona, [persona-name], pain-point, market, segment

### Phase 3: Voice & Tone

**Procedural memories (most common):**
- Language rules (do/don't lists — separate memories for do and don't)
- Channel-specific tone variations
- Audience-specific language adaptations

**Semantic memories:**
- Brand personality definition
- Communication style description
- Reference examples (content the brand liked/disliked)

**Key tags:** tone, voice, language, do, dont, brand-personality, [channel]-tone

### Phase 4: Channels & Formats

**Procedural memories (most common):**
- Per-channel format specs (dimensions, length, structure)
- Posting cadence per channel
- Hashtag strategy
- Cross-posting rules
- Content creation workflows

**Semantic memories:**
- Channel priorities (which is primary, secondary)
- Tools used and their roles
- Template library location

**Key tags:** channel, [channel-name], format, frequency, hashtags, tools, workflow

### Phase 5: Goals & Strategy

**Episodic memories:**
- Current goals with dates and metrics
- Active campaigns with timelines
- Performance benchmarks (dated)
- Strategic decisions (with reasoning)

**Semantic memories:**
- Competitive landscape
- Positioning strategy
- Budget constraints

**Procedural memories:**
- Measurement frameworks (what to track, where, how often)

**Key tags:** goals, strategy, metrics, campaign, competition, budget, KPI, [quarter/year]
