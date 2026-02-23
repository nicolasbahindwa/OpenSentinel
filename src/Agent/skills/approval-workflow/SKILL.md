---
name: approval-workflow
description: "Critical action consent system. Detect actions requiring approval, generate approval cards, log decisions, and execute only after user confirmation."
---

# Approval Workflow Skill

Ensure safe, transparent automation with user control over critical actions.

## Steps

1. **Detect Critical Action** — Use `detect_critical_action` with:
   - `action_type`: Type of action being proposed
   - `context`: Action details and parameters
   - `risk_profile`: User's risk tolerance setting

   Determine:
   - Is this action critical? (requires approval)
   - Severity level (low | medium | high | critical)
   - Reason why approval needed

2. **Generate Approval Card** — Use `create_approval_card` with:
   - `action`: Clear description of what will happen
   - `reason`: Agent's reasoning for recommending this
   - `alternatives`: Other options available

   Create user-facing approval prompt with:
   - **What**: Action description
   - **Why**: Agent reasoning
   - **Risk**: Potential side-effects
   - **Options**: Approve | Edit | Defer | Escalate | Cancel

3. **Log Proposed Action** — Use `log_action` with:
   - `action`: Full action description
   - `timestamp`: Current time
   - `agent_reasoning`: Why agent proposed this
   - `user_decision`: "pending"

   Write to audit trail BEFORE awaiting decision

4. **WAIT for User Decision** — Present approval card and pause execution

5. **Process User Decision**:

   **A. If APPROVED:**
   - Execute the proposed action
   - Use `log_action` with `user_decision`: "approved"
   - Return execution result

   **B. If EDITED:**
   - Accept user modifications
   - Re-run detection (step 1) with edited action
   - Generate new approval card if still critical
   - Loop back to step 4

   **C. If DEFERRED:**
   - Use `log_action` with `user_decision`: "deferred"
   - Schedule for later review (add to task list)
   - Return deferral confirmation

   **D. If ESCALATED:**
   - Use `log_action` with `user_decision`: "escalated"
   - Flag for manual handling
   - Do NOT auto-execute
   - Return escalation notice

   **E. If CANCELLED:**
   - Use `log_action` with `user_decision`: "cancelled"
   - Do NOT execute action
   - Return cancellation confirmation

6. **Final Audit Log** — Use `log_action` with final outcome

## Output Format

Return approval card and await decision:

```markdown
## Approval Required: [Action Title]

**What:** Send email to client@example.com with project update

**Why:** User requested email triage created draft reply; client is awaiting update

**Risk:** External communication will be sent from your account

**Options:**
✅ Approve — Send email as drafted
✏️ Edit — Modify email before sending
⏸️ Defer — Review later today
⬆️ Escalate — Handle manually
❌ Cancel — Do not send email

**Context:**
- Email draft previewed in previous message
- Client last contacted 3 days ago
- Marked as high-priority follow-up

---
Approval ID: approval_20260221_001
Created: 2026-02-21T10:30:00
```

## Quality Rules

- **Never assume approval**: Even for previously approved similar actions
- **Clear risk assessment**: Explicit about what could go wrong
- **Concise cards**: 10-second decision time (not walls of text)
- **Provide alternatives**: Always suggest at least one alternative
- **Complete audit trail**: Log proposal, decision, and execution
- **Respect user autonomy**: Accept cancellation without retry

## Critical Action Triggers

Always require approval for:
- Sending email/messages to external parties
- Creating/modifying/deleting calendar events
- Financial transactions or commitments
- Legal language or contract-related actions
- File writes or deletions
- Automation rule changes
- Any action with irreversible consequences

## Safe Actions (No Approval Needed)

May proceed without approval:
- Mark email as read (after user opt-in)
- Create internal task
- Search local documents (within granted scope)
- Generate summaries or reports (not sent)
- Retrieve calendar or email data (read-only)
