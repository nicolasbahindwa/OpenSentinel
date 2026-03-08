"""
Lazy tool loader - tools are only instantiated when first used
"""
from typing import Optional
from functools import cached_property
from langchain_core.tools import BaseTool


class LazyToolLoader:
    """
    Lazy loader for tools - instantiates tools only when accessed.

    This prevents expensive tool initialization at import time.
    """

    def __init__(self):
        self._tools_cache = {}

    @cached_property
    def internet_search(self) -> BaseTool:
        """Lazy load internet search tool."""
        if "internet_search" not in self._tools_cache:
            from .internet_search import TavilySearchTool
            self._tools_cache["internet_search"] = TavilySearchTool()

        return self._tools_cache["internet_search"]

    @cached_property
    def weather_lookup(self) -> BaseTool:
        """Lazy load weather lookup tool (no API key required - uses free Open-Meteo API)."""
        if "weather_lookup" not in self._tools_cache:
            from .weather import WeatherLookupTool

            # No API key needed - Open-Meteo is free
            self._tools_cache["weather_lookup"] = WeatherLookupTool()

        return self._tools_cache["weather_lookup"]

    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """
        Get a tool by name (lazy loaded).

        Args:
            tool_name: Name of the tool to load

        Returns:
            Tool instance or None if not found
        """
        tool_getter = getattr(self, tool_name, None)
        if tool_getter:
            return tool_getter
        return None

    def get_tools(self, *tool_names: str) -> list[BaseTool]:
        """
        Get multiple tools by name.

        Args:
            *tool_names: Names of tools to load

        Returns:
            List of tool instances
        """
        tools = []
        for name in tool_names:
            tool = self.get_tool(name)
            if tool:
                tools.append(tool)
        return tools

    def get_all_tools(self) -> list[BaseTool]:
        """
        Get all available tools (lazy loaded on first access).

        Returns:
            List of all tool instances
        """
        return [
            self.internet_search,
            self.weather_lookup,
        ]


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
    return [_tool_loader.internet_search]


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
