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
from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, HumanMessage, SystemMessage, ToolMessage
from typing_extensions import override

from agent.logger import get_logger

logger = get_logger("agent.middleware.routing", component="routing")


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
                "transport",
                re.compile(
                    r"\b(train|station|transport|transportation|fare|ticket|route|transit|metro|subway|bus|jr|travel cost)\b",
                    re.I,
                ),
                ["internet_search", "weather_lookup"],
                "For straightforward travel, fare, and route lookups, use direct tools and answer in the main agent. Do not delegate to a general-purpose subagent unless the user explicitly asks for deeper research.",
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

    @staticmethod
    def _extract_tool_call_ids(msg: Any) -> set[str]:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls and hasattr(msg, "additional_kwargs"):
            additional_kwargs = getattr(msg, "additional_kwargs", {}) or {}
            tool_calls = additional_kwargs.get("tool_calls")

        ids: set[str] = set()
        for tool_call in tool_calls or []:
            if isinstance(tool_call, dict) and tool_call.get("id"):
                ids.add(str(tool_call["id"]))
        return ids

    @staticmethod
    def _is_tool_role_message(msg: Any) -> bool:
        if isinstance(msg, ToolMessage):
            return True
        if isinstance(msg, ChatMessage) and getattr(msg, "role", None) == "tool":
            return True
        return getattr(msg, "role", None) == "tool" or getattr(msg, "type", None) == "tool"

    @staticmethod
    def _tool_message_id(msg: Any) -> str:
        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id:
            return str(tool_call_id)
        additional_kwargs = getattr(msg, "additional_kwargs", {}) or {}
        candidate = additional_kwargs.get("tool_call_id") or additional_kwargs.get("id")
        return str(candidate or "")

    def _sanitize_messages(self, messages: list[Any]) -> list[Any]:
        """Drop orphaned tool-role messages that would be rejected by tool-capable chat APIs."""
        sanitized: list[Any] = []
        pending_tool_calls: set[str] = set()
        dropped = 0

        for msg in messages:
            if isinstance(msg, AIMessage):
                pending_tool_calls = self._extract_tool_call_ids(msg)
                sanitized.append(msg)
                continue

            if self._is_tool_role_message(msg):
                tool_call_id = self._tool_message_id(msg)
                if tool_call_id and tool_call_id in pending_tool_calls:
                    pending_tool_calls.discard(tool_call_id)
                    sanitized.append(msg)
                elif not tool_call_id and pending_tool_calls:
                    sanitized.append(msg)
                else:
                    dropped += 1
                continue

            pending_tool_calls = set()
            sanitized.append(msg)

        if dropped:
            logger.warning("dropped_orphan_tool_messages count=%s", dropped)
        return sanitized

    def _message_debug_summary(self, messages: list[Any]) -> str:
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                ids = sorted(self._extract_tool_call_ids(msg))
                parts.append(f"assistant(tool_calls={ids})")
            elif self._is_tool_role_message(msg):
                parts.append(f"tool(id={self._tool_message_id(msg) or '-'})")
            elif isinstance(msg, HumanMessage):
                parts.append("user")
            elif isinstance(msg, SystemMessage):
                parts.append("system")
            else:
                parts.append(getattr(msg, "type", msg.__class__.__name__))
        return " -> ".join(parts)

    def _classify(self, text: str) -> tuple[str, list[str], str]:
        matched_routes: list[str] = []
        preferred_tools: list[str] = []
        hints: list[str] = []

        for route, pattern, tools, hint in self._routes:
            if not pattern.search(text):
                continue
            matched_routes.append(route)
            for tool_name in tools:
                if tool_name not in preferred_tools:
                    preferred_tools.append(tool_name)
            if hint not in hints:
                hints.append(hint)

        if not matched_routes:
            return "general", [], "Use normal planning; delegate only when specialization improves quality."

        return "+".join(matched_routes), preferred_tools, " ".join(hints)

    def _reorder_tools(self, tools: list[Any], preferred: list[str]) -> list[Any]:
        if not preferred:
            return tools

        regular = [t for t in tools if not isinstance(t, dict)]
        provider = [t for t in tools if isinstance(t, dict)]
        preferred_set = set(preferred)

        ordered = [t for t in regular if getattr(t, "name", None) in preferred_set]
        ordered.extend([t for t in regular if getattr(t, "name", None) not in preferred_set])
        return [*ordered, *provider]

    @staticmethod
    def _should_disable_task_tool(route: str, text: str) -> bool:
        """
        Determine if task delegation tool should be disabled.

        CRITICAL FIX: Disable task tool for ALL queries that can be handled with direct tools.
        Task delegation is causing infinite loops where subagents return tool call syntax
        as strings, which the main agent then interprets as "call this tool", creating a loop.
        """
        normalized = text.lower()

        # Always allow if explicit research/analysis/planning requested
        explicit_research_markers = (
            "research",
            "investigate",
            "deep dive",
            "thorough",
            "comprehensive",
            "in detail",
            "analyze",
            "analysis",
            "plan",
            "strategy",
        )
        if any(marker in normalized for marker in explicit_research_markers):
            return False

        # CHANGED: Disable task tool for weather/finance/news/transport queries
        # Let the main agent handle these directly with its tools
        route_parts = set(route.split("+"))
        if route_parts & {"weather", "transport", "finance", "news", "fact_check", "general"}:
            logger.info("disabling_task_tool reason=direct_tools_available route=%s", route)
            return True

        # For other routes, keep task tool
        return False

    def _filter_tools_for_route(self, tools: list[Any], route: str, text: str) -> list[Any]:
        if not self._should_disable_task_tool(route, text):
            return tools

        filtered: list[Any] = []
        for tool in tools:
            name = getattr(tool, "name", None) if not isinstance(tool, dict) else None
            if name == "task":
                continue
            filtered.append(tool)
        return filtered

    def _append_hint(self, system_message: SystemMessage | None, hint: str) -> SystemMessage:
        route_text = (
            "\n\n[Routing Hint]\n"
            f"{hint}\n"
            "Make at most one tool call in a single assistant turn. If more tools are needed, use them sequentially.\n"
        )
        if system_message is None:
            return SystemMessage(content=route_text.strip())
        existing = system_message.text or ""
        return SystemMessage(content=f"{existing}{route_text}")

    @staticmethod
    def _append_force_answer_hint(system_message: SystemMessage | None) -> SystemMessage:
        force_text = (
            "\n\n[Stop Tool Loop]\n"
            "Recent tool results are repetitive and already provide enough information.\n"
            "Do not call any more tools in this turn.\n"
            "Answer the user directly using the existing tool results in the conversation.\n"
        )
        if system_message is None:
            return SystemMessage(content=force_text.strip())
        existing = system_message.text or ""
        return SystemMessage(content=f"{existing}{force_text}")

    @staticmethod
    def _recent_tool_outputs(messages: list[Any], limit: int = 8) -> list[str]:
        outputs: list[str] = []
        for msg in messages[-limit:]:
            if RoutingMiddleware._is_tool_role_message(msg):
                text = _content_to_text(msg.content).strip()
                if text:
                    outputs.append(text)
        return outputs

    def _should_force_answer_from_recent_tools(self, messages: list[Any]) -> bool:
        """Check if recent tool outputs are repetitive, indicating a stuck loop."""
        outputs = self._recent_tool_outputs(messages, limit=10)  # Check more history

        # Need at least 4 tool outputs to detect a pattern
        if len(outputs) < 4:
            return False

        # Normalize outputs for comparison (remove extra whitespace)
        normalized = [" ".join(output.split()) for output in outputs]

        # Check if the same output appears 3+ times in recent history
        latest = normalized[-1]
        duplicate_count = sum(1 for output in normalized if output == latest)
        if duplicate_count >= 3:
            logger.warning("detected_repetitive_tools duplicates=%s output_preview=%s",
                          duplicate_count, latest[:100])
            return True

        # Check if last 4 outputs are all identical
        recent_unique = set(normalized[-4:])
        if len(recent_unique) == 1:
            logger.warning("detected_identical_tool_loop outputs=%s", len(normalized[-4:]))
            return True

        return False

    def _should_force_answer_for_route(self, route: str, messages: list[Any]) -> bool:
        # ONLY force answer if we detect truly repetitive tool outputs (stuck in infinite loop)
        # Let the agent naturally decide when it has enough information
        if self._should_force_answer_from_recent_tools(messages):
            logger.warning("force_answer_triggered reason=repetitive_tool_loop_detected")
            return True

        # No artificial limits - trust the agent's judgment and recursion limit
        return False

    @staticmethod
    def _is_single_tool_call_provider_error(exc: Exception) -> bool:
        text = str(exc).lower()
        return "only supports single tool-calls at once" in text

    @staticmethod
    def _append_single_tool_retry_hint(system_message: SystemMessage | None) -> SystemMessage:
        retry_text = (
            "\n\n[Tool Call Retry]\n"
            "The provider rejected the previous attempt because it tried to call multiple tools in one turn.\n"
            "You must now do exactly one of these:\n"
            "1. Call exactly one tool.\n"
            "2. Answer without tools.\n"
            "Do not request multiple tool calls in this turn.\n"
        )
        if system_message is None:
            return SystemMessage(content=retry_text.strip())
        existing = system_message.text or ""
        return SystemMessage(content=f"{existing}{retry_text}")

    @staticmethod
    def _select_single_retry_tool(
        tools: list[Any],
        route: str | None,
    ) -> tuple[list[Any], Any | None]:
        regular_tools = [tool for tool in tools if not isinstance(tool, dict)]
        if not regular_tools:
            return tools, None

        if route == "general":
            for tool in regular_tools:
                if getattr(tool, "name", None) == "tool_search":
                    return [tool], getattr(tool, "name", None)

        selected = regular_tools[0]
        return [selected], getattr(selected, "name", None)

    def _retry_with_single_tool_constraint(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
        exc: Exception,
    ) -> ModelResponse[ResponseT]:
        state = dict(request.state or {})
        if state.get("single_tool_retry_attempted"):
            raise exc
        retry_tools, retry_tool_choice = self._select_single_retry_tool(
            request.tools,
            state.get("route_decision"),
        )
        logger.warning("retrying_after_single_tool_provider_error")
        retry_request = request.override(
            system_message=self._append_single_tool_retry_hint(request.system_message),
            tools=retry_tools,
            tool_choice=retry_tool_choice,
            state={**state, "single_tool_retry_attempted": True},
        )
        return handler(retry_request)

    async def _aretry_with_single_tool_constraint(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
        exc: Exception,
    ) -> ModelResponse[ResponseT]:
        state = dict(request.state or {})
        if state.get("single_tool_retry_attempted"):
            raise exc
        retry_tools, retry_tool_choice = self._select_single_retry_tool(
            request.tools,
            state.get("route_decision"),
        )
        logger.warning("retrying_after_single_tool_provider_error")
        retry_request = request.override(
            system_message=self._append_single_tool_retry_hint(request.system_message),
            tools=retry_tools,
            tool_choice=retry_tool_choice,
            state={**state, "single_tool_retry_attempted": True},
        )
        return await handler(retry_request)

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        text = self._last_user_text(request)
        route, preferred_tools, hint = self._classify(text)

        sanitized_messages = self._sanitize_messages(request.messages)
        state = dict(request.state or {})

        # Enhanced logging for debugging
        logger.info("=== ROUTING MIDDLEWARE ===")
        logger.info("route=%s user_query=%s", route, text[:100])
        logger.info("preferred_tools=%s", preferred_tools)
        logger.info("message_flow=%s", self._message_debug_summary(sanitized_messages))
        logger.info("total_messages=%s tool_outputs=%s",
                   len(sanitized_messages),
                   len(self._recent_tool_outputs(sanitized_messages)))

        force_answer = self._should_force_answer_for_route(route, sanitized_messages)
        if force_answer:
            logger.warning("FORCING_ANSWER route=%s reason=tool_loop_detected", route)
        patched_request = request.override(
            messages=sanitized_messages,
            tools=[] if force_answer else self._filter_tools_for_route(
                self._reorder_tools(request.tools, preferred_tools),
                route,
                text,
            ),
            tool_choice="none" if force_answer else request.tool_choice,
            system_message=(
                self._append_force_answer_hint(self._append_hint(request.system_message, hint))
                if force_answer
                else self._append_hint(request.system_message, hint)
            ),
            state={**state, "route_decision": route, "forced_answer_after_tool_loop": force_answer},
        )
        try:
            response = handler(patched_request)
            logger.info("=== MODEL RESPONSE ===")
            if hasattr(response, 'result'):
                logger.info("response_messages=%s", len(response.result) if hasattr(response.result, '__len__') else 1)
            return response
        except Exception as exc:
            logger.error("model_call_failed error=%s", str(exc)[:200])
            if self._is_single_tool_call_provider_error(exc):
                return self._retry_with_single_tool_constraint(patched_request, handler, exc)
            raise

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        text = self._last_user_text(request)
        route, preferred_tools, hint = self._classify(text)

        sanitized_messages = self._sanitize_messages(request.messages)
        state = dict(request.state or {})

        # Enhanced logging for debugging (async)
        logger.info("=== ROUTING MIDDLEWARE (ASYNC) ===")
        logger.info("route=%s user_query=%s", route, text[:100])
        logger.info("preferred_tools=%s", preferred_tools)
        logger.info("message_flow=%s", self._message_debug_summary(sanitized_messages))
        logger.info("total_messages=%s tool_outputs=%s",
                   len(sanitized_messages),
                   len(self._recent_tool_outputs(sanitized_messages)))

        force_answer = self._should_force_answer_for_route(route, sanitized_messages)
        if force_answer:
            logger.warning("FORCING_ANSWER route=%s reason=tool_loop_detected", route)
        patched_request = request.override(
            messages=sanitized_messages,
            tools=[] if force_answer else self._filter_tools_for_route(
                self._reorder_tools(request.tools, preferred_tools),
                route,
                text,
            ),
            tool_choice="none" if force_answer else request.tool_choice,
            system_message=(
                self._append_force_answer_hint(self._append_hint(request.system_message, hint))
                if force_answer
                else self._append_hint(request.system_message, hint)
            ),
            state={**state, "route_decision": route, "forced_answer_after_tool_loop": force_answer},
        )
        try:
            response = await handler(patched_request)
            logger.info("=== MODEL RESPONSE (ASYNC) ===")
            if hasattr(response, 'result'):
                logger.info("response_messages=%s", len(response.result) if hasattr(response.result, '__len__') else 1)
            return response
        except Exception as exc:
            logger.error("model_call_failed error=%s", str(exc)[:200])
            if self._is_single_tool_call_provider_error(exc):
                return await self._aretry_with_single_tool_constraint(patched_request, handler, exc)
            raise


__all__ = ["RoutingMiddleware"]

