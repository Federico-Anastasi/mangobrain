# MangoBrain Work — Query Strategy

You have access to the `remember` MCP tool to retrieve information from the project.
Use it often. Memory contains brand decisions, feedback, patterns, target insights, and references that documents alone don't communicate.

## When to use remember

- **Session start**: recent context + project overview
- **Before creating content**: query brand, tone, audience for that channel
- **When the user asks something new**: check for past decisions
- **When the user gives feedback**: check if it's a pattern (have they said the same thing before?)
- **End of session**: `remember(mode="recent")` to confirm what to save

## Multi-query strategy (session start)

### 1. Recent — where we left off
```
remember(mode="recent", project="{PROJECT}", limit=10, k_neighbors=2)
```

### 2. Deep — broad context on the topic
```
remember(query="[5-10 keywords from the requested topic]", mode="deep", project="{PROJECT}")
```

### 3. Quick — specific areas
```
remember(query="[brand tone voice guidelines]", mode="quick", project="{PROJECT}")
remember(query="[Instagram format carousel content rules]", mode="quick", project="{PROJECT}")
```

## Query Language

**All remember() queries MUST use English keywords**, regardless of session language.
Memories are stored in English — queries in other languages degrade retrieval by ~15-20%.

```
GOOD: remember(query="Instagram post engagement CTA caption", ...)
BAD:  remember(query="post Instagram coinvolgimento didascalia", ...)
```

Always translate concepts before querying. The conversation stays in the user's language, but queries go to the DB in English.

## How to formulate queries

### Keywords > natural language
```
GOOD: "Instagram carousel CTA engagement caption hashtags"
BAD:  "how should I write Instagram posts"
```

### Domain proper names
```
GOOD: "target musician band rehearsal studio booking"
BAD:  "our target audience"
```

### Mix area + specific
```
GOOD: "competitor pricing studio booking platform market"
BAD:  "competitive analysis"
```

## Cross-project (if available)

If the project has an associated Code memory, you can pull product information:
```
remember(query="feature booking user flow value proposition", project="{CODE_PROJECT}", mode="quick")
```

**RULE**: always translate to non-technical language before using or showing this information to the user.

## Quick vs Deep vs Recent

| Mode | Results | When |
|------|---------|------|
| deep | ~20 | Session start, strategy, broad analysis |
| quick | ~6 | Mid-session, specific area, quick lookup |
| recent | ~15 | Session start, understand WIP and state |
