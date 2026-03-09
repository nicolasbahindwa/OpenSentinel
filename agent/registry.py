"""Capability registry for OpenSentinel.

Single source of truth for all tools and subagents.  Each entry stores
discovery metadata (for ``tool_search``) AND a factory import path (for
lazy instantiation).  Adding a new capability means one ``register()``
call — the loaders and search tool pick it up automatically.
"""

from __future__ import annotations

import importlib
import re
from dataclasses import dataclass, field
from typing import Any


# ============================================================================
# Registry data model
# ============================================================================


@dataclass
class ToolEntry:
    """Metadata for a single registered tool or subagent."""

    name: str  # Code-level key (used by loaders / AVAILABLE_*)
    kind: str  # "tool" or "subagent"
    description: str
    category: str  # e.g. "search", "weather", "files", "finance"
    factory: str = ""  # Import path — "module.path:ClassName" or "module.path:builder_func"
    display_name: str = ""  # Model-facing name (defaults to name if empty)
    keywords: list[str] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    parameters: str = ""  # brief param summary

    @property
    def label(self) -> str:
        """Name shown to the model / in search results."""
        return self.display_name or self.name


class ToolRegistry:
    """Central catalogue of tools and subagents."""

    def __init__(self) -> None:
        self._entries: dict[str, ToolEntry] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(self, entry: ToolEntry) -> None:
        self._entries[entry.name] = entry

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def search(self, query: str, kind: str = "") -> list[ToolEntry]:
        """Search entries by keyword match against name, description, keywords, category."""
        tokens = re.findall(r"\w+", query.lower())

        results: list[tuple[int, ToolEntry]] = []
        for entry in self._entries.values():
            if kind and entry.kind != kind:
                continue

            searchable = " ".join([
                entry.name,
                entry.label,
                entry.description,
                entry.category,
                " ".join(entry.keywords),
            ]).lower()

            score = 0
            for token in tokens:
                if token in searchable:
                    score += 1
                if token == entry.name or token == entry.label or token == entry.category:
                    score += 2

            if score > 0:
                results.append((score, entry))

        results.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in results]

    def list_all(self, kind: str = "") -> list[ToolEntry]:
        entries = list(self._entries.values())
        if kind:
            entries = [e for e in entries if e.kind == kind]
        return entries

    def get(self, name: str) -> ToolEntry | None:
        return self._entries.get(name)

    def available_names(self, kind: str) -> tuple[str, ...]:
        """Return a tuple of registered names for a given kind."""
        return tuple(e.name for e in self._entries.values() if e.kind == kind)

    # ------------------------------------------------------------------
    # Factory instantiation
    # ------------------------------------------------------------------

    @staticmethod
    def _import_factory(factory_path: str) -> Any:
        """Import and return the class/function from 'module.path:Name'."""
        module_path, attr_name = factory_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)

    def create_tool(self, name: str) -> Any | None:
        """Instantiate a tool by name. Returns BaseTool instance or None."""
        entry = self._entries.get(name)
        if not entry or entry.kind != "tool" or not entry.factory:
            return None
        cls = self._import_factory(entry.factory)
        return cls()

    def create_subagent(self, name: str, model: Any) -> Any | None:
        """Build a subagent by name. Returns SubAgent dict or None."""
        entry = self._entries.get(name)
        if not entry or entry.kind != "subagent" or not entry.factory:
            return None
        builder = self._import_factory(entry.factory)
        return builder(model)


# ============================================================================
# Global registry
# ============================================================================

_registry = ToolRegistry()


def get_registry() -> ToolRegistry:
    """Return the global tool registry."""
    return _registry


# ============================================================================
# Built-in registrations
# ============================================================================


def _register_builtins() -> None:
    """Register all built-in tools and subagents."""

    # ----- Tools -----

    _registry.register(ToolEntry(
        name="tool_search",
        kind="tool",
        description="Discover available tools and subagents by searching the registry.",
        category="discovery",
        factory="agent.tools.tool_search:ToolSearchTool",
        keywords=["search", "find", "discover", "tool", "subagent", "capability"],
        examples=[
            'query="weather forecast"',
            'query="all", kind="subagent"',
        ],
        parameters="query (required), kind (tool|subagent|empty)",
    ))

    _registry.register(ToolEntry(
        name="internet_search",
        kind="tool",
        description=(
            "Search the internet for current, real-time information including "
            "news, facts, statistics, and any post-cutoff data."
        ),
        category="search",
        factory="agent.tools.internet_search:TavilySearchTool",
        keywords=["search", "web", "news", "lookup", "find", "latest", "current", "google"],
        examples=[
            'query="latest AI regulation news", max_results=5',
            'query="population of Japan 2025", max_results=3',
            'query="AAPL stock price", search_depth="advanced"',
        ],
        parameters="query (required), max_results (1-20, default 5), search_depth (basic|advanced)",
    ))

    _registry.register(ToolEntry(
        name="weather_lookup",
        kind="tool",
        description=(
            "Get current weather conditions and 3-day forecast for any location. "
            "Free Open-Meteo API, no API key required."
        ),
        category="weather",
        factory="agent.tools.weather:WeatherLookupTool",
        keywords=["weather", "forecast", "temperature", "rain", "wind", "humidity", "outdoor"],
        examples=[
            'location="Istanbul", units="metric"',
            'location="New York", units="imperial"',
            'location="Tokyo"',
        ],
        parameters='location (required), units ("metric"|"imperial", default "metric")',
    ))

    _registry.register(ToolEntry(
        name="file_browser",
        kind="tool",
        description=(
            "Browse and manage files on the user's local computer. "
            "Supports list, read, search, create, edit, and move operations. "
            "Restricted to ~/Desktop, ~/Documents, ~/Downloads."
        ),
        category="files",
        factory="agent.tools.file_browser:FileBrowserTool",
        keywords=[
            "file", "folder", "desktop", "documents", "downloads",
            "read", "create", "edit", "move", "rename", "search", "list",
        ],
        examples=[
            'action="list", path="~/Desktop"',
            'action="read", path="~/Documents/report.txt"',
            'action="search", path="~/Documents", pattern="*.pdf"',
            'action="create_file", path="~/Documents/notes.txt", content="Hello"',
            'action="move", path="~/Desktop/file.txt", destination="~/Documents"',
        ],
        parameters=(
            "action (list|read|search|create_folder|create_file|edit_file|move), "
            "path, pattern, content, destination, confirm (bool), max_results"
        ),
    ))

    _registry.register(ToolEntry(
        name="system_status",
        kind="tool",
        description=(
            "Check system status including CPU, memory, disk, network, and running processes. "
            "All operations are read-only and use direct Python APIs (no shell commands)."
        ),
        category="system",
        factory="agent.tools.system_monitoring:SystemStatusTool",
        keywords=[
            "system", "cpu", "memory", "ram", "disk", "network",
            "processes", "monitor", "status", "performance", "health",
        ],
        examples=[
            'category="all"',
            'category="cpu"',
            'category="memory"',
            'category="disk"',
            'category="processes", limit=20',
        ],
        parameters='category (all|cpu|memory|disk|network|processes|os, default "all"), limit (1-100, default 10)',
    ))

    # ----- Subagents -----
    # name = loader key (used by agent_professional.py)
    # display_name = SubAgent name (what the model sees via the task tool)

    _registry.register(ToolEntry(
        name="fact_check",
        kind="subagent",
        display_name="fact_checker",
        description=(
            "Verifies factual claims using web evidence and returns a verdict with sources. "
            "Use for controversial topics, medical/legal/financial claims, or conflicting information."
        ),
        category="verification",
        factory="agent.subagents.fact_check:build_fact_check_subagent",
        keywords=["fact", "check", "verify", "claim", "true", "false", "evidence", "source"],
        examples=[
            'subagent_type="fact_checker", prompt="Verify: The Eiffel Tower is 330 meters tall"',
            'subagent_type="fact_checker", prompt="Fact-check: Japan has the oldest population"',
        ],
    ))

    _registry.register(ToolEntry(
        name="weather",
        kind="subagent",
        display_name="weather_advisor",
        description=(
            "Provides weather forecasts with practical advice on clothing, activities, and travel. "
            "Goes beyond raw data to give actionable recommendations."
        ),
        category="weather",
        factory="agent.subagents.weather:build_weather_advisor",
        keywords=["weather", "forecast", "clothing", "umbrella", "outdoor", "travel", "advisory"],
        examples=[
            'subagent_type="weather_advisor", prompt="Weather advice for Istanbul today, '
            'I plan to walk around the city"',
        ],
    ))

    _registry.register(ToolEntry(
        name="finance",
        kind="subagent",
        display_name="finance_expert",
        description=(
            "Analyzes stocks, forex, and crypto with market context and investment perspective. "
            "Always includes risk disclaimers."
        ),
        category="finance",
        factory="agent.subagents.finance:build_finance_expert",
        keywords=[
            "stock", "market", "forex", "dollar", "exchange", "rate",
            "crypto", "investment", "portfolio", "AAPL", "price",
        ],
        examples=[
            'subagent_type="finance_expert", prompt="Analyze AAPL and MSFT performance this week"',
            'subagent_type="finance_expert", prompt="What is the current USD/TRY exchange rate?"',
        ],
    ))

    _registry.register(ToolEntry(
        name="news",
        kind="subagent",
        display_name="news_curator",
        description=(
            "Curates top news across tech, IT, finance, and politics. "
            "Returns a structured digest ranked by impact with source URLs."
        ),
        category="news",
        factory="agent.subagents.news:build_news_curator",
        keywords=["news", "headlines", "current events", "today", "happening", "tech", "politics"],
        examples=[
            'subagent_type="news_curator", prompt="Top tech and AI news today"',
            'subagent_type="news_curator", prompt="What happened in global politics this week?"',
        ],
    ))

    _registry.register(ToolEntry(
        name="morning_briefing",
        kind="subagent",
        display_name="morning_briefing",
        description=(
            "Compiles a personalized daily briefing covering weather, markets, and news. "
            "Read /memories/user_prefs.txt first and pass preferences in the task description."
        ),
        category="briefing",
        factory="agent.subagents.morning_briefing:build_morning_briefing",
        keywords=[
            "morning", "briefing", "daily", "summary", "good morning",
            "start my day", "overnight", "digest",
        ],
        examples=[
            'subagent_type="morning_briefing", prompt="Daily briefing. User prefs: '
            'location=Istanbul, units=metric, watchlist=AAPL,MSFT, '
            'news_categories=tech,finance"',
        ],
    ))


# Auto-register on import
_register_builtins()


__all__ = ["ToolRegistry", "ToolEntry", "get_registry"]
