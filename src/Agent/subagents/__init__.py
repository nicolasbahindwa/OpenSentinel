"""
Subagents module — Configuration-based subagents for DeepAgents architecture.

Each subagent is defined as a configuration dictionary with:
- name: Unique identifier
- description: When to use this subagent
- system_prompt: Specialized instructions for the subagent
- tools: List of tool functions available to the subagent

Subagent configurations:
- Personal Planning: scheduling_coordinator, email_triage_specialist, task_strategist, daily_briefing_compiler
- Research & Knowledge: research_analyst, report_generator
- Life Management: weather_advisor, culinary_advisor, travel_coordinator
- System Health: system_monitor
- Safety: approval_gatekeeper
"""

# Personal Planning & Productivity
from .scheduling_coordinator import get_config as get_scheduling_coordinator_config
from .email_triage_specialist import get_config as get_email_triage_specialist_config
from .task_strategist import get_config as get_task_strategist_config
from .daily_briefing_compiler import get_config as get_daily_briefing_compiler_config

# Research & Knowledge
from .research_analyst import get_config as get_research_analyst_config
from .report_generator import get_config as get_report_generator_config

# Life Management
from .weather_advisor import get_config as get_weather_advisor_config
from .culinary_advisor import get_config as get_culinary_advisor_config
from .travel_coordinator import get_config as get_travel_coordinator_config

# System Health
from .system_monitor import get_config as get_system_monitor_config

# Safety
from .approval_gatekeeper import get_config as get_approval_gatekeeper_config


def get_all_subagent_configs():
    """Returns a list of all subagent configurations."""
    return [
        get_scheduling_coordinator_config(),
        get_email_triage_specialist_config(),
        get_task_strategist_config(),
        get_daily_briefing_compiler_config(),
        get_research_analyst_config(),
        get_report_generator_config(),
        get_weather_advisor_config(),
        get_culinary_advisor_config(),
        get_travel_coordinator_config(),
        get_system_monitor_config(),
        get_approval_gatekeeper_config(),
    ]


__all__ = [
    "get_scheduling_coordinator_config",
    "get_email_triage_specialist_config",
    "get_task_strategist_config",
    "get_daily_briefing_compiler_config",
    "get_research_analyst_config",
    "get_report_generator_config",
    "get_weather_advisor_config",
    "get_culinary_advisor_config",
    "get_travel_coordinator_config",
    "get_system_monitor_config",
    "get_approval_gatekeeper_config",
    "get_all_subagent_configs",
]
