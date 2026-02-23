"""
Task Management Tools — Unified task list with external integrations
"""

from langchain_core.tools import tool
import json
from datetime import datetime
from typing import Dict, List, Optional


@tool
def create_task(
    title: str,
    priority: str = "medium",
    deadline: str = "",
    effort_estimate: str = "",
    source: str = "manual",
) -> str:
    """
    Add task to unified task list.

    Args:
        title: Task description
        priority: Priority level (urgent, high, medium, low)
        deadline: Due date (ISO format YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)
        effort_estimate: Time estimate (5min, 30min, 2hr, 4hr+)
        source: Origin of task (manual, email, calendar, meeting_notes)

    Returns:
        Created task with unique ID
    """
    task_id = f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    task = {
        "id": task_id,
        "title": title,
        "priority": priority,
        "deadline": deadline or None,
        "effort_estimate": effort_estimate or "unknown",
        "source": source,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
    }

    return json.dumps(
        {
            "status": "created",
            "task": task,
            "note": "Task added to unified list — sync with external providers via sync_external_tasks",
        },
        indent=2,
    )


@tool
def update_task(task_id: str, updates: Dict) -> str:
    """
    Modify task status or details.

    Args:
        task_id: Unique task identifier
        updates: Dictionary of fields to update (status, priority, deadline, etc.)

    Returns:
        Updated task
    """
    return json.dumps(
        {
            "status": "updated",
            "task_id": task_id,
            "applied_updates": updates,
            "updated_at": datetime.now().isoformat(),
            "note": "Task updated in local list — sync with external providers if needed",
        },
        indent=2,
    )


@tool
def fetch_tasks(
    priority: str = "",
    deadline_range: str = "",
    status: str = "pending",
) -> str:
    """
    Retrieve tasks with filters.

    Args:
        priority: Filter by priority (urgent, high, medium, low) — empty for all
        deadline_range: Filter by deadline (today, this_week, overdue) — empty for all
        status: Filter by status (pending, in_progress, completed, deferred)

    Returns:
        List of matching tasks
    """
    # Simulated task list
    sample_tasks = [
        {
            "id": "task_001",
            "title": "Review budget proposal",
            "priority": "high",
            "deadline": "2026-02-25",
            "effort_estimate": "30min",
            "source": "email",
            "status": "pending",
        },
        {
            "id": "task_002",
            "title": "Prepare client presentation slides",
            "priority": "urgent",
            "deadline": "2026-02-21T15:00:00",
            "effort_estimate": "2hr",
            "source": "email",
            "status": "in_progress",
        },
        {
            "id": "task_003",
            "title": "Update project documentation",
            "priority": "medium",
            "deadline": "2026-02-28",
            "effort_estimate": "1hr",
            "source": "manual",
            "status": "pending",
        },
    ]

    # Apply filters
    filtered_tasks = [t for t in sample_tasks if t["status"] == status] if status else sample_tasks
    if priority:
        filtered_tasks = [t for t in filtered_tasks if t["priority"] == priority]

    return json.dumps(
        {
            "filters": {
                "priority": priority or "all",
                "deadline_range": deadline_range or "all",
                "status": status,
            },
            "tasks": filtered_tasks,
            "total_count": len(filtered_tasks),
            "note": "Simulated task list — connect to local DB in production",
        },
        indent=2,
    )


@tool
def suggest_task_schedule(task_ids: List[str], date_range: str) -> str:
    """
    Propose when to work on tasks based on calendar availability.

    Args:
        task_ids: List of task IDs to schedule
        date_range: Date range for scheduling (e.g., "2026-02-21 to 2026-02-25")

    Returns:
        Suggested task-to-timeslot mapping
    """
    # Simulated scheduling suggestions
    suggestions = [
        {
            "task_id": "task_001",
            "task_title": "Review budget proposal",
            "suggested_slot": {
                "start": "2026-02-22T10:00:00",
                "end": "2026-02-22T10:30:00",
                "reasoning": "Morning slot, 30min estimated, aligns with deadline",
            },
            "confidence": 0.85,
        },
        {
            "task_id": "task_002",
            "task_title": "Prepare client presentation slides",
            "suggested_slot": {
                "start": "2026-02-21T11:00:00",
                "end": "2026-02-21T13:00:00",
                "reasoning": "Urgent deadline today at 3pm, 2hr block available",
            },
            "confidence": 0.95,
        },
    ]

    return json.dumps(
        {
            "date_range": date_range,
            "requested_tasks": len(task_ids),
            "suggestions": suggestions,
            "note": "Suggestions only — use create_calendar_event with approval to schedule",
        },
        indent=2,
    )


@tool
def sync_external_tasks(provider: str, auth_token: Optional[str] = None) -> str:
    """
    Sync with external task management services (Todoist, Asana, etc.).

    Args:
        provider: Task service (todoist, asana, trello, etc.)
        auth_token: OAuth access token

    Returns:
        Sync status and statistics
    """
    return json.dumps(
        {
            "status": "synced",
            "provider": provider,
            "sync_time": datetime.now().isoformat(),
            "statistics": {
                "tasks_imported": 12,
                "tasks_exported": 3,
                "conflicts_resolved": 0,
            },
            "note": "Simulated sync — implement provider-specific API in production",
        },
        indent=2,
    )
