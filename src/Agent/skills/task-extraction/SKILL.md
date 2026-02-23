---
name: task-extraction
description: "Convert emails, meeting notes, or documents into actionable tasks with deadlines, effort estimates, and scheduling recommendations."
---

# Task Extraction Skill

Transform unstructured content into organized, schedulable tasks.

## Steps

1. **Accept Input** — Receive content from:
   - Email body and subject
   - Meeting notes
   - Document text
   - User-pasted text

2. **Extract Action Items** — Use `extract_action_items` with:
   - `email_id`: source identifier (or "manual_input")
   - `content`: full text

   Parse for:
   - Tasks and deliverables
   - Deadlines (explicit and implicit)
   - Commitments and promises
   - Follow-up actions

3. **Enrich Each Action** — For each extracted item:
   - **Estimate Effort**: Categorize as 5min | 30min | 1hr | 2hr | 4hr+
   - **Assign Priority**: Based on deadline proximity and keywords (urgent/ASAP → high)
   - **Extract Deadline**: Parse dates in various formats
   - **Identify Dependencies**: Flag if task depends on others

4. **Create Tasks** — For each enriched action:
   - Use `create_task` with:
     - `title`: clear, actionable description
     - `priority`: derived priority
     - `deadline`: extracted or inferred deadline
     - `effort_estimate`: from step 3
     - `source`: input source identifier

5. **Suggest Scheduling** — Use `suggest_task_schedule` with:
   - `task_ids`: all created tasks
   - `date_range`: from today to furthest deadline

   Get recommended timeslots for each task

6. **Generate Summary** — Compile extraction results

## Output Format

Return JSON summary with created tasks:

```json
{
  "extraction_summary": {
    "source": "email_005 | meeting_notes | manual",
    "total_actions_found": 5,
    "tasks_created": 5,
    "timestamp": "2026-02-21T10:00:00"
  },
  "created_tasks": [
    {
      "task_id": "task_20260221100015",
      "title": "Review budget proposal",
      "priority": "high",
      "deadline": "2026-02-25",
      "effort_estimate": "30min",
      "source": "email_001"
    },
    ...
  ],
  "scheduling_recommendations": [
    {
      "task_id": "task_20260221100015",
      "suggested_slot": "2026-02-23T10:00:00 - 10:30:00",
      "reasoning": "Morning slot before deadline"
    },
    ...
  ],
  "confidence_scores": {
    "extraction_confidence": 0.88,
    "deadline_accuracy": 0.92
  }
}
```

## Quality Rules

- **Actionable language**: Use verbs (review, prepare, send, update)
- **Specific titles**: Include key context (not just "Follow up")
- **Realistic estimates**: Bias toward longer (humans underestimate)
- **Buffer for deadlines**: Suggest completion 1 day before actual deadline
- **Flag ambiguity**: If confidence < 0.7, note for user clarification

## Error Handling

- If no actions found → Return empty list, suggest manual review
- If deadline parsing fails → Create task without deadline, flag for user
- If effort estimate unclear → Default to "unknown", ask user
