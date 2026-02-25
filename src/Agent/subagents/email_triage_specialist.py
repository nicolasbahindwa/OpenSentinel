"""
Email Triage Specialist Subagent Configuration

Classifies emails, extracts action items, and drafts responses.
"""

from ..tools import (
    connect_email,
    fetch_emails,
    classify_email_intent,
    extract_action_items,
    draft_email_reply,
    create_task,
)


def get_config():
    """Returns the email triage specialist subagent configuration."""
    return {
        "name": "email_triage_specialist",
        "description": "Classifies emails, extracts action items, and drafts responses. Use for inbox processing.",
        "system_prompt": (
            "You are an email management specialist. Classify emails by urgency and intent, "
            "extract actionable tasks, and draft appropriate replies. Prioritize based on sender importance "
            "and content urgency. Return a structured triage report."
        ),
        "tools": [
            connect_email,
            fetch_emails,
            classify_email_intent,
            extract_action_items,
            draft_email_reply,
            create_task,
        ],
    }
