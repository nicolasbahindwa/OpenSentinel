import logging
import time
from typing import Any, Awaitable, Callable

from langchain.agents.middleware.types import AgentMiddleware, ModelRequest, ModelResponse
from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest
from langgraph.types import Command


logger = logging.getLogger("agent.middleware.observability")


class ObservabilityMiddleware(AgentMiddleware):
    """Logs model and tool latency/error events."""

    def wrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        start = time.perf_counter()
        try:
            response = handler(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "model_call_success",
                extra={
                    "elapsed_ms": elapsed_ms,
                    "message_count": len(request.messages),
                    "tool_count": len(request.tools or []),
                },
            )
            return response
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("model_call_error", extra={"elapsed_ms": elapsed_ms})
            raise

    async def awrap_model_call(
        self,
        request: ModelRequest,
        handler: Callable[[ModelRequest], Awaitable[ModelResponse]],
    ) -> ModelResponse:
        start = time.perf_counter()
        try:
            response = await handler(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info(
                "model_call_success",
                extra={
                    "elapsed_ms": elapsed_ms,
                    "message_count": len(request.messages),
                    "tool_count": len(request.tools or []),
                },
            )
            return response
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("model_call_error", extra={"elapsed_ms": elapsed_ms})
            raise

    def wrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command[Any]],
    ) -> ToolMessage | Command[Any]:
        start = time.perf_counter()
        tool_name = request.tool_call.get("name", "unknown_tool")
        try:
            result = handler(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info("tool_call_success", extra={"tool": tool_name, "elapsed_ms": elapsed_ms})
            return result
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("tool_call_error", extra={"tool": tool_name, "elapsed_ms": elapsed_ms})
            raise

    async def awrap_tool_call(
        self,
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], Awaitable[ToolMessage | Command[Any]]],
    ) -> ToolMessage | Command[Any]:
        start = time.perf_counter()
        tool_name = request.tool_call.get("name", "unknown_tool")
        try:
            result = await handler(request)
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.info("tool_call_success", extra={"tool": tool_name, "elapsed_ms": elapsed_ms})
            return result
        except Exception:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            logger.exception("tool_call_error", extra={"tool": tool_name, "elapsed_ms": elapsed_ms})
            raise
