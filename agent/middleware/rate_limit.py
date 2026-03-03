import os
import threading
import time
from collections import deque
from typing import Any, Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command


class RateLimitMiddleware(AgentMiddleware):
    """Simple in-process sliding-window rate limiting for model and tool calls."""

    def __init__(
        self,
        model_calls_per_minute: int | None = None,
        tool_calls_per_minute: int | None = None,
    ) -> None:
        self.model_limit = model_calls_per_minute or int(os.getenv("MODEL_CALLS_PER_MINUTE", "60"))
        self.tool_limit = tool_calls_per_minute or int(os.getenv("TOOL_CALLS_PER_MINUTE", "120"))
        self.window_seconds = 60.0
        self._model_hits: deque[float] = deque()
        self._tool_hits: deque[float] = deque()
        self._lock = threading.Lock()

    def _acquire(self, bucket: deque[float], limit: int) -> bool:
        now = time.monotonic()
        with self._lock:
            while bucket and (now - bucket[0]) >= self.window_seconds:
                bucket.popleft()
            if len(bucket) >= limit:
                return False
            bucket.append(now)
            return True

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse | AIMessage:
        if not self._acquire(self._model_hits, self.model_limit):
            return AIMessage(content="Rate limit exceeded for model calls. Please retry in a moment.")
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse | AIMessage:
        if not self._acquire(self._model_hits, self.model_limit):
            return AIMessage(content="Rate limit exceeded for model calls. Please retry in a moment.")
        return await handler(request)

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        if not self._acquire(self._tool_hits, self.tool_limit):
            return ToolMessage(
                content="Rate limit exceeded for tool calls. Please retry in a moment.",
                name=request.tool_call.get("name"),
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return handler(request)

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        if not self._acquire(self._tool_hits, self.tool_limit):
            return ToolMessage(
                content="Rate limit exceeded for tool calls. Please retry in a moment.",
                name=request.tool_call.get("name"),
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return await handler(request)
