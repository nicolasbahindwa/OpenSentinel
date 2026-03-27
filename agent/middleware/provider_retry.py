"""Provider error retry middleware for transient model API failures."""

from __future__ import annotations

import asyncio
import time
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ModelRequest,
    ModelResponse,
    ResponseT,
)
from typing_extensions import override

from agent.logger import get_logger

logger = get_logger("agent.middleware.provider_retry", component="provider_retry")


class ProviderRetryMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Retry transient provider errors with bounded exponential backoff."""

    def __init__(self, max_attempts: int = 3, base_delay_seconds: float = 1.0) -> None:
        super().__init__()
        self._max_attempts = max(1, min(max_attempts, 5))
        self._base_delay_seconds = max(0.1, base_delay_seconds)

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        text = str(exc).lower()
        return "too many requests" in text or "[429]" in text or "'status': 429" in text

    def _delay_seconds(self, attempt_index: int) -> float:
        return self._base_delay_seconds * (2 ** attempt_index)

    @override
    def wrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        last_exc: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                return handler(request)
            except Exception as exc:
                if not self._is_retryable(exc) or attempt + 1 >= self._max_attempts:
                    raise
                delay = self._delay_seconds(attempt)
                logger.warning(
                    "provider_retry_sync attempt=%s delay_seconds=%.2f",
                    attempt + 1,
                    delay,
                )
                time.sleep(delay)
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        return handler(request)

    async def awrap_model_call(
        self,
        request: ModelRequest[ContextT],
        handler: Any,
    ) -> ModelResponse[ResponseT]:
        last_exc: Exception | None = None
        for attempt in range(self._max_attempts):
            try:
                return await handler(request)
            except Exception as exc:
                if not self._is_retryable(exc) or attempt + 1 >= self._max_attempts:
                    raise
                delay = self._delay_seconds(attempt)
                logger.warning(
                    "provider_retry_async attempt=%s delay_seconds=%.2f",
                    attempt + 1,
                    delay,
                )
                await asyncio.sleep(delay)
                last_exc = exc
        if last_exc is not None:
            raise last_exc
        return await handler(request)


__all__ = ["ProviderRetryMiddleware"]
