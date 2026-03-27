"""Follow-up question middleware."""

from __future__ import annotations

import re
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ExtendedModelResponse,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from langchain_core.messages import AIMessage, BaseMessage, ChatMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.types import Command
from typing_extensions import NotRequired, override

from agent.logger import get_logger

logger = get_logger("agent.middleware.followups", component="followups")


class FollowupState(AgentState[ResponseT], total=False):
    followup_questions: NotRequired[list[str]]


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


def _normalize_question(text: str) -> str | None:
    cleaned = re.sub(r"^\s*(\d+[.)]|[-*])\s*", "", text).strip()
    if not cleaned:
        return None
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned.endswith("?"):
        cleaned = cleaned.rstrip(".,;:") + "?"
    return cleaned[0].upper() + cleaned[1:] if cleaned else cleaned


def _clean_followups(questions: list[str], max_questions: int) -> list[str]:
    seen: set[str] = set()
    cleaned: list[str] = []
    for question in questions:
        normalized = _normalize_question(question)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(normalized)
        if len(cleaned) >= max_questions:
            break
    return cleaned


def _normalize_topic(text: str) -> str:
    topic = re.sub(r"\s+", " ", text).strip(" \t\r\n.:;,-")
    return topic


def _topic_from_user_text(text: str) -> str:
    topic = _normalize_topic(text)
    topic = re.sub(
        r"^(can you|could you|would you|please|help me|tell me|show me|give me|explain|summarize|outline)\s+",
        "",
        topic,
        flags=re.IGNORECASE,
    )
    topic = re.sub(r"\?$", "", topic).strip()
    words = topic.split()
    if len(words) > 12:
        topic = " ".join(words[:12])
    return topic


class FollowupQuestionsMiddleware(AgentMiddleware[FollowupState, ContextT, ResponseT]):
    """Extract, normalize, and synthesize follow-up questions."""

    _SECTION_RE = re.compile(
        r"\n\s*\*{0,2}follow[\s\-]?up\s+questions?\*{0,2}:?\*{0,2}\s*\n"
        r"((?:\s*\d+[.)].+\s*\n?)+)",
        re.IGNORECASE,
    )

    _ITEM_RE = re.compile(r"\d+[.)]\s*(.+)")

    def __init__(self, max_followups: int = 5) -> None:
        super().__init__()
        self._max_followups = max(1, min(max_followups, 10))

    @staticmethod
    def _extract_tool_call_ids(msg: AIMessage) -> set[str]:
        tool_calls = getattr(msg, "tool_calls", None)
        if not tool_calls and hasattr(msg, "additional_kwargs"):
            tool_calls = (getattr(msg, "additional_kwargs", {}) or {}).get("tool_calls")

        ids: set[str] = set()
        for tool_call in tool_calls or []:
            if isinstance(tool_call, dict) and tool_call.get("id"):
                ids.add(str(tool_call["id"]))
        return ids

    @staticmethod
    def _is_tool_role_message(msg: BaseMessage) -> bool:
        if isinstance(msg, ToolMessage):
            return True
        if isinstance(msg, ChatMessage) and getattr(msg, "role", None) == "tool":
            return True
        return getattr(msg, "type", None) == "tool"

    @staticmethod
    def _tool_message_id(msg: BaseMessage) -> str:
        tool_call_id = getattr(msg, "tool_call_id", None)
        if tool_call_id:
            return str(tool_call_id)
        additional_kwargs = getattr(msg, "additional_kwargs", {}) or {}
        candidate = additional_kwargs.get("tool_call_id") or additional_kwargs.get("id")
        return str(candidate or "")

    def _sanitize_request_messages(self, messages: list[BaseMessage]) -> list[BaseMessage]:
        sanitized: list[BaseMessage] = []
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
            logger.warning("dropped_orphan_tool_messages_before_model count=%s", dropped)
        return sanitized

    def _message_debug_summary(self, messages: list[BaseMessage]) -> str:
        parts: list[str] = []
        for msg in messages:
            if isinstance(msg, AIMessage):
                parts.append(f"assistant(tool_calls={sorted(self._extract_tool_call_ids(msg))})")
            elif self._is_tool_role_message(msg):
                parts.append(f"tool(id={self._tool_message_id(msg) or '-'})")
            elif isinstance(msg, HumanMessage):
                parts.append("user")
            elif isinstance(msg, SystemMessage):
                parts.append("system")
            else:
                parts.append(getattr(msg, "type", msg.__class__.__name__))
        return " -> ".join(parts)

    def _extract_followups(self, text: str) -> tuple[str, list[str]]:
        match = self._SECTION_RE.search(text)
        if not match:
            return text.rstrip(), []
        raw = [q.strip() for q in self._ITEM_RE.findall(match.group(1))]
        followups = _clean_followups(raw, self._max_followups)
        clean = text[: match.start()].rstrip()
        return clean, followups

    @staticmethod
    def _latest_user_text(messages: list[BaseMessage]) -> str:
        for msg in reversed(messages):
            if isinstance(msg, HumanMessage):
                return _content_to_text(msg.content).strip()
        return ""

    @staticmethod
    def _looks_like_short_confirmation(text: str) -> bool:
        normalized = text.strip().lower()
        return normalized in {
            "ok",
            "okay",
            "done",
            "yes",
            "no",
            "thanks",
            "thank you",
            "sounds good",
            "understood",
        }

    @staticmethod
    def _looks_like_error(text: str) -> bool:
        normalized = text.strip().lower()
        error_markers = ("error", "failed", "unable", "exception", "traceback")
        return any(marker in normalized for marker in error_markers)

    def _should_generate_followups(self, text: str) -> bool:
        normalized = text.strip()
        if not normalized:
            return False
        if self._looks_like_short_confirmation(normalized):
            return False
        if self._looks_like_error(normalized):
            return False
        if len(normalized.split()) < 8:
            return False
        return True

    def _fallback_followups(
        self,
        request: ModelRequest[ContextT],
        assistant_text: str,
    ) -> list[str]:
        return []

    def _process_message(self, msg: AIMessage) -> tuple[AIMessage, list[str]]:
        content = _content_to_text(msg.content)
        clean, followups = self._extract_followups(content)
        if clean == content and isinstance(msg.content, str):
            return msg, followups
        new_msg = msg.model_copy()
        new_msg.content = clean
        return new_msg, followups

    def _merge_command(self, existing: Command | None, update: dict[str, Any]) -> Command:
        if existing is None:
            return Command(update=update)
        if existing.update is None:
            merged_update: Any = update
        elif isinstance(existing.update, dict):
            merged_update = {**existing.update, **update}
        else:
            merged_update = list(existing._update_as_tuples()) + list(update.items())
        return Command(
            graph=existing.graph,
            update=merged_update,
            resume=existing.resume,
            goto=existing.goto,
        )

    def _apply(
        self,
        request: ModelRequest[ContextT],
        response: ModelResponse[ResponseT],
        command: Command | None,
    ) -> ModelResponse[ResponseT] | ExtendedModelResponse[ResponseT]:
        new_messages: list[BaseMessage] = []
        collected: list[str] = []
        for msg in response.result:
            if isinstance(msg, AIMessage):
                new_msg, followups = self._process_message(msg)
                if followups:
                    collected = followups
                elif not collected:
                    collected = self._fallback_followups(request, _content_to_text(new_msg.content))
                new_messages.append(new_msg)
            else:
                new_messages.append(msg)

        new_response = ModelResponse(
            result=new_messages,
            structured_response=response.structured_response,
        )
        if command is not None:
            if collected:
                command = self._merge_command(command, {"followup_questions": collected})
            return ExtendedModelResponse(model_response=new_response, command=command)
        if collected:
            command = Command(update={"followup_questions": collected})
            return ExtendedModelResponse(model_response=new_response, command=command)
        return new_response

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT] | ExtendedModelResponse[ResponseT]:
        sanitized_request = request.override(
            messages=self._sanitize_request_messages(request.messages)
        )
        logger.info(
            "followups_message_summary %s",
            self._message_debug_summary(sanitized_request.messages),
        )
        result = handler(sanitized_request)
        if isinstance(result, ExtendedModelResponse):
            return self._apply(sanitized_request, result.model_response, result.command)
        if isinstance(result, ModelResponse):
            return self._apply(sanitized_request, result, None)
        if isinstance(result, AIMessage):
            return self._apply(sanitized_request, ModelResponse(result=[result]), None)
        return result

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT] | ExtendedModelResponse[ResponseT]:
        sanitized_request = request.override(
            messages=self._sanitize_request_messages(request.messages)
        )
        logger.info(
            "followups_message_summary %s",
            self._message_debug_summary(sanitized_request.messages),
        )
        result = await handler(sanitized_request)
        if isinstance(result, ExtendedModelResponse):
            return self._apply(sanitized_request, result.model_response, result.command)
        if isinstance(result, ModelResponse):
            return self._apply(sanitized_request, result, None)
        if isinstance(result, AIMessage):
            return self._apply(sanitized_request, ModelResponse(result=[result]), None)
        return result


__all__ = ["FollowupQuestionsMiddleware"]
