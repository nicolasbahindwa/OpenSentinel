"""Always-on response style middleware for OpenSentinel."""

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

from agent.logger import get_logger

logger = get_logger("agent.middleware.response_style", component="response_style")


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


class ResponseStyleMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Inject a concise style hint on every turn."""

    _HIGH_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
        ("formal", re.compile(r"\b(legal|contract|lawsuit|regulation|compliance|policy)\b", re.I)),
        ("formal", re.compile(r"\b(medical|diagnosis|symptom|treatment|prescription|doctor)\b", re.I)),
        ("formal", re.compile(r"\b(invest|investment|portfolio|stock|crypto|financial advice|tax)\b", re.I)),
        ("formal", re.compile(r"\b(vulnerability|exploit|breach|malware|incident|security)\b", re.I)),
        ("formal", re.compile(r"\b(emergency|suicide|self-harm|danger|unsafe|urgent)\b", re.I)),
    )

    def _last_user_text(self, request: ModelRequest[ContextT]) -> str:
        for msg in reversed(request.messages):
            if isinstance(msg, HumanMessage):
                return _content_to_text(msg.content).strip()
        return ""

    @staticmethod
    def _conversation_bias(request: ModelRequest[ContextT]) -> str | None:
        value = request.state.get("response_tone") if isinstance(request.state, dict) else None
        return str(value) if value else None

    def _classify_tone(self, text: str, prior_tone: str | None) -> tuple[str, str]:
        normalized = text.strip()
        lowered = f" {normalized.lower()} "
        if not normalized:
            return "neutral", "low"

        for tone, pattern in self._HIGH_RISK_PATTERNS:
            if pattern.search(normalized):
                return tone, "high"

        scores = {
            "formal": 0,
            "neutral": 0,
            "friendly": 0,
            "relaxed": 0,
            "fun": 0,
        }

        formal_markers = (" please ", " thank you ", " kindly ", " could you ", " would you ", " review ", " analyze ")
        friendly_markers = (" thanks ", " appreciate ", " i'd ", " i'm ", " you're ", " could you help ")
        relaxed_markers = (" hey ", " hi ", " quick ", " kinda ", " wanna ", " gonna ", " can u ", " pls ")
        fun_markers = (" lol ", " haha ", " bro ", " wild ", " no way ", " omg ")

        scores["formal"] += sum(lowered.count(marker) for marker in formal_markers)
        scores["friendly"] += sum(lowered.count(marker) for marker in friendly_markers)
        scores["relaxed"] += sum(lowered.count(marker) for marker in relaxed_markers)
        scores["fun"] += sum(lowered.count(marker) for marker in fun_markers)
        scores["neutral"] += 1

        if re.search(r"[!?]{2,}|[.]{3,}", normalized):
            scores["fun"] += 2
        if re.search(r"[\U0001F300-\U0001FAFF]", normalized):
            scores["fun"] += 2
        if normalized == normalized.lower() and len(normalized.split()) <= 18:
            scores["relaxed"] += 1
        if re.search(r"\b(error|traceback|bug|test|function|middleware|api|python|typescript|refactor)\b", normalized, re.I):
            scores["formal"] += 1
        if re.search(r"^\s*(\d+[.)]|[-*])", normalized):
            scores["formal"] += 1

        if prior_tone in scores:
            scores[prior_tone] += 1

        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        top_tone, top_score = ordered[0]
        second_score = ordered[1][1]

        if top_score <= 1:
            return "neutral", "low"
        if top_score - second_score <= 1:
            return "neutral", "low"
        if top_score - second_score >= 3:
            return top_tone, "high"
        return top_tone, "medium"

    @staticmethod
    def _append_hint(system_message: SystemMessage | None, tone: str, confidence: str) -> SystemMessage:
        hint = (
            "\n\n[Response Style]\n"
            "Use the response-style policy from mood-skill."
            " Match the user's latest message language unless they request another language."
            f" Use a {tone} tone for the final user-facing answer."
            " Change presentation only; do not change facts, reasoning, conclusions, or risk framing."
            " For legal, medical, financial-risk, safety, and security topics, stay formal regardless of the user's tone."
            f" Confidence: {confidence}.\n"
        )
        if system_message is None:
            return SystemMessage(content=hint.strip())
        existing = system_message.text or ""
        return SystemMessage(content=f"{existing}{hint}")

    def _patch_request(self, request: ModelRequest[ContextT]) -> ModelRequest[ContextT]:
        text = self._last_user_text(request)
        prior_tone = self._conversation_bias(request)
        tone, confidence = self._classify_tone(text, prior_tone)
        state = dict(request.state or {})
        logger.info("response_style tone=%s confidence=%s", tone, confidence)
        return request.override(
            system_message=self._append_hint(request.system_message, tone, confidence),
            state={**state, "response_tone": tone, "response_tone_confidence": confidence},
        )

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        return handler(self._patch_request(request))

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        return await handler(self._patch_request(request))


__all__ = ["ResponseStyleMiddleware"]
