"""
System Monitor Subagent Configuration

Monitors device health, tracks app usage, and suggests system optimizations.
"""

from ..tools import (
    get_system_metrics,
    monitor_app_usage,
    check_device_health,
    suggest_system_optimization,
)


def get_config():
    """Returns the system monitor subagent configuration."""
    return {
        "name": "system_monitor",
        "description": "Monitors device health, tracks app usage, and suggests system optimizations. Use for system diagnostics.",
        "system_prompt": (
            "You are a system health specialist. Monitor CPU, memory, disk, and battery metrics. "
            "Track application usage patterns. Identify performance bottlenecks and suggest optimizations. "
            "Present findings in a clear, actionable format."
        ),
        "tools": [
            get_system_metrics,
            monitor_app_usage,
            check_device_health,
            suggest_system_optimization,
        ],
    }
