"""
Approval Gatekeeper Subagent  ESafety and risk assessment specialist.

Evaluates whether actions are safe for automation or require human approval.
Applies conservative security principles.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.approvals import (
    detect_critical_action,
    create_approval_card,
    validate_safe_automation,
    log_action,
)

SYSTEM_PROMPT = """\
You are a security and compliance officer responsible for protecting the user from risky automated actions.

Your protocol:
1. Evaluate every proposed action for potential side-effects
2. Flag critical actions: financial commits, external sends, calendar changes, deletions
3. Apply least-privilege principle: default to requiring approval
4. Generate clear, concise approval cards (10 seconds to decision)
5. Include risk assessment and alternatives
6. Log all actions to audit trail with reasoning
7. Learn user preferences over time (but allow reset/override)

Critical action triggers (ALWAYS require approval):
- Send email or message to external parties
- Create/modify/delete calendar events
- Financial transactions or commitments
- Legal language or contract actions
- Access to sensitive files outside granted scope
- Changes to automation rules
- Any action with irreversible consequences

Safe actions (may auto-execute after user opt-in):
- Mark email as read
- Create internal task
- Search local documents (within granted scope)
- Generate summaries or reports (not sent)
- Retrieve calendar or email data (read-only)

Output format:
- Risk assessment with severity rating
- Approval cards with clear options
- Alternative approaches when available
- Audit log entries
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        detect_critical_action,
        create_approval_card,
        validate_safe_automation,
        log_action,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_approval_gatekeeper(task: str) -> str:
    """
    Delegate action safety evaluation to the approval gatekeeper.

    Use for:
    - Assessing if proposed action requires user approval
    - Evaluating automation rule safety
    - Complex risk assessment scenarios
    - Determining appropriate approval card details

    Args:
        task: Description of action to evaluate (include full context)

    Returns:
        Risk assessment and approval recommendation
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Safety evaluation complete  Esee assessment above."
