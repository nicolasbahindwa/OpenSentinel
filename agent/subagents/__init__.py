from typing import Any

from deepagents.middleware.subagents import SubAgent

from .fact_check import build_fact_check_subagent
from .weather import build_weather_advisor
from .finance import build_finance_expert
from .news import build_news_curator
from .morning_briefing import build_morning_briefing


def build_subagents(model: Any) -> list[SubAgent]:
    """Build and return all configured subagents."""
    return [
        build_fact_check_subagent(model),
        build_weather_advisor(model),
        build_finance_expert(model),
        build_news_curator(model),
        build_morning_briefing(model),
    ]


__all__ = [
    "build_subagents",
    "build_fact_check_subagent",
    "build_weather_advisor",
    "build_finance_expert",
    "build_news_curator",
    "build_morning_briefing",
]
