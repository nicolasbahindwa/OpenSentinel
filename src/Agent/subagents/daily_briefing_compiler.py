"""
Daily Briefing Compiler Subagent  EPersonal chief of staff for daily summaries.

Generates comprehensive morning briefings, weekly reviews, and on-demand status updates.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.calendar import fetch_calendar_events, suggest_focus_blocks
from ..tools.email_tools import fetch_emails, classify_email_intent, extract_action_items
from ..tools.tasks import fetch_tasks, create_task
from ..tools.approvals import detect_critical_action, create_approval_card
from ..tools.system_monitoring import get_system_metrics, check_device_health

SYSTEM_PROMPT = """\
You are a personal chief of staff responsible for daily briefings and status updates.

Your protocol:
1. Pull data: today's calendar, unread emails, high-priority tasks, critical approvals
2. Surface the most important 3-5 items requiring user attention
3. Suggest optimal focus blocks for deep work
4. Flag critical approvals with approval cards
5. Include device health summary if alerts present
6. Provide concise, actionable briefing (2-minute read max)

Briefing structure:
- **Critical Approvals** (if any)  Emax 3, most urgent first
- **Today's Schedule**  Etime-blocked view with focus slots highlighted
- **Top 3 Actions**  Eprioritized tasks with deadlines and estimates
- **Inbox Summary**  EX unread, Y urgent, Z converted to tasks
- **Device Health** (if alerts)  Erecommendations only
- **Suggested Focus**  Erecommended deep work block with reasoning

Quality standards:
- Concise (2-minute read, ~400-500 words)
- Actionable (every item has a clear next step)
- Prioritized (most critical first)
- Time-aware (morning briefing = forward-looking, evening = retrospective)
- Include confidence scores if classifications below 0.8
- Cite sources (email IDs, calendar event IDs, task IDs)

Tone:
- Morning briefing: Energetic, forward-looking, empowering
- Evening review: Reflective, accomplishment-focused, prep for tomorrow
- Ad-hoc status: Neutral, informative, concise

Output format: Use Daily Briefing Format from system prompt
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        fetch_calendar_events,
        suggest_focus_blocks,
        fetch_emails,
        classify_email_intent,
        extract_action_items,
        fetch_tasks,
        create_task,
        detect_critical_action,
        create_approval_card,
        get_system_metrics,
        check_device_health,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_daily_briefing_compiler(task: str) -> str:
    """
    Delegate briefing generation to the personal chief of staff.

    Use for:
    - Morning daily briefing
    - Evening review and next-day prep
    - Weekly planning summary
    - On-demand status updates
    - Comprehensive inbox/calendar/task synthesis

    Args:
        task: Briefing request (e.g., "Generate morning briefing for today")

    Returns:
        Formatted briefing with schedule, actions, approvals, and focus recommendations
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Daily briefing compiled  Esee above."
