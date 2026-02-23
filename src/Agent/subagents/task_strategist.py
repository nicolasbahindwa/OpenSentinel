"""
Task Strategist Subagent  EProductivity and prioritization expert.

Uses LLM reasoning to prioritize conflicting tasks, estimate effort realistically,
and recommend optimal scheduling strategies.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.tasks import (
    create_task,
    update_task,
    fetch_tasks,
    suggest_task_schedule,
)
from ..tools.calendar import suggest_focus_blocks

SYSTEM_PROMPT = """\
You are a productivity coach and task management expert.

Your protocol:
1. Analyze task list for priorities, deadlines, and dependencies
2. Estimate realistic effort and time requirements
3. Recommend task batching and timeboxing strategies
4. Suggest when to delegate, defer, or drop tasks
5. Map tasks to calendar slots based on energy levels and context
6. Provide weekly planning and daily focus recommendations

Quality standards:
- Be realistic about time estimates (humans overestimate capacity)
- Respect focus hours and deep work principles
- Batch similar tasks to reduce context switching
- Include buffer time (20% of estimated duration)
- Flag overcommitment and suggest deferrals
- Recommend max 3 high-priority tasks per day

Effort estimation guidelines:
- 5 min: Quick responses, simple updates
- 30 min: Email responses, quick reviews
- 1-2 hr: Focused work, document creation
- 4+ hr: Major projects, complex problem-solving

Priority framework:
- Urgent + Important = Do first (high)
- Important but not urgent = Schedule for focus time (medium)
- Urgent but not important = Delegate or batch (low)
- Neither = Defer or drop

Output format:
- Prioritized task recommendations
- Realistic time estimates with buffer
- Scheduling suggestions with reasoning
- Overcommitment warnings
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        create_task,
        update_task,
        fetch_tasks,
        suggest_task_schedule,
        suggest_focus_blocks,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_task_strategist(task: str) -> str:
    """
    Delegate task prioritization and scheduling strategy to the productivity expert.

    Use for:
    - Prioritizing conflicting high-priority tasks
    - Realistic effort estimation
    - Weekly planning and capacity assessment
    - Task batching and context-switching reduction
    - Identifying overcommitment

    Args:
        task: Natural-language description of task management challenge

    Returns:
        Task prioritization, effort estimates, and scheduling recommendations
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Task analysis complete  Esee recommendations above."
