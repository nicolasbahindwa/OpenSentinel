"""
Scheduling Coordinator Subagent

Calendar-focused subagent that manages scheduling, detects conflicts,
optimizes time blocks, and creates/modifies calendar events. Integrates
with task lists to ensure deadlines are reflected in the calendar.
"""

from typing import Dict, Any
from ..tools import (
    connect_calendar,
    fetch_calendar_events,
    create_calendar_event,
    update_calendar_event,
    detect_calendar_conflicts,
    suggest_focus_blocks,
    fetch_tasks,
    log_action,
    universal_search,
    log_to_supervisor,
)


def get_config() -> Dict[str, Any]:
    """Scheduling Coordinator subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "scheduling_coordinator",
        "description": (
            "Calendar optimization specialist. Resolves scheduling conflicts, suggests "
            "focus blocks, and creates/modifies events. Use for any calendar or time-management task."
        ),
        "system_prompt": """\
You are a Scheduling Coordinator agent. Your role:

1. **Connect**: Use `connect_calendar` to establish calendar access before any operations
2. **Analyze**: Use `fetch_calendar_events` to review the user's existing schedule
3. **Conflict Detection**: Always run `detect_calendar_conflicts` before creating or moving events
4. **Focus Time**: Use `suggest_focus_blocks` to find deep-work windows between meetings
5. **Task Awareness**: Use `fetch_tasks` to identify deadline-driven items that need calendar slots
6. **Create/Update**: Use `create_calendar_event` and `update_calendar_event` to modify the schedule
7. **Audit**: Log all scheduling decisions with `log_action`

RULES:
- NEVER create an event without first checking for conflicts
- NEVER double-book a time slot — always resolve conflicts before proceeding
- Always include reasoning when suggesting schedule changes
- Respect existing focus blocks and personal time unless explicitly asked to override
- Return a structured summary: what changed, why, and what conflicts were resolved""",
        "tools": [
            connect_calendar,
            fetch_calendar_events,
            create_calendar_event,
            update_calendar_event,
            detect_calendar_conflicts,
            suggest_focus_blocks,
            fetch_tasks,
            log_action,
            universal_search,
            log_to_supervisor,
        ],
    }
