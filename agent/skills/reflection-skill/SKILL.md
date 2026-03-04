---
name: reflection-skill
description: Automatic post-interaction self-reflection that evaluates quality, detects user patterns, and persists learnings to memory
---

# Reflection Skill

## Purpose

After every interaction, OpenSentinel performs a lightweight self-reflection to evaluate quality, detect user patterns, and persist useful context to memory.

Reflection affects memory and future behavior only.
Reflection must NEVER be shown to the user unless explicitly requested.
Reflection must NEVER delay or block the user-facing response.

This skill runs AFTER the final response has been delivered.

---

## Trigger

Automatic, after every completed user interaction.

If the interaction was trivial (greeting, single acknowledgment, clarification-only),
skip to a minimal reflection: log task type and completion status only.

---

## Execution Flow

### Step 1: Gather Interaction Context

Collect from the current conversation:

- User's original request
- Task type (research, coding, writing, analysis, conversation, other)
- Tools and skills invoked
- Subagents delegated to
- Files created or modified
- Task completion status (complete, partial, failed, ongoing)
- Any errors or retries that occurred

---

### Step 2: Evaluate Quality

Rate the interaction on these dimensions (1-5 scale):

| Dimension | Question |
|-----------|----------|
| Understanding | Did I correctly interpret user intent? |
| Accuracy | Was information correct and well-sourced? |
| Completeness | Did I address all parts of the request? |
| Efficiency | Did I use optimal tools and steps? |
| Focus | Did I stay on task without scope creep? |
| User Experience | Was response format and tone appropriate? |

For any dimension scored 3 or below:
- Identify the root cause.
- Note a specific corrective action.

---

### Step 3: Detect Patterns

Compare the current interaction against existing patterns in
`/memories/reflection/patterns_learned.md` (if it exists).

Look for:
- Request type frequency (e.g., user asks research questions often)
- Topic clusters (e.g., recurring interest in finance, AI, health)
- Format preferences (bullets vs paragraphs, tables vs prose)
- Tool usage patterns (which tools needed most)
- Feedback signals (positive or negative, explicit or implicit)

Classify each pattern as:
- NEW: not previously recorded
- REINFORCED: matches an existing pattern
- CHANGED: contradicts or evolves an existing pattern

---

### Step 4: Update Memory

Write to persistent memory only when meaningful new information is found.
Do not write empty or redundant updates.

Before writing, read the target file to avoid duplicating existing content.

| Condition | Target File | Mode |
|-----------|-------------|------|
| New user preference discovered | `/memories/user_prefs.txt` | append |
| New behavioral instruction | `/memories/instructions.txt` | overwrite |
| Explicit user feedback received | `/memories/feedback.log` | append |
| New or reinforced pattern | `/memories/reflection/patterns_learned.md` | append |
| Improvement action taken | `/memories/reflection/improvements_made.md` | append |
| Active project context changed | `/memories/context/active_projects.md` | overwrite |
| Communication style note | `/memories/context/communication_style.md` | overwrite |

---

### Step 5: Write Session Log

Create or update the daily session log:

File: `/memories/reflection/session_{YYYY-MM-DD}.md`

Structure:

```
## Reflection - {DATE}

### Summary
- Request: {brief description}
- Type: {task type}
- Status: {completion status}

### Quality (1-5)
- Understanding: {score}
- Accuracy: {score}
- Completeness: {score}
- Efficiency: {score}
- Focus: {score}
- UX: {score}

### Patterns
- {pattern type}: {description}

### Memory Updates
- {action}: {file} - {what changed}

### Improvements Needed
- {specific corrective action}
```

If multiple interactions occur on the same day, append to the existing file
with a separator line.

---

### Step 6: Generate Improvement Actions

For each dimension scored 3 or below:

1. State the issue concisely.
2. Identify root cause.
3. Propose a specific fix.
4. Classify effort: low, medium, high.

For recurring patterns (3+ occurrences):
- Consider whether a new skill should be created.
- Consider whether an existing skill needs updating.

Record actionable improvements in `/memories/reflection/improvements_made.md`.

---

## Privacy and Safety Rules

Permitted to log:
- Task types and tool usage patterns
- Format and tone preferences
- Explicit user feedback
- Interaction quality scores

Never log:
- Passwords, API keys, or credentials
- Sensitive personal information (health details, financial amounts, legal matters)
- Verbatim conversation content
- Data that could identify third parties

If the interaction involved sensitive topics:
- Use generic descriptions only (e.g., "financial query" not specific amounts).
- Mark the session log entry as "privacy-protected".
- Do not persist sensitive details to `/kb/` or any shareable location.

---

## Critical Constraints

- Reflection is internal. Never surface reflection output in user-facing responses
  unless the user explicitly asks for it.
- Never fabricate quality scores. If you cannot assess a dimension, mark it N/A.
- Never create memory files with placeholder or template content.
  Only write when there is real data to persist.
- Keep reflection lightweight. Skip verbose logging for trivial interactions.
- Read existing memory files before writing to avoid duplication.

---

## Priority Order

Response delivery to user (always first)
> Accuracy of reflection
> Pattern detection
> Memory persistence
> Improvement suggestions

Reflection must never compromise response speed or quality.

---

End of Skill.
