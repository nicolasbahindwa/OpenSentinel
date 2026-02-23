---
name: email-triage
description: "Process inbox to actionable tasks. Classify emails by urgency and category, extract action items, create tasks, and flag spam. Inbox zero workflow."
---

# Email Triage Skill

Convert inbox chaos into organized action items.

## Steps

1. **Fetch Unread Emails** — Use `fetch_emails` with:
   - `folder`: "INBOX"
   - `unread_only`: true
   - `max_count`: 50 (configurable)

2. **Classify Each Email** — For each email fetched:
   - Use `classify_email_intent` with email content
   - Parse classification results:
     - `category`: action_required | fyi | spam
     - `priority`: urgent | high | routine
     - `spam_probability`: 0.0-1.0
     - `sentiment`: positive | neutral | negative

3. **Route by Classification**:

   **A. If spam_probability > 0.7:**
   - Flag email as spam
   - Do NOT process further
   - Increment spam counter

   **B. If priority == "urgent":**
   - Use `extract_action_items` immediately
   - Use `detect_critical_action` to check if requires approval
   - If critical → use `create_approval_card`
   - Increment urgent counter

   **C. If category == "action_required":**
   - Use `extract_action_items` to parse tasks
   - For each extracted task:
     - Use `create_task` with:
       - `title`: task description
       - `priority`: from email classification
       - `deadline`: extracted deadline
       - `effort_estimate`: extracted or inferred
       - `source`: email ID
   - Increment action counter

   **D. If category == "fyi":**
   - Mark as processed (read-only action)
   - Increment FYI counter

4. **Generate Triage Summary** — Compile statistics and results

## Output Format

Return JSON summary:

```json
{
  "triage_session": {
    "processed_count": 47,
    "timestamp": "2026-02-21T09:00:00"
  },
  "classification_summary": {
    "spam_flagged": 8,
    "urgent": 3,
    "action_required": 12,
    "fyi": 24
  },
  "tasks_created": 15,
  "critical_approvals": 1,
  "urgent_items": [
    {
      "email_id": "email_003",
      "subject": "URGENT: Client presentation today at 3pm",
      "action": "Prepare slides",
      "deadline": "2026-02-21T15:00:00"
    }
  ],
  "confidence_scores": {
    "average": 0.85,
    "low_confidence_count": 2
  }
}
```

## Quality Rules

- **Accuracy over speed**: If confidence < 0.7, flag for user review
- **Never auto-send**: Email responses require approval workflow
- **Extract ALL deadlines**: Don't miss time-sensitive commitments
- **Flag financial/legal language**: Automatic escalation to critical
- **Preserve context**: Link tasks to source email IDs

## Error Handling

- If `fetch_emails` fails → Return error, suggest manual check
- If single classification fails → Skip email, log error, continue
- If `extract_action_items` fails → Create generic task for manual review
- Log all errors to audit trail with `log_action`
