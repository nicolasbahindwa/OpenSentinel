"""
Subagent composition utilities.

Keeps skill and tool wiring separate from agent.py so the orchestrator file
stays focused on agent construction.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..tools import universal_search, log_to_supervisor

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

# Map subagent name -> skill folders under src/Agent/skills/<skill-name>/SKILL.md
SUBAGENT_SKILL_MAP: dict[str, list[str]] = {
    "approval_gatekeeper": ["approval-workflow"],
    "daily_briefing_compiler": ["daily-briefing"],
    "email_triage_specialist": ["email-triage", "email-processing", "task-extraction"],
    "report_generator": ["report-generation", "document-research"],
    "research_analyst": ["research", "financial-analysis", "document-research"],
    "scheduling_coordinator": ["smart-scheduling"],
    "system_monitor": ["system-health-check"],
    "task_strategist": ["task-extraction"],
}

SHARED_SUBAGENT_TOOLS = [universal_search, log_to_supervisor]


def load_skill_text(skill_name: str) -> str:
    """Load src/Agent/skills/<skill_name>/SKILL.md if present."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""


def _inject_skills_into_prompt(config: dict[str, Any]) -> dict[str, Any]:
    """Append mapped skill text to a subagent's system prompt."""
    subagent_name = config.get("name", "")
    mapped_skills = SUBAGENT_SKILL_MAP.get(subagent_name, [])
    if not mapped_skills:
        return config

    skill_chunks: list[str] = []
    for skill_name in mapped_skills:
        skill_text = load_skill_text(skill_name).strip()
        if skill_text:
            skill_chunks.append(f"[Skill: {skill_name}]\n{skill_text}")

    if not skill_chunks:
        return config

    updated = dict(config)
    current_prompt = updated.get("system_prompt", "")
    updated["system_prompt"] = (
        f"{current_prompt}\n\n"
        "Follow these domain skills when relevant:\n\n"
        f"{'\n\n'.join(skill_chunks)}"
    )
    return updated


def _attach_shared_tools(config: dict[str, Any]) -> dict[str, Any]:
    """Ensure every subagent has shared cross-cutting tools once."""
    updated = dict(config)
    current_tools = list(updated.get("tools", []))

    by_name: dict[str, Any] = {}
    for tool_fn in current_tools + SHARED_SUBAGENT_TOOLS:
        name = getattr(tool_fn, "name", None) or getattr(tool_fn, "__name__", repr(tool_fn))
        by_name[name] = tool_fn

    updated["tools"] = list(by_name.values())
    return updated


def build_subagent_configs(base_configs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Build final subagent configs by injecting mapped skills and shared tools.
    """
    final_configs: list[dict[str, Any]] = []
    for config in base_configs:
        updated = _inject_skills_into_prompt(config)
        updated = _attach_shared_tools(updated)
        final_configs.append(updated)
    return final_configs


def example_skill_and_tool_loading() -> dict[str, Any]:
    """
    Example output describing how skill and shared tool loading is applied.
    """
    return {
        "skills_dir": str(SKILLS_DIR),
        "shared_tools": [t.__name__ for t in SHARED_SUBAGENT_TOOLS],
        "mapped_subagents": sorted(SUBAGENT_SKILL_MAP.keys()),
        "note": "Use build_subagent_configs(get_all_subagent_configs()) in agent.py.",
    }

