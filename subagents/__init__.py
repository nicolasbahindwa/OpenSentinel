from typing import Any

from deepagents.middleware.subagents import SubAgent

from .fact_check import build_fact_check_subagent


def build_subagents(model: Any) -> list[SubAgent]:
    """Build and return all configured subagents."""
    return [
        build_fact_check_subagent(model),
    ]


__all__ = [
    "build_subagents",
    "build_fact_check_subagent",
]