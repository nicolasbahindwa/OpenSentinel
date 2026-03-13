"""
OpenSentinel professional agent setup.

Loading behavior:
- Agent graph creation is deferred and cached via ``@lru_cache``.
- Tools and subagents are selected and materialized during graph creation.
- External tool clients are created only at tool invocation time.
- Memory and skills are loaded by DeepAgents middleware at runtime.
"""

from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

from deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph

from agent.backend import composite_backend
from agent.config import Config
from agent.logger import configure_logging, get_logger
from agent.middleware import (
    GuardrailsMiddleware,
    FollowupQuestionsMiddleware,
    ObservabilityMiddleware,
    RateLimitMiddleware,
    RoutingMiddleware,
)
from agent.prompt.loader import get_full_prompt
from agent.registry import get_registry

SKILL_SOURCES = ("/skills/",)


def _validate_requested_names(
    requested: Optional[tuple[str, ...]],
    available: tuple[str, ...],
    label: str,
) -> None:
    """Fail fast when an invalid tool or subagent name is requested."""
    if requested is None:
        return

    unknown = sorted(set(requested) - set(available))
    if unknown:
        raise ValueError(
            f"Unknown {label}: {unknown}. Available {label}: {list(available)}"
        )


def get_selected_tools(tool_names: Optional[tuple[str, ...]] = None):
    """
    Get selected tools (materialized during agent creation).

    Args:
        tool_names: Tuple of tool names to load. If None, loads all tools.

    Returns:
        List of materialized tool instances
    """
    registry = get_registry()
    _validate_requested_names(tool_names, registry.available_names("tool"), "tools")

    from agent.tools.lazy_loader import get_all_tools, get_tool

    if tool_names is None:
        return get_all_tools()

    tools = []
    for name in tool_names:
        tool = get_tool(name)
        if tool is None:
            raise ValueError(f"Failed to load tool '{name}'")
        tools.append(tool)
    return tools


def get_selected_subagents(
    model: Any,
    subagent_names: Optional[tuple[str, ...]] = None,
):
    """
    Get selected subagents (materialized during agent creation).

    Args:
        model: Model to use for subagents
        subagent_names: Tuple of subagent names to load. If None, loads all.

    Returns:
        List of materialized subagent instances
    """
    registry = get_registry()
    _validate_requested_names(
        subagent_names, registry.available_names("subagent"), "subagents"
    )

    from agent.subagents.lazy_loader import LazySubagentLoader

    loader = LazySubagentLoader(model)

    if subagent_names is None:
        return loader.get_all_subagents()

    if len(subagent_names) == 0:
        return []

    subagents = loader.get_subagents(*subagent_names)
    if len(subagents) != len(subagent_names):
        raise ValueError("Failed to load one or more requested subagents")
    return subagents


logger = get_logger("agent.agent", component="agent")


@lru_cache(maxsize=1)
def create_professional_agent(
    tool_names: Optional[tuple[str, ...]] = None,
    subagent_names: Optional[tuple[str, ...]] = None,
) -> CompiledStateGraph:
    """
    Create a professional OpenSentinel agent.

    Agent graph creation is deferred and cached: this runs only on first call.
    """
    configure_logging(json_output=True, log_level="INFO")
    logger.info("creating_agent", tools=tool_names, subagents=subagent_names)

    configurable = Config.from_runnable_config()

    tools = get_selected_tools(tool_names)
    subagents = get_selected_subagents(configurable.subagent_model, subagent_names)

    # create_deep_agent adds built-in middleware for memory/skills/filesystem.
    return create_deep_agent(
        model=configurable.base_model,
        name="OPENSENTINEL_PROFESSIONAL",
        system_prompt=get_full_prompt(),
        tools=tools,
        subagents=subagents,
        skills=list(SKILL_SOURCES),
        middleware=[
            GuardrailsMiddleware(judge_model=configurable.judge_model),
            RateLimitMiddleware(max_requests=30, window_seconds=60),
            RoutingMiddleware(),
            ObservabilityMiddleware(),
            FollowupQuestionsMiddleware(),
        ],
        backend=composite_backend(),
        memory=[str(Path(__file__).parent.parent / "AGENTS.md")],
        debug=True,
    )


def create_agent() -> CompiledStateGraph:
    """Create default professional agent (all tools, all subagents)."""
    return create_professional_agent()


def reset_agent_cache() -> None:
    """Clear the cached agent so next call rebuilds it."""
    create_professional_agent.cache_clear()
