"""
Business Strategy Agent — Deep Agent orchestrator.

Architecture:
    tools/      → Atomic, stateless @tool functions   (single operations)
    skills/     → SKILL.md instruction files           (multi-step pipelines)
    subagents/  → LLM-driven specialist agents         (reasoning, flexible)
    agent.py    → Main orchestrator via create_deep_agent

Skills are loaded as SKILL.md files (Agent Skills standard). At startup the
agent reads only the frontmatter (name + description). The full instructions
are loaded on-demand when the agent decides a skill is relevant — keeping the
context window small.
"""

import asyncio
import json
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain.chat_models import init_chat_model
from deepagents import create_deep_agent

# ── Atomic tools ─────────────────────────────────────────────────────
from tools import (
    search_web,
    get_trending_topics,
    search_market_data,
    analyze_dataset,
    calculate_statistics,
    calculate_financial_metrics,
    analyze_weather_impact,
    generate_report_summary,
    generate_summary,
    create_recommendation,
    validate_data_quality,
    compose_email,
    classify_email,
)

# ── Subagents (LLM-driven specialists) ──────────────────────────────
from subagents import (
    delegate_to_researcher,
    delegate_to_financial_analyst,
    delegate_to_weather_strategist,
    delegate_to_report_compiler,
)

# ── Paths ────────────────────────────────────────────────────────────
SKILLS_DIR = Path(__file__).parent / "skills"

# ── System prompt ────────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a Senior Business Strategy Orchestrator.

You have three tiers of capabilities — choose the right level for each task:

## 1. SKILLS  (multi-step pipelines — loaded from SKILL.md)
Skills are activated automatically when your task matches their description.
Each skill provides step-by-step instructions for orchestrating tools.
Available skills: research, financial-analysis, report-generation,
email-processing.

## 2. SUBAGENTS  (LLM reasoning — flexible & adaptive)
Delegate here when the task is open-ended or needs judgment:
  - delegate_to_researcher         → Exploratory market research
  - delegate_to_financial_analyst  → Nuanced financial questions
  - delegate_to_weather_strategist → Climate-business correlation analysis
  - delegate_to_report_compiler    → Polish raw findings into executive reports

## 3. RAW TOOLS  (atomic operations — when you just need one thing)
Use individual tools only for single, specific data points.

## Decision Rules
- Prefer SKILLS when the task fits a known pipeline.
- Use SUBAGENTS for open-ended tasks requiring reasoning.
- Use RAW TOOLS only for quick, one-off lookups.
- For complex requests: break into subtasks, handle each with the right tier,
  then synthesize.

## Quality Standards
- Verify data sources and confidence scores.
- Ensure financial projections include sensitivity analysis.
- Provide actionable, specific recommendations.
- Structure outputs for C-suite readability.
"""


# ── Agent factory ────────────────────────────────────────────────────
def create_agent(model_name: str = "claude-sonnet-4-20250514"):
    """Create the orchestrator agent with tools, skills, and subagents."""

    try:
        model = ChatAnthropic(model=model_name)
    except Exception:
        model = init_chat_model(f"anthropic:{model_name}")

    # All atomic tools + subagent delegation tools
    all_tools = [
        # Atomic tools
        search_web,
        get_trending_topics,
        search_market_data,
        analyze_dataset,
        calculate_statistics,
        calculate_financial_metrics,
        analyze_weather_impact,
        generate_report_summary,
        generate_summary,
        create_recommendation,
        validate_data_quality,
        compose_email,
        classify_email,
        # Subagent delegation
        delegate_to_researcher,
        delegate_to_financial_analyst,
        delegate_to_weather_strategist,
        delegate_to_report_compiler,
    ]

    # Skill directories (each contains a SKILL.md)
    skill_paths = [
        str(SKILLS_DIR / "research"),
        str(SKILLS_DIR / "financial-analysis"),
        str(SKILLS_DIR / "report-generation"),
        str(SKILLS_DIR / "email-processing"),
    ]

    agent = create_deep_agent(
        model=model,
        tools=all_tools,
        skills=skill_paths,
        system_prompt=SYSTEM_PROMPT,
        debug=True,
    )

    return agent


# ── Execution ────────────────────────────────────────────────────────
async def run_analysis(query: str):
    """Execute a business analysis query."""
    agent = create_agent()

    print(f"Starting analysis: {query}")
    print("=" * 60)

    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": query}]}
    )

    # Print the final assistant response
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            print("\nFinal Response:")
            print("=" * 60)
            print(msg.content)
            break

    return result


if __name__ == "__main__":
    query = "Analyze startup profitability in Tokyo weather tech market"
    asyncio.run(run_analysis(query))
