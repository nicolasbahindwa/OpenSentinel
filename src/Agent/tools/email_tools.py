"""
Email Integration Tools — Gmail, Outlook, IMAP with triage and action extraction
"""

from langchain_core.tools import tool
import json
from datetime import datetime
from typing import List, Optional


@tool
def connect_email(provider: str, auth_token: Optional[str] = None) -> str:
    """
    Establish OAuth connection to email provider.

    Args:
        provider: Email provider (gmail, outlook, imap)
        auth_token: OAuth 2.0 access token (in production, handled by OAuth flow)

    Returns:
        Connection status and mailbox info
    """
    return json.dumps(
        {
            "status": "connected",
            "provider": provider,
            "mailboxes": [
                {"name": "INBOX", "unread_count": 47},
                {"name": "Sent", "message_count": 1203},
                {"name": "Important", "unread_count": 8},
            ],
            "connection_time": datetime.now().isoformat(),
            "note": "Simulated connection — implement OAuth flow in production",
        },
        indent=2,
    )


@tool
def fetch_emails(
    folder: str = "INBOX",
    unread_only: bool = True,
    since_date: str = "",
    max_count: int = 20,
) -> str:
    """
    Retrieve emails with filters.

    Args:
        folder: Mailbox folder (INBOX, Sent, Important, etc.)
        unread_only: Only fetch unread messages
        since_date: Fetch emails since date (ISO format YYYY-MM-DD)
        max_count: Maximum emails to retrieve (1-100)

    Returns:
        List of emails with metadata (subject, from, date, snippet)
    """
    # Simulated emails
    sample_emails = [
        {
            "id": "email_001",
            "from": "alice@example.com",
            "subject": "Q1 Budget Review - Action Required",
            "date": "2026-02-21T08:30:00",
            "snippet": "Please review the attached budget proposal by Friday...",
            "has_attachments": True,
            "is_read": False,
            "labels": ["Important", "Work"],
        },
        {
            "id": "email_002",
            "from": "newsletter@techcrunch.com",
            "subject": "This Week in Tech",
            "date": "2026-02-21T07:00:00",
            "snippet": "Top stories: AI advances, startup funding rounds...",
            "has_attachments": False,
            "is_read": False,
            "labels": ["Newsletter"],
        },
        {
            "id": "email_003",
            "from": "boss@example.com",
            "subject": "URGENT: Client presentation today at 3pm",
            "date": "2026-02-21T09:15:00",
            "snippet": "Need you to prepare slides for the client meeting this afternoon...",
            "has_attachments": False,
            "is_read": False,
            "labels": ["Important", "Urgent"],
        },
    ]

    return json.dumps(
        {
            "folder": folder,
            "filters": {
                "unread_only": unread_only,
                "since_date": since_date or "all",
                "max_count": max_count,
            },
            "emails": sample_emails,
            "total_fetched": len(sample_emails),
            "note": "Simulated emails — connect to Gmail API / MS Graph in production",
        },
        indent=2,
    )


@tool
def classify_email_intent(email_id: str, content: str) -> str:
    """
    Classify email by intent, urgency, category, and spam probability.

    Args:
        email_id: Unique email identifier
        content: Email subject and body text

    Returns:
        Classification with category, priority, sentiment, spam score
    """
    # Simulated classification — in production, use LLM or trained classifier

    # Simple heuristics for demo
    is_urgent = "URGENT" in content.upper() or "ASAP" in content.upper()
    is_spam = "newsletter" in content.lower() or "unsubscribe" in content.lower()

    classification = {
        "email_id": email_id,
        "category": "action_required" if "action required" in content.lower() else "fyi",
        "priority": "urgent" if is_urgent else "routine",
        "sentiment": "neutral",
        "spam_probability": 0.8 if is_spam else 0.1,
        "requires_response": not is_spam,
        "confidence_score": 0.85,
    }

    return json.dumps(classification, indent=2)


@tool
def extract_action_items(email_id: str, content: str) -> str:
    """
    Extract tasks, deadlines, and commitments from email content.

    Args:
        email_id: Unique email identifier
        content: Email subject and body text

    Returns:
        List of action items with deadlines and priorities
    """
    # Simulated extraction — in production, use LLM with structured output

    action_items = []

    # Simple heuristics for demo
    if "review" in content.lower():
        action_items.append({
            "task": "Review budget proposal",
            "deadline": "2026-02-25",
            "priority": "high",
            "effort_estimate": "30min",
            "source": email_id,
        })

    if "prepare" in content.lower() and "slides" in content.lower():
        action_items.append({
            "task": "Prepare client presentation slides",
            "deadline": "2026-02-21T15:00:00",
            "priority": "urgent",
            "effort_estimate": "2hr",
            "source": email_id,
        })

    return json.dumps(
        {
            "email_id": email_id,
            "action_items": action_items,
            "total_actions": len(action_items),
            "extraction_confidence": 0.8,
            "note": "Simulated extraction — use LLM with function calling in production",
        },
        indent=2,
    )


@tool
def draft_email_reply(
    email_id: str,
    reply_type: str = "professional",
    context: str = "",
) -> str:
    """
    Generate email reply draft. NOT sent without explicit approval.

    Args:
        email_id: Email being replied to
        reply_type: Reply style (professional, urgent, followup, brief)
        context: Additional context for reply generation

    Returns:
        Draft reply (not sent)
    """
    reply_templates = {
        "professional": "Thank you for your email. I've reviewed your message and will {action}.",
        "urgent": "Received and prioritizing this now. I will {action} by {deadline}.",
        "followup": "Following up on our previous conversation. {context}",
        "brief": "Acknowledged. {action}.",
    }

    template = reply_templates.get(reply_type, reply_templates["professional"])

    return json.dumps(
        {
            "status": "draft_created",
            "email_id": email_id,
            "reply_type": reply_type,
            "draft": {
                "to": "alice@example.com",
                "subject": "Re: Q1 Budget Review - Action Required",
                "body": template.format(
                    action="review the budget proposal and respond by Friday",
                    deadline="end of week",
                    context=context,
                ),
            },
            "is_sent": False,
            "note": "Draft created — use send_email with approval to send",
        },
        indent=2,
    )


@tool
def send_email(draft_id: str, approval_token: str) -> str:
    """
    Send email message. REQUIRES EXPLICIT USER APPROVAL (critical action).

    Args:
        draft_id: Draft email identifier
        approval_token: User approval confirmation token

    Returns:
        Send status (pending approval or sent confirmation)
    """
    return json.dumps(
        {
            "status": "pending_approval",
            "action": "send_email",
            "draft_id": draft_id,
            "requires_approval": True,
            "reason": "Sending external emails requires explicit user approval",
            "approval_options": ["approve", "edit", "defer", "cancel"],
            "note": "Email will NOT be sent until user approves this action",
        },
        indent=2,
    )
