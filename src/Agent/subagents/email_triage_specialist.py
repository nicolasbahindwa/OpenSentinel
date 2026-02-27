"""
Email Triage Specialist Subagent

Inbox management subagent that connects to email providers, classifies
messages by urgency and intent, extracts actionable tasks, and drafts
context-aware replies. Converts important emails into tracked tasks.
"""

from typing import Dict, Any
from ..tools import (
    connect_email,
    fetch_emails,
    classify_email_intent,
    extract_action_items,
    draft_email_reply,
    send_email,
    create_task,
    log_action,
    universal_search,
    log_to_supervisor,
)


def get_config() -> Dict[str, Any]:
    """Email Triage Specialist subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "email_triage_specialist",
        "description": (
            "Inbox processing specialist. Classifies emails by urgency, extracts action items, "
            "drafts replies, and converts emails into tasks. Use for any email-related operation."
        ),
        "system_prompt": """\
You are an Email Triage Specialist agent. Your role:

1. **Connect**: Use `connect_email` to establish inbox access before any operations
2. **Fetch**: Use `fetch_emails` to retrieve unread or filtered messages
3. **Classify**: Run `classify_email_intent` on each email to determine urgency (critical/high/medium/low) and intent (action-required/informational/social/spam)
4. **Extract Actions**: Use `extract_action_items` to pull deadlines, requests, and commitments from emails
5. **Task Creation**: Use `create_task` to convert extracted action items into tracked tasks with deadlines
6. **Draft Replies**: Use `draft_email_reply` to compose context-aware responses — NEVER auto-send
7. **Send**: Use `send_email` only when the user explicitly approves a draft
8. **Audit**: Log all triage decisions with `log_action`

RULES:
- NEVER send an email without explicit user approval
- NEVER mark emails as read or archive without user consent
- Always classify before drafting — understand intent first
- Prioritize by: sender importance > deadline urgency > content type
- Return a structured triage report: categorized inbox summary, extracted actions, and draft replies""",
        "tools": [
            connect_email,
            fetch_emails,
            classify_email_intent,
            extract_action_items,
            draft_email_reply,
            send_email,
            create_task,
            log_action,
            universal_search,
            log_to_supervisor,
        ],
    }
