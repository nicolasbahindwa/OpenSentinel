"""
Scheduling Coordinator Subagent  ESmart calendar and time management specialist.

Uses LLM reasoning to handle complex scheduling scenarios requiring judgment:
multi-person coordination, priority conflicts, travel time estimation.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Import calendar and task tools

from ..tools.calendar import (
    fetch_calendar_events,
    create_calendar_event,
    update_calendar_event,
    suggest_focus_blocks,
    detect_calendar_conflicts,
)
from ..tools.tasks import fetch_tasks, suggest_task_schedule
from ..tools.approvals import detect_critical_action, create_approval_card

SYSTEM_PROMPT = """\
You are a senior executive assistant specializing in calendar optimization and time management.

Your protocol:
1. Understand the user's scheduling constraints and preferences
2. Identify conflicts and propose resolutions
3. Suggest optimal focus blocks for deep work
4. Coordinate multi-person meetings (check availability, propose times)
5. Factor in travel time, buffer time, and energy levels
6. ALWAYS flag calendar changes as critical actions requiring approval
7. Provide clear reasoning for every scheduling recommendation

Quality standards:
- Never double-book
- Respect user-defined focus hours
- Include buffer time between meetings (10-15 min minimum)
- Optimize for minimal context switching
- Present max 3 options for user decision
- Energy-aware scheduling: high-priority work in morning, routine in afternoon

Output format:
- Structured scheduling proposals with reasoning
- Approval cards for all calendar modifications
- Clear alternatives and trade-offs
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        fetch_calendar_events,
        create_calendar_event,
        update_calendar_event,
        suggest_focus_blocks,
        detect_calendar_conflicts,
        fetch_tasks,
        suggest_task_schedule,
        detect_critical_action,
        create_approval_card,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_scheduling_coordinator(task: str) -> str:
    """
    Delegate complex scheduling tasks to the calendar optimization specialist.

    Use for:
    - Multi-person meeting coordination
    - Resolving scheduling conflicts with competing priorities
    - Optimizing weekly calendar for focus time
    - Travel time and logistics planning
    - Complex rescheduling scenarios

    Args:
        task: Natural-language description of scheduling challenge

    Returns:
        Scheduling recommendations with approval cards for changes
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    # Return the last AI message content
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Scheduling analysis complete  Eno specific recommendations."
