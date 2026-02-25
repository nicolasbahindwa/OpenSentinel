"""
Daily Briefing Compiler Subagent Configuration

Compiles daily briefings from calendar, weather, tasks, news, and messages.
"""

from ..tools import (
    fetch_calendar_events,
    get_current_weather,
    get_weather_forecast,
    fetch_tasks,
    fetch_messages,
    classify_message_urgency,
    search_news,
    generate_summary,
)


def get_config():
    """Returns the daily briefing compiler subagent configuration."""
    return {
        "name": "daily_briefing_compiler",
        "description": "Compiles daily briefings from calendar, weather, tasks, and news. Use for morning briefings.",
        "system_prompt": (
            "You are a daily briefing specialist. Compile information from multiple sources "
            "(calendar, weather, tasks, news, messages) into a concise, actionable morning briefing. "
            "Prioritize by urgency and impact. Use markdown formatting."
        ),
        "tools": [
            fetch_calendar_events,
            get_current_weather,
            get_weather_forecast,
            fetch_tasks,
            fetch_messages,
            classify_message_urgency,
            search_news,
            generate_summary,
        ],
    }
