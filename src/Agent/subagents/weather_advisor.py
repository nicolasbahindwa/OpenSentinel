"""
Weather Advisor Subagent  EIntelligent weather monitoring and alerts specialist.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.weather import (
    get_current_weather,
    get_weather_forecast,
    get_hourly_forecast,
    detect_weather_alerts,
    check_precipitation_forecast,
    compare_weather_change,
)

SYSTEM_PROMPT = """\
You are a weather monitoring specialist and meteorological advisor.

Your protocol:
1. Provide morning weather briefings with current conditions and daily forecast
2. Alert user to significant weather changes (temperature swings, storms)
3. Proactive rain warnings when precipitation expected within 6 hours
4. Compare today's weather to yesterday to flag notable changes
5. Recommend appropriate clothing and preparations based on forecast

Use when to alert:
- Morning briefing: Always include weather summary
- Significant temperature change: > 5°C from yesterday
- Rain expected: Within next 6 hours with >60% probability
- Severe weather alerts: Storms, extreme temps, hazardous conditions

Output format:
- Concise weather summary (2-3 sentences)
- Key alerts and recommendations
- Today's forecast with highs/lows
- Precipitation timing if relevant
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        get_current_weather,
        get_weather_forecast,
        get_hourly_forecast,
        detect_weather_alerts,
        check_precipitation_forecast,
        compare_weather_change,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_weather_advisor(task: str) -> str:
    """
    Delegate weather monitoring and forecasting to the weather specialist.

    Use for:
    - Morning weather briefings
    - Rain/precipitation alerts
    - Significant weather change detection
    - Weather-based recommendations (clothing, planning)

    Args:
        task: Weather-related request (e.g., "Check if I need umbrella today", "Weather briefing")

    Returns:
        Weather summary with alerts and recommendations
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Weather check complete  Esee above."
