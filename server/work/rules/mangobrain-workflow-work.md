# MangoBrain Work — Workflow

MangoBrain provides persistent memory across sessions. This rule describes how to use it in daily workflow.

## Principle

Memory is not a file to consult. It's an active system: ask for what you need, when you need it. It contains brand decisions, user feedback, target insights, content patterns, past mistakes — knowledge that documents alone don't transmit.

## Query Language

**All remember() queries MUST use English keywords**, regardless of session language.
Memories are stored in English — queries in other languages degrade retrieval by ~15-20%. The conversation stays in the user's language, but queries go to the DB in English.

## Integration with /brief

**INTAKE**: remember recent + deep + quick → full context before asking questions
**CLARIFICATION**: use context to NOT ask things you already know
**MATERIAL EXPLORATION**: search documents AND memory
**BRIEF**: the brief is informed by project history

## Integration with /create

**RESEARCH**: the Researcher pulls from memory for brand, tone, audience, past content
**CREATION**: the Creator receives pre-digested context (does not query)
**REVIEW**: the Reviewer compares against past decisions and historical feedback
**CLOSE**: the Mem-manager saves new decisions, feedback, patterns

## Free sessions

For sessions without /create (brainstorm, analysis, strategy):
- Use `remember` during the session
- At end of session: `/memorize-work`

## What to memorize and what not to

### YES — produces reusable knowledge
- Brand decision ("we use teal as primary color")
- User feedback ("the tone was too formal, prefers casual")
- Target insight ("musicians under 25 prefer Reels over static posts")
- Content pattern ("carousels with a question in the title perform better")
- Strategic choice ("for launch we focus on Instagram + TikTok, no LinkedIn")
- Mistake not to repeat ("the last CTA was too aggressive")

### NO — not worth memorizing
- Discarded drafts and intermediate iterations
- Information already in rule files (those are auto-loaded every session)
- Generic facts not specific to the project
- Content already produced (the file exists, no need to duplicate it in memory)
