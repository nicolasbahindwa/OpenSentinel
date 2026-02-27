"""
Agent composition helpers.

This package keeps agent assembly logic out of agent.py:
- skill loading and prompt injection
- shared tool attachment for subagents
"""

from .agent_composition import (
    build_subagent_configs,
    load_skill_text,
    example_skill_and_tool_loading,
)

__all__ = [
    "build_subagent_configs",
    "load_skill_text",
    "example_skill_and_tool_loading",
]

