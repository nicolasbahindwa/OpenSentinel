"""
Weather Strategist Subagent — LLM-driven climate business analysis.

Uses reasoning to correlate weather patterns with business opportunities
and risks across industries and locations.
"""

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from tools import (
    analyze_weather_impact,
    search_market_data,
    search_web,
    analyze_dataset,
    create_recommendation,
)

SYSTEM_PROMPT = """\
You are a climate business strategist. Your expertise:

1. Analyze weather impact on specific industries using analyze_weather_impact.
2. Use search_web to find current weather-related business trends.
3. Use search_market_data for sector-specific climate intelligence.
4. Use analyze_dataset to correlate seasonal patterns with business cycles.
5. Identify weather-tech opportunities and risks.
6. Provide location-based strategic recommendations via create_recommendation.

Focus on actionable business insights, not meteorological trivia.
"""

_model = ChatAnthropic(model="claude-sonnet-4-20250514")

_agent = create_react_agent(
    model=_model,
    tools=[analyze_weather_impact, search_market_data, search_web, analyze_dataset, create_recommendation],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_weather_strategist(task: str) -> str:
    """
    Delegate a weather-business analysis task to the climate strategist.

    The strategist uses LLM reasoning to correlate weather data with
    market opportunities and risks. Best for location-specific or
    climate-dependent business questions.

    Args:
        task: Natural-language description of the weather/climate task

    Returns:
        The strategist's analysis as a string
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Weather analysis complete — no summary produced."
