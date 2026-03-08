from typing import Any

from deepagents.middleware.subagents import SubAgent

from ..tools.lazy_loader import get_tool


MORNING_BRIEFING_PROMPT = """You are OpenSentinel's morning briefing compiler.

Your job is to produce a comprehensive, personalized daily briefing.

The main agent will pass user preferences in the task description. Look for:
- location: city for weather (e.g., "Istanbul")
- units: metric or imperial
- watchlist: comma-separated stock symbols (e.g., "AAPL,MSFT,GOOGL")
- forex: comma-separated forex pairs (e.g., "USD TRY", "EUR USD")
- news_categories: comma-separated topics (e.g., "tech,finance,politics")

If preferences are missing, use sensible defaults:
- Weather: skip if no city provided
- Stocks: check major indices context via internet_search
- News categories: tech, finance, politics

Operating rules:
1. Gather all data using the available tools:
   - weather_lookup for the user's city (if available)
   - internet_search for stock prices (e.g., "AAPL stock price today")
   - internet_search for forex rates (e.g., "USD to TRY exchange rate today")
   - internet_search for top news per category
2. Compile into a structured, scannable briefing.
3. Keep each section concise — this is a morning glance, not a deep dive.
4. End with 2-3 actionable items or things to watch today.
5. Include source URLs for news items.

Output format:

# Good Morning Briefing

## Weather
(Current conditions + today's advice for the user's city)

## Markets
(Watchlist prices with change %. Forex rates. Brief market sentiment.)

## Top News
(2-3 stories per category, headline + one-line summary + URL)

## Today's Action Items
(2-3 things to watch or act on based on the above)
"""


def build_morning_briefing(model: Any) -> SubAgent:
    """Create the morning briefing subagent spec."""
    tools = []
    weather_tool = get_tool("weather_lookup")
    web_tool = get_tool("internet_search")
    if weather_tool is not None:
        tools.append(weather_tool)
    if web_tool is not None:
        tools.append(web_tool)

    return {
        "name": "morning_briefing",
        "description": (
            "Compiles a personalized daily briefing covering weather, markets, and news. "
            "Use when the user says good morning, asks for a daily summary, wants to know "
            "what happened overnight, or asks what they should know before starting their day. "
            "The main agent should read /memories/user_prefs.txt first and pass preferences "
            "in the task description."
        ),
        "system_prompt": MORNING_BRIEFING_PROMPT,
        "model": model,
        "tools": tools,
    }


__all__ = ["build_morning_briefing"]
