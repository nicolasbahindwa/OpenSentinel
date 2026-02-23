"""
Research Specialist Subagent  ELLM-driven market research.

Uses reasoning to decide which search tools to call, how to validate
findings, and how to synthesize results. More flexible than the
deterministic research skill pipeline.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..tools import (
    search_web,
    search_market_data,
    get_trending_topics,
    validate_data_quality,
    generate_summary,
)

SYSTEM_PROMPT = """\
You are an elite market research analyst. Your protocol:

1. Use search_web and search_market_data to gather current market intelligence.
2. Use get_trending_topics to identify market trends.
3. Cross-reference multiple sources for accuracy.
4. Flag any data quality issues using validate_data_quality.
5. Summarise findings with generate_summary.
6. Structure your final answer as JSON with: sources, metrics, confidence_scores.
7. Always include TAM (Total Addressable Market), CAGR, and competitive landscape.

Return only synthesized insights  Enever raw search dumps.
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[search_web, search_market_data, get_trending_topics, validate_data_quality, generate_summary],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_researcher(task: str) -> str:
    """
    Delegate a research task to the market research specialist.

    The researcher uses LLM reasoning to decide which sources to query,
    how to validate data, and how to synthesize findings. Best for
    open-ended or exploratory research where the exact pipeline isn't
    known in advance.

    Args:
        task: Natural-language description of the research task

    Returns:
        The researcher's synthesized findings as a string
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    # Return the last AI message content
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Research complete  Eno summary produced."
