"""Tool Search tool for OpenSentinel.

A meta-tool that lets the agent discover available tools and subagents
by querying the central registry.
"""

from __future__ import annotations

from typing import ClassVar, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agent.registry import ToolEntry, ToolRegistry, get_registry


class ToolSearchInput(BaseModel):
    query: str = Field(
        ...,
        min_length=1,
        description="What capability you are looking for (e.g. 'weather', 'search files', 'stock prices').",
    )
    kind: str = Field(
        default="",
        description="Filter by kind: 'tool', 'subagent', or empty for all.",
    )


class ToolSearchTool(BaseTool):
    name: str = "tool_search"
    description: str = (
        "Discover available tools and subagents by searching the registry. "
        "Use this FIRST when you're unsure which tool or subagent to use for a task. "
        "Returns matching capabilities with descriptions, parameters, and usage examples.\n\n"
        "Examples:\n"
        '- Find weather tools: query="weather forecast"\n'
        '- Find file tools: query="read desktop files"\n'
        '- List all subagents: query="all", kind="subagent"\n'
        '- Find financial tools: query="stock price exchange rate"'
    )
    args_schema: Type[BaseModel] = ToolSearchInput
    handle_tool_error: bool = True

    _registry: ToolRegistry

    MAX_RESULTS: ClassVar[int] = 10

    def __init__(self, registry: ToolRegistry | None = None, **kwargs):
        super().__init__(**kwargs)
        self._registry = registry or get_registry()

    def _format_entry(self, entry: ToolEntry) -> str:
        lines = [
            f"[{entry.kind.upper()}] {entry.label}",
            f"  Category: {entry.category}",
            f"  Description: {entry.description}",
        ]
        if entry.parameters:
            lines.append(f"  Parameters: {entry.parameters}")
        if entry.examples:
            lines.append("  Usage examples:")
            for ex in entry.examples:
                lines.append(f"    - {ex}")
        return "\n".join(lines)

    def _run(self, query: str, kind: str = "") -> str:
        kind = kind.lower().strip()
        if kind and kind not in ("tool", "subagent"):
            kind = ""

        # Special: list all
        if query.lower().strip() in ("all", "list", "*"):
            entries = self._registry.list_all(kind=kind)
        else:
            entries = self._registry.search(query, kind=kind)

        if not entries:
            return (
                f"No tools or subagents found matching '{query}'. "
                "Try broader keywords or query='all' to see everything."
            )

        entries = entries[: self.MAX_RESULTS]
        header = f"Found {len(entries)} matching {'items' if not kind else kind + 's'}:\n"
        body = "\n\n".join(self._format_entry(e) for e in entries)
        return header + body

    async def _arun(self, query: str, kind: str = "") -> str:
        return self._run(query, kind)


__all__ = ["ToolSearchTool"]
