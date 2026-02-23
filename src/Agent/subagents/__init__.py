"""
Subagents module — LLM-driven specialist agents for personal productivity and life management.

Each subagent is a create_react_agent with access to relevant tools.
Subagents use reasoning to decide which tools to call and how to synthesize results.
Use subagents for open-ended tasks requiring judgment; use skills for deterministic pipelines.
"""

# Personal Planning & Productivity
from .scheduling_coordinator import delegate_to_scheduling_coordinator
from .email_triage_specialist import delegate_to_email_triage_specialist
from .approval_gatekeeper import delegate_to_approval_gatekeeper
from .task_strategist import delegate_to_task_strategist
from .daily_briefing_compiler import delegate_to_daily_briefing_compiler

# Research & Knowledge
from .research_assistant import delegate_to_research_assistant
from .general_researcher import delegate_to_general_researcher
from .report_generator import delegate_to_report_generator

# Life Management
from .weather_advisor import delegate_to_weather_advisor
from .culinary_advisor import delegate_to_culinary_advisor
from .travel_coordinator import delegate_to_travel_coordinator

__all__ = [
    # Personal Planning
    "delegate_to_scheduling_coordinator",
    "delegate_to_email_triage_specialist",
    "delegate_to_approval_gatekeeper",
    "delegate_to_task_strategist",
    "delegate_to_daily_briefing_compiler",
    # Research & Knowledge
    "delegate_to_research_assistant",
    "delegate_to_general_researcher",
    "delegate_to_report_generator",
    # Life Management
    "delegate_to_weather_advisor",
    "delegate_to_culinary_advisor",
    "delegate_to_travel_coordinator",
]
