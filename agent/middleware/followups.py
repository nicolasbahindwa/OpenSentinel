"""Follow-up question formatting middleware."""

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
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.types import Command
from typing_extensions import NotRequired, TypedDict, override

from agent.tools.followup_writer import FollowupWriterTool


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


class FollowupQuestionsMiddleware(AgentMiddleware[FollowupState, ContextT, ResponseT]):
    """Extract and format follow-up questions from model responses."""

    _SECTION_RE = re.compile(
        r"\n\s*\*{0,2}follow[\s\-]?up\s+questions?\*{0,2}:?\*{0,2}\s*\n"
        r"((?:\s*\d+[.)].+\s*\n?)+)",
        re.IGNORECASE,
    )

    _ITEM_RE = re.compile(r"\d+[.)]\s*(.+)")

    def __init__(self, max_followups: int = 5) -> None:
        super().__init__()
        self._writer = FollowupWriterTool()
        self._max_followups = max(1, min(max_followups, 10))

    def _extract_followups(self, text: str) -> tuple[str, list[str]]:
        match = self._SECTION_RE.search(text)
        if not match:
            return text.rstrip(), []
        raw = [q.strip() for q in self._ITEM_RE.findall(match.group(1))]
        followups = self._writer._run(questions=raw, max_questions=self._max_followups)
        clean = text[: match.start()].rstrip()
        return clean, followups

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
        result = handler(request)
        if isinstance(result, ExtendedModelResponse):
            return self._apply(result.model_response, result.command)
        if isinstance(result, ModelResponse):
            return self._apply(result, None)
        if isinstance(result, AIMessage):
            return self._apply(ModelResponse(result=[result]), None)
        return result

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT] | ExtendedModelResponse[ResponseT]:
        result = await handler(request)
        if isinstance(result, ExtendedModelResponse):
            return self._apply(result.model_response, result.command)
        if isinstance(result, ModelResponse):
            return self._apply(result, None)
        if isinstance(result, AIMessage):
            return self._apply(ModelResponse(result=[result]), None)
        return result


__all__ = ["FollowupQuestionsMiddleware"]
