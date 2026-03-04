from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph
from deepagents.middleware.skills import SkillsMiddleware

from agent.config import Config
from agent.backend import composite_backend
from agent.tools import internet_search as web_tools
from agent.tools import weather_lookup
from agent.subagents import build_subagents
from agent.middleware import (
    GuardrailsMiddleware,
    ObservabilityMiddleware,
    RateLimitMiddleware,
    RoutingMiddleware,
    SourceCitationMiddleware,
)


def create_agent() -> CompiledStateGraph:
    """Create the OpenSentinel agent with configured model and tools."""
    configurable = Config.from_runnable_config()
    subagent_specs = build_subagents(configurable.subagent_model)

    agent = create_deep_agent(
        name="OPENSENTINEL_AGENT",
        model=configurable.base_model,
        system_prompt=configurable.base_agent_prompt,
        memory=["./AGENTS.md"],
        backend=composite_backend(),
        tools=[t for t in [web_tools, weather_lookup] if t is not None],
        subagents=subagent_specs,
        middleware=[
            GuardrailsMiddleware(),
            RoutingMiddleware(),
            SourceCitationMiddleware(),
            RateLimitMiddleware(),
            ObservabilityMiddleware(),
            SkillsMiddleware(
                backend=composite_backend(),
                sources=["/skills/"]
            )
        ]
    )

    return agent


__all__ = [
    "create_agent",
]
