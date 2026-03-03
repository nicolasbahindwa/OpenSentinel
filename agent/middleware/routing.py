import re
from typing import Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import SystemMessage


class RoutingMiddleware(AgentMiddleware):
    """Adds dynamic routing hints so the main agent delegates when appropriate."""

    def __init__(self, subagent_name: str = "fact_checker") -> None:
        self.subagent_name = subagent_name
        self._fact_check_patterns = [
            re.compile(p, re.IGNORECASE)
            for p in [
                r"\bfact[- ]?check\b",
                r"\bverify\b",
                r"\bis this true\b",
                r"\bcheck (this|that|claim|rumou?r|news)\b",
                r"\bdebunk\b",
                r"\bsource[- ]?check\b",
            ]
        ]

    @staticmethod
    def _latest_user_text(request: ModelRequest) -> str:
        for msg in reversed(request.messages):
            if getattr(msg, "type", "") == "human":
                return getattr(msg, "text", "") or ""
        return ""

    def _should_route_to_fact_checker(self, text: str) -> bool:
        return any(p.search(text) for p in self._fact_check_patterns)

    def _route_hint(self) -> str:
        return (
            f"Routing hint: when the user asks for verification/fact-checking, delegate to "
            f"subagent `{self.subagent_name}` using the task tool and provide exact claim text."
        )

    def _merge_system(self, request: ModelRequest) -> ModelRequest:
        existing = request.system_message.text if request.system_message else ""
        hint = self._route_hint()
        if hint in existing:
            return request
        merged = f"{existing}\n\n{hint}".strip()
        return request.override(system_message=SystemMessage(content=merged))

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        user_text = self._latest_user_text(request)
        if self._should_route_to_fact_checker(user_text):
            request = self._merge_system(request)
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        user_text = self._latest_user_text(request)
        if self._should_route_to_fact_checker(user_text):
            request = self._merge_system(request)
        return await handler(request)
