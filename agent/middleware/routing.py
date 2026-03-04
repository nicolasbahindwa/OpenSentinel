import re
from typing import Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage


# ==============================
# Default route definitions
# ==============================

DEFAULT_ROUTES: list[dict] = [
    {
        "name": "fact_checker",
        "patterns": [
            r"\bfact[- ]?check\b",
            r"\bverify\b",
            r"\bis this true\b",
            r"\bcheck (this|that|claim|rumou?r|news)\b",
            r"\bdebunk\b",
            r"\bsource[- ]?check\b",
        ],
        "hint": (
            "Routing hint: delegate to subagent `{name}` using the task tool. "
            "Pass the exact claim text and required output format."
        ),
    },
    {
        "name": "weather_advisor",
        "patterns": [
            r"\bweather\b",
            r"\bforecast\b",
            r"\btemperature\b",
            r"\brain\b",
            r"\bumbrella\b",
            r"\bclimate\b",
            r"\boutdoor\b.*\b(plan|activit)",
        ],
        "hint": (
            "Routing hint: delegate to subagent `{name}` using the task tool. "
            "Include the city name (check /memories/user_prefs.txt if not specified)."
        ),
    },
    {
        "name": "finance_expert",
        "patterns": [
            r"\bstock[s]?\b",
            r"\bmarket[s]?\b",
            r"\bdollar[- ]?rate\b",
            r"\bexchange[- ]?rate\b",
            r"\binvest(ment|ing)?\b",
            r"\bportfolio\b",
            r"\bforex\b",
            r"\bcrypto\b",
            r"\bticker\b",
            r"\bbuy[- ]?(stock|shares)\b",
            r"\bsell[- ]?(stock|shares)\b",
        ],
        "hint": (
            "Routing hint: delegate to subagent `{name}` using the task tool. "
            "Include specific ticker symbols or forex pairs. "
            "Check /memories/user_prefs.txt for the user's watchlist."
        ),
    },
    {
        "name": "news_curator",
        "patterns": [
            r"\bnews\b",
            r"\bheadline[s]?\b",
            r"\bcurrent[- ]?events?\b",
            r"\bwhat'?s happening\b",
        ],
        "hint": (
            "Routing hint: delegate to subagent `{name}` using the task tool. "
            "Specify categories (tech, finance, politics) or check /memories/user_prefs.txt."
        ),
    },
    {
        "name": "morning_briefing",
        "patterns": [
            r"\bgood morning\b",
            r"\bmorning[- ]?briefing\b",
            r"\bdaily[- ]?(summary|briefing|update)\b",
            r"\bstart my day\b",
            r"\bjust woke up\b",
            r"\bwhat should I know\b",
            r"\bbrief me\b",
            r"\bwhat did I miss\b",
        ],
        "hint": (
            "Routing hint: delegate to subagent `{name}` using the task tool. "
            "IMPORTANT: First read /memories/user_prefs.txt and pass the user's preferences "
            "(location, units, watchlist, forex, news_categories) in the task description."
        ),
    },
]


class RoutingMiddleware(AgentMiddleware):
    """Adds dynamic routing hints so the main agent delegates when appropriate.

    Supports multiple subagent routes with pattern-based matching.
    """

    def __init__(self, routes: list[dict] | None = None) -> None:
        self._routes = []
        for route in (routes or DEFAULT_ROUTES):
            self._routes.append({
                "name": route["name"],
                "compiled": [re.compile(p, re.IGNORECASE) for p in route["patterns"]],
                "hint": route["hint"],
            })

    @staticmethod
    def _latest_user_text(request: ModelRequest) -> str:
        for msg in reversed(request.messages):
            if getattr(msg, "type", "") == "human":
                return getattr(msg, "text", "") or ""
        return ""

    def _matched_routes(self, text: str) -> list[dict]:
        """Return all routes whose patterns match the user text."""
        matched = []
        for route in self._routes:
            if any(p.search(text) for p in route["compiled"]):
                matched.append(route)
        return matched

    def _proactive_hint(self) -> str:
        return (
            "Proactive verification: For any response containing factual claims, "
            "you should use internet_search to verify before stating them. "
            "If you encounter conflicting sources or high-stakes claims (medical, legal, financial), "
            "delegate to subagent `fact_checker` for thorough verification."
        )

    def _merge_hint(self, request: ModelRequest, hint: str) -> ModelRequest:
        existing = request.system_message.text if request.system_message else ""
        if hint in existing:
            return request
        merged = f"{existing}\n\n{hint}".strip()
        return request.override(system_message=SystemMessage(content=merged))

    def _apply_routing(self, request: ModelRequest, user_text: str) -> ModelRequest:
        # Always inject proactive verification hint
        request = self._merge_hint(request, self._proactive_hint())

        # Inject specific routing hints for matched patterns
        for route in self._matched_routes(user_text):
            hint = route["hint"].format(name=route["name"])
            request = self._merge_hint(request, hint)

        return request

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        user_text = self._latest_user_text(request)
        request = self._apply_routing(request, user_text)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        user_text = self._latest_user_text(request)
        request = self._apply_routing(request, user_text)
        return await handler(request)
