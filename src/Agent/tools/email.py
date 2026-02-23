"""
Email Tools — Email composition and classification.
"""

from langchain_core.tools import tool
import json
from datetime import datetime, timedelta


@tool
def compose_email(recipient: str, subject: str, message_type: str = "professional") -> str:
    """
    Compose a professional email message.

    Args:
        recipient: Email recipient name or address
        subject: Email subject line
        message_type: Style of message (professional, informal, urgent, followup)

    Returns:
        JSON string containing composed email
    """
    message_templates = {
        "professional": (
            f"Dear {recipient},\n\n"
            f"I hope this message finds you well. Regarding {subject}, "
            "I wanted to reach out with some important updates and insights.\n\n"
            "Key points:\n"
            "- Important consideration 1\n"
            "- Important consideration 2\n"
            "- Important consideration 3\n\n"
            "I would appreciate the opportunity to discuss this further "
            "at your earliest convenience.\n\n"
            "Best regards,\nBusiness Agent"
        ),
        "informal": (
            f"Hi {recipient},\n\n"
            f"Quick note about {subject} - I've got some good news and updates to share.\n\n"
            "Here's what's happening:\n"
            "- Update 1\n- Update 2\n- Update 3\n\n"
            "Let me know your thoughts!\n\nCheers,\nAgent"
        ),
        "urgent": (
            f"URGENT - {recipient}\n\n"
            f"This requires immediate attention regarding {subject}.\n\n"
            "Critical action items:\n"
            "1. Action 1 - Complete by end of today\n"
            "2. Action 2 - Review attached documents\n"
            "3. Action 3 - Confirm receipt\n\n"
            "Please acknowledge receipt immediately.\n\nBusiness Agent"
        ),
        "followup": (
            f"Hi {recipient},\n\n"
            f"Following up on our previous discussion about {subject}.\n\n"
            "Status update:\n"
            "- Progress item 1: Complete\n"
            "- Progress item 2: In progress\n"
            "- Progress item 3: Pending\n\n"
            "Next steps: Schedule meeting to review deliverables.\n\n"
            "Regards,\nAgent"
        ),
    }

    email_body = message_templates.get(message_type, message_templates["professional"])

    return json.dumps(
        {
            "recipient": recipient,
            "subject": subject,
            "message_type": message_type,
            "body": email_body,
            "estimated_send_time": (datetime.now() + timedelta(minutes=1)).isoformat(),
            "priority": "High" if message_type == "urgent" else "Normal",
            "ready_to_send": True,
        },
        indent=2,
    )


@tool
def classify_email(email_content: str, classification_type: str = "category") -> str:
    """
    Classify an email message for routing and prioritization.

    Args:
        email_content: The email content/body to classify
        classification_type: Type of classification (category, priority, sentiment, spam)

    Returns:
        JSON string containing classification results
    """
    priority_scores = {
        "urgent": 0.1 if any(w in email_content.lower() for w in ["urgent", "asap", "immediate", "emergency"]) else 0.0,
        "important": 0.1 if any(w in email_content.lower() for w in ["important", "critical", "must", "essential"]) else 0.0,
        "routine": 0.1 if any(w in email_content.lower() for w in ["routine", "standard", "normal", "regular"]) else 0.0,
    }

    top_priority = max(priority_scores, key=priority_scores.get)
    sentiment_score = 0.7 if any(w in email_content.lower() for w in ["thanks", "appreciate", "please"]) else 0.5

    if "product" in email_content.lower():
        category = "Sales"
    elif "issue" in email_content.lower():
        category = "Support"
    else:
        category = "General"

    return json.dumps(
        {
            "email_length": len(email_content),
            "category": category,
            "priority": top_priority,
            "sentiment": "Positive" if sentiment_score > 0.7 else "Neutral" if sentiment_score > 0.4 else "Negative",
            "sentiment_score": round(sentiment_score, 2),
            "spam_probability": 0.02,
            "requires_response": True,
            "suggested_response_time": "1-2 hours",
            "classification_confidence": 0.92,
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )
