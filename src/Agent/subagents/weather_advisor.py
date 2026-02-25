"""
Weather Advisor Subagent Configuration

Analyzes weather patterns and suggests preparations.
"""

from ..tools import (
    get_current_weather,
    get_weather_forecast,
    get_hourly_forecast,
    detect_weather_alerts,
    check_precipitation_forecast,
    compare_weather_change,
)


def get_config():
    """Returns the weather advisor subagent configuration."""
    return {
        "name": "weather_advisor",
        "description": "Analyzes weather patterns and suggests preparations. Use for weather-related planning.",
        "system_prompt": (
            "You are a weather planning specialist. Analyze forecasts, detect alerts, and suggest "
            "preparations for weather conditions. Consider travel impacts, outdoor activities, and safety."
        ),
        "tools": [
            get_current_weather,
            get_weather_forecast,
            get_hourly_forecast,
            detect_weather_alerts,
            check_precipitation_forecast,
            compare_weather_change,
        ],
    }
