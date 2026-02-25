"""
Task Strategist Subagent Configuration

Analyzes task lists and suggests prioritization strategies.
"""

from ..tools import (
    fetch_tasks,
    create_task,
    update_task,
    suggest_task_schedule,
)


def get_config():
    """Returns the task strategist subagent configuration."""
    return {
        "name": "task_strategist",
        "description": "Analyzes task lists and suggests prioritization strategies. Use for task management.",
        "system_prompt": (
            "You are a productivity strategist. Analyze task lists, suggest prioritization frameworks "
            "(Eisenhower matrix, energy-based scheduling), and identify task dependencies. "
            "Consider deadlines, energy levels, and context switching costs."
        ),
        "tools": [
            fetch_tasks,
            create_task,
            update_task,
            suggest_task_schedule,
        ],
    }
