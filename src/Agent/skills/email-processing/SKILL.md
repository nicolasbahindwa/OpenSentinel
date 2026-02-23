---
name: email-processing
description: "Process emails end-to-end. Classifies incoming email by category, priority, and sentiment, then routes to compose an appropriate response — urgent, standard professional, or spam flag."
---

# Email Processing Skill

Process an incoming email: classify it, determine the right response strategy,
and draft an appropriate reply.

## Steps

1. **Classify** — Use `classify_email` with `classification_type: "category"`
   to determine:
   - Category (Sales, Support, General)
   - Priority (urgent, important, routine)
   - Sentiment (Positive, Neutral, Negative)
   - Spam probability

2. **Route** — Based on classification results, choose one path:
   - **Spam**: If `spam_probability > 0.7` → flag as spam, do NOT compose a
     response.
   - **Urgent**: If `priority == "urgent"` → compose an urgent response.
   - **Standard**: All other cases → compose a standard professional response.

3. **Compose Response** (skip if spam):
   - **Urgent path**: Use `compose_email` with:
     - `message_type: "urgent"`
     - `subject: "RE: {category} — Urgent Response"`
   - **Standard path**: Use `compose_email` with:
     - `message_type: "followup"` if category is `"Support"`,
       otherwise `"professional"`
     - `subject: "RE: {category} Inquiry"`

## Output Format

Return a JSON object:

```json
{
  "classification": {
    "category": "...",
    "priority": "...",
    "sentiment": "...",
    "spam_probability": 0.02
  },
  "action": "urgent_response | standard_response | flagged_as_spam",
  "drafted_response": { ... },
  "note": "only present if flagged as spam"
}
```

## Quality Rules

- Always classify before composing — never skip classification.
- Never respond to spam — only flag it.
- Match response urgency to email priority.
- For Support category emails, always use follow-up tone.
- Include the full classification in the output regardless of route taken.
