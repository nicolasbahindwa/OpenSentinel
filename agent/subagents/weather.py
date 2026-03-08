from typing import Any

from deepagents.middleware.subagents import SubAgent

from ..tools.lazy_loader import get_tool


WEATHER_ADVISOR_PROMPT = """You are OpenSentinel's weather advisor.

Your job is to provide practical, actionable weather intelligence.

Operating rules:
1. Use weather_lookup to get current conditions and the 5-day forecast for the requested city.
2. If no city is specified, check whether the task description includes a user preference for location.
3. Analyze the data and provide practical advice:
   - Clothing recommendations (jacket, umbrella, sunscreen, layers)
   - Outdoor activity suitability (good for running, avoid cycling, etc.)
   - Travel warnings if severe weather is expected
   - Temperature trends over the coming days
4. Use internet_search for severe weather alerts or unusual conditions.
5. Always state the city and units used.
6. Be concise but helpful.

Output format:
- Current Conditions (brief)
- Today's Advice (practical, actionable)
- 5-Day Outlook (trends, key days to watch)
- Alerts (if any severe weather)
"""


def build_weather_advisor(model: Any) -> SubAgent:
    """Create the weather advisor subagent spec."""
    tools = []
    weather_tool = get_tool("weather_lookup")
    web_tool = get_tool("internet_search")
    if weather_tool is not None:
        tools.append(weather_tool)
    if web_tool is not None:
        tools.append(web_tool)

    return {
        "name": "weather_advisor",
        "description": (
            "Provides weather forecasts with practical advice (clothing, activities, travel). "
            "Use when the user asks about weather, temperature, forecast, rain, or outdoor plans."
        ),
        "system_prompt": WEATHER_ADVISOR_PROMPT,
        "model": model,
        "tools": tools,
    }


__all__ = ["build_weather_advisor"]
