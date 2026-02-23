---
name: daily-briefing
description: "Generate morning briefing with today's schedule, critical approvals, high-priority tasks, inbox summary, and suggested focus blocks. The essential daily planning workflow."
---

# Daily Briefing Skill

Generate a comprehensive daily briefing to start the day with clarity and focus.

## Steps

1. **Fetch Calendar** — Use `fetch_calendar_events` with:
   - `start_date`: today's date (YYYY-MM-DD)
   - `end_date`: today's date
   - `calendar_id`: "primary"

   Extract: total meetings, time-blocked schedule, any conflicts

2. **Fetch Emails** — Use `fetch_emails` with:
   - `folder`: "INBOX"
   - `unread_only`: true
   - `max_count`: 50

   Count total unread emails

3. **Classify Emails** — For each email from step 2:
   - Use `classify_email_intent` to determine priority and category
   - Track: urgent count, action-required count, FYI count, spam count

4. **Extract Action Items** — For emails marked "action_required":
   - Use `extract_action_items` to parse tasks and deadlines
   - Create tasks using `create_task` for each extracted action
   - Track: total tasks created from emails

5. **Fetch High-Priority Tasks** — Use `fetch_tasks` with:
   - `priority`: "urgent" and "high"
   - `status`: "pending"

   Identify top 3 most urgent tasks

6. **Detect Critical Actions** — For any pending actions requiring approval:
   - Use `detect_critical_action` to flag items needing user decision
   - Use `create_approval_card` for each critical item
   - Track: total approvals needed

7. **Suggest Focus Blocks** — Use `suggest_focus_blocks` with:
   - `date`: today's date
   - `min_duration_minutes`: 90

   Identify best deep work slots based on calendar gaps

8. **System Health Check** (optional) — Use `get_system_metrics` with:
   - `metric_types`: "all"

   Check for any alerts or optimization needs

9. **Compile Briefing** — Generate structured output following the Daily Briefing Format from system prompt

## Output Format

Return a markdown-formatted briefing:

```
## OpenSentinel Daily Briefing — [Date]

### Critical Approvals (X items)
[Approval cards if any, otherwise "None pending"]

### Today's Schedule
[Time-blocked view of calendar events]
- 09:00-09:30: Team Standup
- 10:00-12:00: Deep Work Block (focus)
- 14:00-15:00: Client Meeting

### Top 3 Actions
1. [Task] — Priority: [H/M/L] | Deadline: [Date] | Est: [Time]
2. ...
3. ...

### Inbox Summary
- X unread emails
- Y urgent items
- Z converted to tasks
- A flagged as spam/FYI

### Device Health
[If alerts present, show recommendations; otherwise omit section]

### Suggested Focus
Recommended deep work block: [Time range]
Reasoning: [Why this is optimal]
```

## Quality Rules

- **Concise**: Max 2-minute read (400-500 words)
- **Actionable**: Every section has clear next steps
- **Prioritized**: Most critical items first
- **Time-aware**: Morning tone, forward-looking
- **Confidence scores**: Include for classifications if below 0.8
- **Provenance**: Cite sources (email IDs, calendar event IDs)

## Error Handling

- If calendar fetch fails → Continue with email triage only
- If email fetch fails → Continue with calendar and tasks only
- If both fail → Show tasks and suggest manual check
- Always complete the briefing with available data
