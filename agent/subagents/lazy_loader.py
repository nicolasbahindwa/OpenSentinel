"""
Lazy subagent loader - subagents are only built when needed
"""
from typing import Any, List, Optional
from functools import lru_cache
from deepagents.middleware.subagents import SubAgent


class LazySubagentLoader:
    """
    Lazy loader for subagents - builds subagents only when accessed.

    This prevents expensive subagent initialization at startup.
    Each subagent is only built when first requested.
    """

    def __init__(self, model: Any):
        self.model = model
        self._subagents_cache = {}

    @lru_cache(maxsize=None)
    def fact_check(self) -> SubAgent:
        """Lazy load fact check subagent."""
        if "fact_check" not in self._subagents_cache:
            from .fact_check import build_fact_check_subagent
            self._subagents_cache["fact_check"] = build_fact_check_subagent(self.model)
        return self._subagents_cache["fact_check"]

    @lru_cache(maxsize=None)
    def weather(self) -> SubAgent:
        """Lazy load weather advisor subagent."""
        if "weather" not in self._subagents_cache:
            from .weather import build_weather_advisor
            self._subagents_cache["weather"] = build_weather_advisor(self.model)
        return self._subagents_cache["weather"]

    @lru_cache(maxsize=None)
    def finance(self) -> SubAgent:
        """Lazy load finance expert subagent."""
        if "finance" not in self._subagents_cache:
            from .finance import build_finance_expert
            self._subagents_cache["finance"] = build_finance_expert(self.model)
        return self._subagents_cache["finance"]

    @lru_cache(maxsize=None)
    def news(self) -> SubAgent:
        """Lazy load news curator subagent."""
        if "news" not in self._subagents_cache:
            from .news import build_news_curator
            self._subagents_cache["news"] = build_news_curator(self.model)
        return self._subagents_cache["news"]

    @lru_cache(maxsize=None)
    def morning_briefing(self) -> SubAgent:
        """Lazy load morning briefing subagent."""
        if "morning_briefing" not in self._subagents_cache:
            from .morning_briefing import build_morning_briefing
            self._subagents_cache["morning_briefing"] = build_morning_briefing(self.model)
        return self._subagents_cache["morning_briefing"]

    def get_subagent(self, name: str) -> Optional[SubAgent]:
        """
        Get a subagent by name (lazy loaded).

        Args:
            name: Name of the subagent

        Returns:
            Subagent instance or None
        """
        subagent_getter = getattr(self, name, None)
        if subagent_getter and callable(subagent_getter):
            return subagent_getter()
        return None

    def get_subagents(self, *names: str) -> List[SubAgent]:
        """
        Get multiple subagents by name.

        Args:
            *names: Names of subagents to load

        Returns:
            List of subagent instances
        """
        subagents = []
        for name in names:
            subagent = self.get_subagent(name)
            if subagent:
                subagents.append(subagent)
        return subagents

    def get_all_subagents(self) -> List[SubAgent]:
        """
        Get all subagents (lazy loaded on first access).

        Returns:
            List of all subagent instances
        """
        return [
            self.fact_check(),
            self.weather(),
            self.finance(),
            self.news(),
            self.morning_briefing(),
        ]


def create_lazy_subagent_loader(model: Any) -> LazySubagentLoader:
    """
    Create a lazy subagent loader instance.

    Args:
        model: Model to use for subagents

    Returns:
        LazySubagentLoader instance
    """
    return LazySubagentLoader(model)


def get_minimal_subagents(model: Any) -> List[SubAgent]:
    """
    Get minimal subagent set (empty by default).

    Args:
        model: Model to use

    Returns:
        Empty list - no subagents loaded initially
    """
    return []


def get_standard_subagents(model: Any) -> List[SubAgent]:
    """
    Get standard subagent set.

    Args:
        model: Model to use

    Returns:
        List with fact_check and news subagents
    """
    loader = LazySubagentLoader(model)
    return [
        loader.fact_check(),
        loader.news(),
    ]


__all__ = [
    "LazySubagentLoader",
    "create_lazy_subagent_loader",
    "get_minimal_subagents",
    "get_standard_subagents",
]
