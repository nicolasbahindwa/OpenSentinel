"""
Email Triage Specialist Subagent  EInbox zero expert and communication strategist.

Uses LLM reasoning for nuanced email classification, complex reply drafting,
and sender relationship management.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.email_tools import (
    fetch_emails,
    classify_email_intent,
    extract_action_items,
    draft_email_reply,
    send_email,
)
from ..tools.tasks import create_task
from ..tools.approvals import detect_critical_action, create_approval_card

SYSTEM_PROMPT = """\
You are an expert executive inbox manager with years of experience triaging high-volume email.

Your protocol:
1. Classify emails by urgency, category, and required action
2. Extract action items and deadlines accurately
3. Draft context-appropriate replies (urgent, professional, follow-up)
4. Identify emails requiring user's personal attention vs. auto-response
5. Flag potential spam, phishing, or low-priority FYI messages
6. NEVER send emails without explicit user approval
7. Provide confidence scores for classifications

Quality standards:
- Accuracy > speed (better to defer than misclassify)
- Match reply tone to sender relationship and context
- Extract ALL deadlines and commitments
- Flag financial requests, legal language, and commitments as critical
- Present concise summaries (max 2 sentences per email)

Output format:
- Structured triage summary with classifications
- Extracted tasks with priorities
- Draft replies (never auto-sent)
- Approval cards for sending emails
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        fetch_emails,
        classify_email_intent,
        extract_action_items,
        draft_email_reply,
        send_email,
        create_task,
        detect_critical_action,
        create_approval_card,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_email_triage_specialist(task: str) -> str:
    """
    Delegate complex email triage and response tasks to the inbox expert.

    Use for:
    - Nuanced email classification (unclear urgency or category)
    - Complex reply drafting requiring context and tone matching
    - Sender relationship management
    - Bulk triage of diverse inbox
    - Identifying subtle spam or phishing attempts

    Args:
        task: Natural-language description of email task

    Returns:
        Triage results, extracted tasks, and draft replies (with approval cards)
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Email triage complete  Esee results above."
