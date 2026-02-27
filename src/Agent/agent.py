"""
OpenSentinel Life Management Agent - Deep Agent orchestrator.

Architecture:
    tools/      -> Atomic, stateless @tool functions (single operations)
    skills/     -> SKILL.md instruction files
    subagents/  -> Subagent config dictionaries (not pre-created agents)
    functions/  -> Agent composition helpers (skill/tool wiring)
    agent.py    -> Main orchestrator via create_deep_agent

Built on deepagents: filesystem-native, subagent-capable, with human-in-the-loop support.
"""

from pathlib import Path
from typing import Any

from deepagents import create_deep_agent
from langgraph.checkpoint.memory import MemorySaver

from .functions import build_subagent_configs
from .llm_factory import create_llm
from .subagents import get_all_subagent_configs
from .tools import log_action

# Configuration
PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_system_prompt(mode: str = "standard") -> str:
    """
    Load modular system prompt to optimize token usage.
    """
    prompt_parts = []

    core_path = PROMPTS_DIR / "core.md"
    if core_path.exists():
        prompt_parts.append(core_path.read_text(encoding="utf-8"))

    if mode in ("standard", "full"):
        cap_path = PROMPTS_DIR / "capabilities.md"
        if cap_path.exists():
            prompt_parts.append(cap_path.read_text(encoding="utf-8"))

        safety_path = PROMPTS_DIR / "safety.md"
        if safety_path.exists():
            prompt_parts.append(safety_path.read_text(encoding="utf-8"))

    if mode == "full":
        quality_path = PROMPTS_DIR / "quality_standards.md"
        if quality_path.exists():
            prompt_parts.append(quality_path.read_text(encoding="utf-8"))

    if not prompt_parts:
        return (
            "You are OpenSentinel, a proactive AI agent for life management. "
            "You help with daily planning, research, productivity, and personal coordination. "
            "Use tools to interact with external systems and delegate to subagents for complex tasks."
        )

    return "\n\n---\n\n".join(prompt_parts)


def create_subagent_configs() -> list[dict[str, Any]]:
    """
    Build subagent configurations for create_deep_agent.

    Base configs are defined in subagents/. Skill prompt injection and shared
    tool attachment are applied by functions.agent_composition.
    """
    base_configs = get_all_subagent_configs()
    return build_subagent_configs(base_configs)


def create_agent(
    llm: Any = None,
    prompt_mode: str = "standard",
    enable_human_in_the_loop: bool = True,
) -> Any:
    """
    Create the OpenSentinel orchestrator agent.

    The supervisor does NOT receive domain-specific tools. Those belong
    exclusively to the subagents defined in create_subagent_configs().

    deepagents middleware automatically provides the supervisor with:
      - write_todos  -> planning and task decomposition
      - task()       -> delegation to named subagents
      - filesystem   -> read_file, write_file, edit_file, ls, glob, grep

    Custom tools on the supervisor are limited to cross-cutting concerns
    that don't belong to any single subagent (e.g. audit logging).

    Args:
        llm: Pre-configured LLM instance (orchestrator default is used if None)
        prompt_mode: System prompt complexity ("minimal", "standard", "full")
        enable_human_in_the_loop: Whether to require approval for sensitive operations

    Returns:
        Configured deep agent instance
    """

    model = llm if llm is not None else create_llm()

    # Supervisor gets only cross-cutting tools that aren't owned by a subagent.
    tools = [
        log_action,
    ]

    system_prompt = load_system_prompt(mode=prompt_mode)
    subagents = create_subagent_configs()

    # Human-in-the-loop configuration using interrupt_on
    # Tool names must match @tool function names exactly (case-sensitive)
    interrupt_on = {}
    if enable_human_in_the_loop:
        interrupt_on = {
            # Communication - always require approval before sending
            "send_email": True,

            # Calendar - approve before modifying commitments
            "create_calendar_event": True,
            "update_calendar_event": True,

            # Filesystem - Deep Agents built-in tools
            "write_file": True,
            "edit_file": True,
            "delete_file": {"allowed_decisions": ["approve", "reject"]},

            # Safety - approve-only for critical action escalation
            "detect_critical_action": {"allowed_decisions": ["approve"]},
        }

    # Required checkpointer for HITL
    checkpointer = MemorySaver()

    agent = create_deep_agent(
        tools=tools,
        system_prompt=system_prompt,
        model=model,
        subagents=subagents,
        interrupt_on=interrupt_on if enable_human_in_the_loop else None,
        checkpointer=checkpointer,
    )

    return agent
