"""
System Monitoring Tools — Device health, app usage, performance metrics
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def get_system_metrics(metric_types: str = "all") -> str:
    """
    Retrieve system performance metrics (CPU, memory, disk, battery, network).

    Args:
        metric_types: Comma-separated list (cpu, memory, disk, battery, network) or "all"

    Returns:
        Current system metrics
    """
    # Simulated metrics — in production use psutil, WMI (Windows), or macOS APIs
    metrics = {
        "cpu": {"usage_percent": 45.2, "cores": 8, "temperature": 65},
        "memory": {"total_gb": 16, "used_gb": 10.5, "available_gb": 5.5, "percent": 65.6},
        "disk": {"total_gb": 512, "used_gb": 320, "free_gb": 192, "percent": 62.5},
        "battery": {"percent": 78, "is_charging": False, "time_remaining_hours": 4.2},
        "network": {"download_mbps": 45.3, "upload_mbps": 12.1, "is_connected": True},
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(
        {"requested_metrics": metric_types, "metrics": metrics, "note": "Simulated metrics — use psutil in production"},
        indent=2,
    )


@tool
def monitor_app_usage(date_range: str = "today") -> str:
    """
    Track application focus time (opt-in feature).

    Args:
        date_range: Time period (today, this_week, this_month)

    Returns:
        App usage statistics
    """
    # Simulated app usage data
    usage_data = [
        {"app": "VS Code", "focus_time_minutes": 185, "switch_count": 12},
        {"app": "Chrome", "focus_time_minutes": 95, "switch_count": 34},
        {"app": "Slack", "focus_time_minutes": 42, "switch_count": 18},
        {"app": "Zoom", "focus_time_minutes": 60, "switch_count": 3},
    ]

    return json.dumps(
        {
            "date_range": date_range,
            "top_apps": usage_data,
            "total_focus_time": sum(app["focus_time_minutes"] for app in usage_data),
            "note": "Simulated data — implement with OS-specific APIs (ActivityWatch, RescueTime)",
        },
        indent=2,
    )


@tool
def check_device_health() -> str:
    """
    Surface system alerts (high memory, thermal events, disk space warnings).

    Returns:
        Health status and alerts
    """
    # Simulated health check
    alerts = [
        {
            "type": "memory_warning",
            "severity": "medium",
            "message": "Memory usage at 65% — consider closing unused applications",
            "recommendation": "Close background apps or restart",
        }
    ]

    return json.dumps(
        {
            "health_status": "warning" if alerts else "healthy",
            "alerts": alerts,
            "checked_at": datetime.now().isoformat(),
            "note": "Simulated alerts — implement threshold-based monitoring in production",
        },
        indent=2,
    )


@tool
def suggest_system_optimization(metrics: str) -> str:
    """
    Recommend system optimization actions based on current metrics.

    Args:
        metrics: JSON string of current system metrics (from get_system_metrics)

    Returns:
        Actionable optimization recommendations
    """
    recommendations = [
        {
            "action": "Close unused browser tabs",
            "reason": "Memory usage above 60%",
            "impact": "Free ~2GB memory",
            "priority": "medium",
        },
        {
            "action": "Clear disk cache and temp files",
            "reason": "Disk usage above 60%",
            "impact": "Free ~5-10GB storage",
            "priority": "low",
        },
    ]

    return json.dumps(
        {"recommendations": recommendations, "generated_at": datetime.now().isoformat()},
        indent=2,
    )
