"""Lazy subagent loader — driven by the central registry.

Subagents are only built when first accessed.  The registry is the
single source of truth for what subagents exist; this module handles
caching and on-demand instantiation via the factory import paths.
"""

from __future__ import annotations

from typing import Any, List, Optional

from deepagents.middleware.subagents import SubAgent

from agent.registry import get_registry


class LazySubagentLoader:
    """Builds subagents on demand using registry factory paths."""

    def __init__(self, model: Any) -> None:
        self.model = model
        self._cache: dict[str, SubAgent] = {}

    def get_subagent(self, name: str) -> Optional[SubAgent]:
        """Get a subagent by name (lazy loaded from registry)."""
        if name in self._cache:
            return self._cache[name]

        registry = get_registry()
        subagent = registry.create_subagent(name, self.model)
        if subagent is not None:
            self._cache[name] = subagent
        return subagent

    def get_subagents(self, *names: str) -> List[SubAgent]:
        """Get multiple subagents by name."""
        subagents = []
        for name in names:
            subagent = self.get_subagent(name)
            if subagent:
                subagents.append(subagent)
        return subagents

    def get_all_subagents(self) -> List[SubAgent]:
        """Get all registered subagents (lazy loaded on first access)."""
        registry = get_registry()
        subagents = []
        for entry in registry.list_all(kind="subagent"):
            subagent = self.get_subagent(entry.name)
            if subagent:
                subagents.append(subagent)
        return subagents


def create_lazy_subagent_loader(model: Any) -> LazySubagentLoader:
    """Create a lazy subagent loader instance."""
    return LazySubagentLoader(model)


def get_minimal_subagents(model: Any) -> List[SubAgent]:
    """Get minimal subagent set (empty by default)."""
    return []


def get_standard_subagents(model: Any) -> List[SubAgent]:
    """Get standard subagent set (fact_check and news)."""
    loader = LazySubagentLoader(model)
    return loader.get_subagents("fact_check", "news")


__all__ = [
    "LazySubagentLoader",
    "create_lazy_subagent_loader",
    "get_minimal_subagents",
    "get_standard_subagents",
]
