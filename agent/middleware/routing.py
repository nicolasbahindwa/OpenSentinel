"""Intent-based routing middleware for OpenSentinel."""

from __future__ import annotations

import re
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import HumanMessage, SystemMessage
from typing_extensions import override


def _content_to_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for block in content:
            if isinstance(block, str):
                chunks.append(block)
                continue
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return str(content)


class RoutingMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Add lightweight route hints and prioritize relevant tools."""

    def __init__(self) -> None:
        super().__init__()
        self._routes = [
            (
                "morning_briefing",
                re.compile(r"\b(good morning|morning briefing|daily briefing|daily summary)\b", re.I),
                ["weather_lookup", "internet_search"],
                "Prefer delegating to morning_briefing when user asks for a daily overview.",
            ),
            (
                "weather",
                re.compile(r"\b(weather|forecast|temperature|rain|snow|wind|humidity)\b", re.I),
                ["weather_lookup", "internet_search"],
                "Prefer weather_advisor for planning-heavy weather requests.",
            ),
            (
                "finance",
                re.compile(
                    r"\b(stock|stocks|share price|ticker|AAPL|MSFT|GOOGL|TSLA"
                    r"|forex|exchange rate|currency convert"
                    r"|crypto|bitcoin|ethereum|btc|eth"
                    r"|market|invest|portfolio|dividend)\b",
                    re.I,
                ),
                ["yahoo_finance", "crypto", "currency", "internet_search"],
                "Use yahoo_finance for stock quotes and company data, crypto for cryptocurrency data, "
                "currency for exchange rates and conversion. Prefer finance_expert for analysis.",
            ),
            (
                "email",
                re.compile(
                    r"\b(email|gmail|inbox|send email|compose|draft|unread mail"
                    r"|check mail|read email|mail)\b",
                    re.I,
                ),
                ["gmail"],
                "Use gmail for email operations (list, search, read, send, draft).",
            ),
            (
                "news",
                re.compile(r"\b(news|headline|current events|what happened today)\b", re.I),
                ["internet_search"],
                "Prefer news_curator for broad news digests.",
            ),
            (
                "fact_check",
                re.compile(r"\b(fact check|verify|is this true|debunk|evidence)\b", re.I),
                ["internet_search"],
                "Prefer fact_checker for claim verification tasks.",
            ),
            (
                "system_monitoring",
                re.compile(
                    r"\b(cpu|ram|memory usage|disk usage|storage|network status"
                    r"|process(?:es)?|system status|system health|system info"
                    r"|performance|uptime|load average)\b",
                    re.I,
                ),
                ["system_status"],
                "Use system_status for read-only system health checks (CPU, RAM, disk, network, processes).",
            ),
            (
                "web_browsing",
                re.compile(
                    r"\b(browse\s+(the\s+)?web|visit\s+(this\s+|a\s+)?url|open\s+(this\s+|a\s+)?(web)?page"
                    r"|navigate\s+to|screenshot|scrape|fetch\s+(this\s+|a\s+)?(page|url|website)"
                    r"|web\s*page|website\s+content|click\s+(on\s+)?(the\s+)?button"
                    r"|fill\s+(in\s+|out\s+)?(the\s+)?form"
                    r"|connect\s+to\s+chrome|cdp|devtools|cookies?\s+(get|clear|manage)"
                    r"|extract\s+(links|headings|tables|text|metadata|prices)"
                    r"|stealth\s+mode|anti.?detect"
                    r"|multiple\s+tabs?|new\s+tab)\b",
                    re.I,
                ),
                ["web_browser"],
                "Use web_browser for fetching URLs, browsing JS-heavy pages, snapshots, "
                "element interaction, CDP connection, multi-tab management, form filling, "
                "content extraction, cookie management, stealth mode, and page diagnostics.",
            ),
            (
                "file_operations",
                re.compile(
                    r"\b(file|folder|directory|desktop|documents|downloads"
                    r"|open file|browse|list files|find files|search files"
                    r"|create file|create folder|move file|rename file"
                    r"|read file|edit file|save file|delete file)\b",
                    re.I,
                ),
                ["file_browser"],
                "Use file_browser for local file operations (list, read, search, create, move, edit).",
            ),
        ]

    def _last_user_text(self, request: ModelRequest[ContextT]) -> str:
        for msg in reversed(request.messages):
            if isinstance(msg, HumanMessage):
                return _content_to_text(msg.content).strip()
        return ""

    def _classify(self, text: str) -> tuple[str, list[str], str]:
        for route, pattern, tools, hint in self._routes:
            if pattern.search(text):
                return route, tools, hint
        return "general", [], "Use normal planning; delegate only when specialization improves quality."

    def _reorder_tools(self, tools: list[Any], preferred: list[str]) -> list[Any]:
        if not preferred:
            return tools

        regular = [t for t in tools if not isinstance(t, dict)]
        provider = [t for t in tools if isinstance(t, dict)]
        preferred_set = set(preferred)

        ordered = [t for t in regular if getattr(t, "name", None) in preferred_set]
        ordered.extend([t for t in regular if getattr(t, "name", None) not in preferred_set])
        return [*ordered, *provider]

    def _append_hint(self, system_message: SystemMessage | None, hint: str) -> SystemMessage:
        route_text = f"\n\n[Routing Hint]\n{hint}\n"
        if system_message is None:
            return SystemMessage(content=route_text.strip())
        existing = system_message.text or ""
        return SystemMessage(content=f"{existing}{route_text}")

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        text = self._last_user_text(request)
        route, preferred_tools, hint = self._classify(text)

        patched_request = request.override(
            tools=self._reorder_tools(request.tools, preferred_tools),
            system_message=self._append_hint(request.system_message, hint),
            state={**request.state, "route_decision": route},
        )
        return handler(patched_request)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        text = self._last_user_text(request)
        route, preferred_tools, hint = self._classify(text)

        patched_request = request.override(
            tools=self._reorder_tools(request.tools, preferred_tools),
            system_message=self._append_hint(request.system_message, hint),
            state={**request.state, "route_decision": route},
        )
        return await handler(patched_request)


__all__ = ["RoutingMiddleware"]

