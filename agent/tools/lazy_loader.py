"""Lazy tool loader — driven by the central registry.

Tools are only instantiated when first accessed.  The registry is the
single source of truth for what tools exist; this module handles caching
and on-demand instantiation via the factory import paths stored there.
"""

from __future__ import annotations

from typing import Optional

from langchain_core.tools import BaseTool

from agent.registry import get_registry


class LazyToolLoader:
    """Instantiates tools on demand using registry factory paths."""

    def __init__(self) -> None:
        self._cache: dict[str, BaseTool] = {}

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name (lazy loaded from registry)."""
        if name in self._cache:
            return self._cache[name]

        registry = get_registry()
        tool = registry.create_tool(name)
        if tool is not None:
            self._cache[name] = tool
        return tool

    def get_tools(self, *names: str) -> list[BaseTool]:
        """Get multiple tools by name."""
        tools = []
        for name in names:
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)
        return tools

    def get_all_tools(self) -> list[BaseTool]:
        """Get all registered tools (lazy loaded on first access)."""
        registry = get_registry()
        tools = []
        for entry in registry.list_all(kind="tool"):
            tool = self.get_tool(entry.name)
            if tool:
                tools.append(tool)
        return tools


# Global lazy loader instance
_tool_loader = LazyToolLoader()


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Get a single tool by name."""
    return _tool_loader.get_tool(tool_name)


def get_tools(*tool_names: str) -> list[BaseTool]:
    """Get multiple tools by name."""
    return _tool_loader.get_tools(*tool_names)


def get_minimal_tools() -> list[BaseTool]:
    """Get minimal toolset for basic operation."""
    return _tool_loader.get_tools("internet_search")


def get_all_tools() -> list[BaseTool]:
    """Get all available tools."""
    return _tool_loader.get_all_tools()


__all__ = [
    "LazyToolLoader",
    "get_tool",
    "get_tools",
    "get_minimal_tools",
    "get_all_tools",
]
