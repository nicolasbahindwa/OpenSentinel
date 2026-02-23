"""
Messaging Integration Tools — WhatsApp, Telegram, LINE, etc.
"""

from langchain_core.tools import tool
import json
from datetime import datetime
from typing import Optional


@tool
def connect_messenger(provider: str, auth_token: Optional[str] = None) -> str:
    """
    Connect to messaging platform (WhatsApp, Telegram, LINE, etc.).

    Args:
        provider: Messaging service (whatsapp, telegram, line, signal)
        auth_token: Authentication token or bot credentials

    Returns:
        Connection status
    """
    return json.dumps(
        {
            "status": "connected",
            "provider": provider,
            "account_info": {"user_id": "user123", "display_name": "OpenSentinel User"},
            "connection_time": datetime.now().isoformat(),
            "note": "Simulated connection — implement provider-specific API in production",
        },
        indent=2,
    )


@tool
def fetch_messages(provider: str, unread_only: bool = True, max_count: int = 20) -> str:
    """
    Read messages from messaging platform (read-only by default).

    Args:
        provider: Messaging service (whatsapp, telegram, line)
        unread_only: Only fetch unread messages
        max_count: Maximum messages to retrieve

    Returns:
        List of messages
    """
    # Simulated messages
    sample_messages = [
        {
            "id": "msg_001",
            "from": "+1234567890",
            "text": "Hey, can you send me the project update?",
            "timestamp": "2026-02-21T10:30:00",
            "is_read": False,
        },
        {
            "id": "msg_002",
            "from": "alice_telegram",
            "text": "Meeting rescheduled to 3pm",
            "timestamp": "2026-02-21T09:15:00",
            "is_read": False,
        },
    ]

    return json.dumps(
        {
            "provider": provider,
            "filters": {"unread_only": unread_only, "max_count": max_count},
            "messages": sample_messages,
            "total_fetched": len(sample_messages),
            "note": "Simulated messages — connect to provider API in production",
        },
        indent=2,
    )


@tool
def classify_message_urgency(message_id: str, content: str) -> str:
    """
    Triage messaging app notifications by urgency.

    Args:
        message_id: Message identifier
        content: Message text

    Returns:
        Urgency classification
    """
    is_urgent = "urgent" in content.lower() or "asap" in content.lower() or "?" in content

    return json.dumps(
        {
            "message_id": message_id,
            "urgency": "high" if is_urgent else "normal",
            "requires_response": "?" in content,
            "confidence": 0.8,
        },
        indent=2,
    )


@tool
def draft_message_reply(message_id: str, reply_type: str = "brief") -> str:
    """
    Propose message reply. REQUIRES APPROVAL before sending.

    Args:
        message_id: Message being replied to
        reply_type: Reply style (brief, detailed, acknowledgment)

    Returns:
        Draft reply (not sent)
    """
    return json.dumps(
        {
            "status": "draft_created",
            "message_id": message_id,
            "draft_reply": "Thanks for reaching out! I'll get back to you shortly.",
            "is_sent": False,
            "note": "Draft created — requires explicit approval to send",
        },
        indent=2,
    )
