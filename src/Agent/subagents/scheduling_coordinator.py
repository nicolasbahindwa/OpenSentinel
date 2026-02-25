"""
Scheduling Coordinator Subagent Configuration

Optimizes calendar layouts, resolves conflicts, and suggests focus blocks.
"""

from ..tools import (
    connect_calendar,
    fetch_calendar_events,
    create_calendar_event,
    update_calendar_event,
    detect_calendar_conflicts,
    suggest_focus_blocks,
    fetch_tasks,
)


def get_config():
    """Returns the scheduling coordinator subagent configuration."""
    return {
        "name": "scheduling_coordinator",
        "description": "Optimizes calendar layouts, resolves conflicts, and suggests focus blocks. Use for complex scheduling decisions.",
        "system_prompt": (
            "You are a scheduling specialist. Analyze calendars, suggest optimal meeting times, "
            "resolve conflicts, and create focus blocks. Always check for conflicts before creating events. "
            "Return structured recommendations with reasoning."
        ),
        "tools": [
            connect_calendar,
            fetch_calendar_events,
            create_calendar_event,
            update_calendar_event,
            detect_calendar_conflicts,
            suggest_focus_blocks,
            fetch_tasks,
        ],
    }
