"""
Approval & Safety Tools — Risk assessment and user consent workflows
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def detect_critical_action(action_type: str, context: str, risk_profile: str = "standard") -> str:
    """
    Identify if action requires explicit user approval.

    Args:
        action_type: Type of action (send_email, calendar_change, financial_commit, etc.)
        context: Action details and parameters
        risk_profile: User's risk tolerance (conservative, standard, permissive)

    Returns:
        Risk assessment and approval requirement
    """
    # Critical action categories
    critical_actions = {
        "send_email": {
            "is_critical": True,
            "severity": "high",
            "reason": "External communication requiring user review",
        },
        "send_message": {
            "is_critical": True,
            "severity": "high",
            "reason": "External messaging requiring user review",
        },
        "calendar_change": {
            "is_critical": True,
            "severity": "medium",
            "reason": "Calendar modifications affect commitments",
        },
        "financial_commit": {
            "is_critical": True,
            "severity": "critical",
            "reason": "Financial transactions require explicit approval",
        },
        "file_write": {
            "is_critical": True,
            "severity": "medium",
            "reason": "File modifications can cause data loss",
        },
        "automation_rule": {
            "is_critical": True,
            "severity": "high",
            "reason": "Automation rules have ongoing effects",
        },
        "read_only": {
            "is_critical": False,
            "severity": "low",
            "reason": "Read-only operations are safe",
        },
    }

    action_info = critical_actions.get(
        action_type,
        {"is_critical": True, "severity": "medium", "reason": "Unknown action type — defaulting to requiring approval"},
    )

    return json.dumps(
        {
            "action_type": action_type,
            "context": context,
            "is_critical": action_info["is_critical"],
            "severity": action_info["severity"],
            "reason": action_info["reason"],
            "requires_approval": action_info["is_critical"],
            "risk_profile": risk_profile,
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def create_approval_card(action: str, reason: str, alternatives: str = "") -> str:
    """
    Generate user approval prompt with context and options.

    Args:
        action: Clear description of what will be done
        reason: Agent's reasoning for recommending this action
        alternatives: Alternative approaches (optional)

    Returns:
        Formatted approval card for user decision
    """
    approval_card = {
        "title": "Approval Required",
        "action": action,
        "reason": reason,
        "risk_assessment": "This action will have external effects and requires your approval.",
        "alternatives": alternatives or "No alternatives identified",
        "options": {
            "approve": "Execute action as proposed",
            "edit": "Modify action before executing",
            "defer": "Review later",
            "escalate": "Flag for manual handling",
            "cancel": "Do not execute this action",
        },
        "created_at": datetime.now().isoformat(),
    }

    # Format as user-friendly card
    card_text = f"""
## Approval Required: {action}

**What:** {action}
**Why:** {reason}
**Risk:** This action will have external effects and requires your approval.

**Options:**
✅ Approve — Execute as proposed
✏️ Edit — Modify before executing
⏸️ Defer — Review later
⬆️ Escalate — Flag for manual handling
❌ Cancel — Do not execute

**Alternatives:**
{alternatives or "No alternatives identified"}

---
Created: {approval_card['created_at']}
    """.strip()

    return json.dumps(
        {
            "approval_card": approval_card,
            "formatted_output": card_text,
            "status": "awaiting_user_decision",
        },
        indent=2,
    )


@tool
def log_action(action: str, timestamp: str, agent_reasoning: str, user_decision: str = "pending") -> str:
    """
    Write action to audit trail for transparency and debugging.

    Args:
        action: Description of action taken or proposed
        timestamp: When action occurred (ISO format)
        agent_reasoning: Why the agent recommended this action
        user_decision: User's decision (approved, rejected, edited, deferred, pending)

    Returns:
        Log entry confirmation
    """
    log_entry = {
        "action": action,
        "timestamp": timestamp,
        "agent_reasoning": agent_reasoning,
        "user_decision": user_decision,
        "log_id": f"log_{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }

    return json.dumps(
        {
            "status": "logged",
            "log_entry": log_entry,
            "note": "Entry written to audit trail — implement persistent storage in production",
        },
        indent=2,
    )


@tool
def validate_safe_automation(rule: str, scope: str) -> str:
    """
    Check if automation rule is within safe operational bounds.

    Args:
        rule: Automation rule description (e.g., "Auto-archive newsletters older than 7 days")
        scope: Scope of automation (email_folder, calendar, tasks, system)

    Returns:
        Safety validation and recommendations
    """
    # Safety checks
    is_safe = True
    warnings = []

    # Flag risky patterns
    if "delete" in rule.lower():
        is_safe = False
        warnings.append("Deletion rules require user approval for each execution")

    if "send" in rule.lower() or "reply" in rule.lower():
        is_safe = False
        warnings.append("Outbound communication rules require user approval")

    if "financial" in rule.lower() or "payment" in rule.lower():
        is_safe = False
        warnings.append("Financial actions cannot be automated without explicit approval")

    validation = {
        "rule": rule,
        "scope": scope,
        "is_safe_for_automation": is_safe,
        "warnings": warnings,
        "recommendation": "Safe to automate" if is_safe else "Requires approval per execution",
        "validated_at": datetime.now().isoformat(),
    }

    return json.dumps(validation, indent=2)
