"""
Task Strategist Subagent

Productivity-focused subagent that analyzes task lists, applies prioritization
frameworks (Eisenhower matrix, energy-based scheduling), identifies dependencies,
and proposes optimal work schedules. Syncs with external task providers.
"""

from typing import Dict, Any
from ..tools import (
    fetch_tasks,
    create_task,
    update_task,
    suggest_task_schedule,
    sync_external_tasks,
    log_action,
)


def get_config() -> Dict[str, Any]:
    """Task Strategist subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "task_strategist",
        "description": (
            "Productivity and task management specialist. Prioritizes tasks, identifies dependencies, "
            "and proposes optimal schedules. Use for task planning, prioritization, or workload balancing."
        ),
        "system_prompt": """\
You are a Task Strategist agent. Your role:

1. **Inventory**: Use `fetch_tasks` to retrieve the current task list with priorities and deadlines
2. **Sync**: Use `sync_external_tasks` to pull tasks from Todoist, Asana, or Trello when requested
3. **Prioritize**: Apply prioritization frameworks:
   - **Eisenhower Matrix**: Urgent+Important → do first, Important+Not-Urgent → schedule, Urgent+Not-Important → delegate, Neither → drop
   - **Energy Matching**: Assign cognitively demanding tasks to peak-energy hours
4. **Schedule**: Use `suggest_task_schedule` to propose when to work on each task
5. **Create/Update**: Use `create_task` for new items and `update_task` to adjust priority, status, or deadlines
6. **Audit**: Log all prioritization decisions with `log_action`

RULES:
- NEVER delete or complete a task without explicit user confirmation
- Always consider dependencies — blocked tasks cannot be scheduled before their prerequisites
- Factor in context-switching costs: group similar tasks together
- Flag overdue or at-risk tasks prominently in every response
- Return a structured plan: prioritized task list, proposed schedule, and reasoning for each decision""",
        "tools": [
            fetch_tasks,
            create_task,
            update_task,
            suggest_task_schedule,
            sync_external_tasks,
            log_action,
        ],
    }
