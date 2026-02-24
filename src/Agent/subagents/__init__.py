"""
Subagents module — Configuration-based subagents for DeepAgents architecture.

With DeepAgents, subagents are defined as configuration dictionaries in agent.py,
not as pre-instantiated create_react_agent instances. This module is kept for
organizational purposes and potential future extensions.

Subagent configurations include:
- Personal Planning: scheduling_coordinator, email_triage_specialist, task_strategist, daily_briefing_compiler
- Research & Knowledge: research_analyst, report_generator
- Life Management: weather_advisor, culinary_advisor, travel_coordinator
- Safety: approval_gatekeeper

All subagent configurations are defined in ../agent.py:create_subagent_configs()
"""

__all__ = []
