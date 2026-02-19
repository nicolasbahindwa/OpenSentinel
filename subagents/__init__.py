"""
Subagents module — LLM-driven specialist agents.

Each subagent is a create_react_agent instance with its own tools and
system prompt, wrapped as a @tool so the orchestrator can delegate to it.

Unlike skills (deterministic pipelines), subagents use LLM reasoning to
decide which tools to call and in what order.

    tools  →  skills  →  subagents
    atomic    pipeline    reasoning
"""

from .research_specialist import delegate_to_researcher
from .financial_analyst import delegate_to_financial_analyst
from .weather_strategist import delegate_to_weather_strategist
from .report_compiler import delegate_to_report_compiler

__all__ = [
    "delegate_to_researcher",
    "delegate_to_financial_analyst",
    "delegate_to_weather_strategist",
    "delegate_to_report_compiler",
]
