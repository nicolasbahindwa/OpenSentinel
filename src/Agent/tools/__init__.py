"""
Tools module — Atomic, stateless functions for personal productivity and life management.

Each tool performs a single operation and returns structured JSON.
Tools are the lowest-level building blocks; they are composed by
skills (deterministic pipelines) and subagents (LLM-driven specialists).
"""

# Calendar & Scheduling
from .calendar import (
    connect_calendar,
    fetch_calendar_events,
    create_calendar_event,
    update_calendar_event,
    suggest_focus_blocks,
    detect_calendar_conflicts,
)

# Email Integration
from .email_tools import (
    connect_email,
    fetch_emails,
    classify_email_intent,
    extract_action_items,
    draft_email_reply,
    send_email,
)

# Task Management
from .tasks import (
    create_task,
    update_task,
    fetch_tasks,
    suggest_task_schedule,
    sync_external_tasks,
)

# Approval & Safety
from .approvals import (
    detect_critical_action,
    create_approval_card,
    log_action,
    validate_safe_automation,
)

# Permission & Security
from .permissions import (
    check_file_permission,
    request_directory_access,
    revoke_all_permissions,
    list_current_permissions,
    redact_pii,
)

# System Monitoring
from .system_monitoring import (
    get_system_metrics,
    monitor_app_usage,
    check_device_health,
    suggest_system_optimization,
)

# Documents & Files
from .documents import (
    list_documents,
    read_document,
    search_documents,
    cite_document,
)

# Messaging
from .messaging import (
    connect_messenger,
    fetch_messages,
    classify_message_urgency,
    draft_message_reply,
)

# Weather Monitoring
from .weather import (
    get_current_weather,
    get_weather_forecast,
    get_hourly_forecast,
    detect_weather_alerts,
    check_precipitation_forecast,
    compare_weather_change,
)

# Research & Analysis
from .research_analysis import (
    search_news,
    get_financial_data,
    analyze_trend,
    get_market_summary,
    search_research_papers,
    get_political_summary,
)

# Core business analytics
from .core import (
    search_market_data,
    calculate_financial_metrics,
    analyze_weather_impact,
    generate_report_summary,
    validate_data_quality,
)

# Statistical analysis
from .data_analysis import (
    analyze_dataset,
    calculate_statistics,
)

# Food & Recipes
from .food_recipe import (
    search_recipes,
    get_recipe_details,
    get_cooking_tips,
    find_ingredient_stores,
    suggest_ingredient_substitutes,
)

# Transport & Travel
from .transport import (
    search_flights,
    search_trains,
    search_buses,
    get_live_transit_status,
    check_flight_status,
    compare_transport_options,
)

# Web Browsing
from .web_browser import (
    browse_webpage,
    search_internet,
    extract_article_text,
    monitor_website_changes,
)

# Web Search & Content Generation (core utilities)
from .web_search import search_web, get_trending_topics
from .content_generation import generate_summary, create_recommendation

__all__ = [
    # Calendar & Scheduling
    "connect_calendar",
    "fetch_calendar_events",
    "create_calendar_event",
    "update_calendar_event",
    "suggest_focus_blocks",
    "detect_calendar_conflicts",
    # Email
    "connect_email",
    "fetch_emails",
    "classify_email_intent",
    "extract_action_items",
    "draft_email_reply",
    "send_email",
    # Tasks
    "create_task",
    "update_task",
    "fetch_tasks",
    "suggest_task_schedule",
    "sync_external_tasks",
    # Approvals
    "detect_critical_action",
    "create_approval_card",
    "log_action",
    "validate_safe_automation",
    # System Monitoring
    "get_system_metrics",
    "monitor_app_usage",
    "check_device_health",
    "suggest_system_optimization",
    # Documents
    "list_documents",
    "read_document",
    "search_documents",
    "cite_document",
    # Messaging
    "connect_messenger",
    "fetch_messages",
    "classify_message_urgency",
    "draft_message_reply",
    # Weather
    "get_current_weather",
    "get_weather_forecast",
    "get_hourly_forecast",
    "detect_weather_alerts",
    "check_precipitation_forecast",
    "compare_weather_change",
    # Research & Analysis
    "search_news",
    "get_financial_data",
    "analyze_trend",
    "get_market_summary",
    "search_research_papers",
    "get_political_summary",
    # Core business analytics
    "search_market_data",
    "calculate_financial_metrics",
    "analyze_weather_impact",
    "generate_report_summary",
    "validate_data_quality",
    # Statistical analysis
    "analyze_dataset",
    "calculate_statistics",
    # Food & Recipes
    "search_recipes",
    "get_recipe_details",
    "get_cooking_tips",
    "find_ingredient_stores",
    "suggest_ingredient_substitutes",
    # Transport
    "search_flights",
    "search_trains",
    "search_buses",
    "get_live_transit_status",
    "check_flight_status",
    "compare_transport_options",
    # Web Browsing
    "browse_webpage",
    "search_internet",
    "extract_article_text",
    "monitor_website_changes",
    # Web & Content
    "search_web",
    "get_trending_topics",
    "generate_summary",
    "create_recommendation",
]
