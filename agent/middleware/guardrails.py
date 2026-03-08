"""Safety guardrails middleware for OpenSentinel."""

from __future__ import annotations

import re
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ResponseT,
    hook_config,
)
from langchain_core.messages import AIMessage, HumanMessage
from typing_extensions import override


def _content_to_text(content: Any) -> str:
    """Normalize message content (string or content blocks) into plain text."""
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
                continue
            if isinstance(block, dict):
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)

    return str(content)


class GuardrailsMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Blocks clearly harmful intent and returns a safe refusal response."""

    def __init__(self) -> None:
        super().__init__()
        self._allow_context = [
            re.compile(r"\b(prevent|mitigat|defend|detect|protect|awareness|education)\b", re.I),
            re.compile(r"\b(history|historical|fiction|novel|movie|policy|compliance)\b", re.I),
        ]
        self._blocked_intent = {
            "malware": re.compile(
                r"\b(write|build|create|develop|generate|make)\b.{0,40}\b(malware|ransomware|trojan|keylogger|virus)\b",
                re.I,
            ),
            "phishing": re.compile(
                r"\b(phish|credential harvest|steal (password|credentials)|bypass (auth|authentication))\b",
                re.I,
            ),
            "weapons": re.compile(
                r"\b(build|make|assemble|construct)\b.{0,40}\b(bomb|explosive|improvised explosive|weapon)\b",
                re.I,
            ),
        }

    def _last_user_text(self, state: AgentState[ResponseT]) -> str:
        messages = state.get("messages", [])
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return _content_to_text(msg.content).strip()
        return ""

    def _is_allowed_context(self, text: str) -> bool:
        return any(pattern.search(text) for pattern in self._allow_context)

    def _unsafe_category(self, text: str) -> str | None:
        for category, pattern in self._blocked_intent.items():
            if pattern.search(text):
                return category
        return None

    @hook_config(can_jump_to=["end"])
    @override
    def before_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        user_text = self._last_user_text(state)
        if not user_text:
            return None

        if self._is_allowed_context(user_text):
            return None

        category = self._unsafe_category(user_text)
        if category is None:
            return None

        refusal = AIMessage(
            content=(
                "I can't help with harmful instructions. "
                "If your goal is defensive or educational, I can help with prevention, "
                "risk reduction, and safe best practices."
            )
        )
        return {"messages": [refusal], "jump_to": "end"}

    async def abefore_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.before_model(state, runtime)


__all__ = ["GuardrailsMiddleware"]

