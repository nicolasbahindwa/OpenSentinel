from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph
from deepagents.middleware.skills import SkillsMiddleware

from config import Config
from backend import composite_backend
from tools import internet_search as web_tools
from subagents import build_subagents


def create_agent() -> CompiledStateGraph:
    """Create the OpenSentinel agent with configured model and tools."""
    configurable = Config.from_runnable_config()
    subagent_specs = build_subagents(configurable.base_model)

    agent = create_deep_agent(
        name="OPENSENTINEL_AGENT",
        model=configurable.base_model,
        system_prompt=configurable.base_agent_prompt,
        memory=["./AGENTS.md"],
        backend=composite_backend(),
        tools=[web_tools],
        subagents=subagent_specs,
        middleware=[
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