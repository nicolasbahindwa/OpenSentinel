"""Request rate-limiting middleware for OpenSentinel."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from typing import Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    ResponseT,
    hook_config,
)
from langchain_core.messages import AIMessage
from typing_extensions import override

from agent.logger import get_logger

logger = get_logger("agent.middleware.rate_limit", component="rate_limit")


class RateLimitMiddleware(AgentMiddleware[AgentState[ResponseT], ContextT, ResponseT]):
    """Enforce a per-identity request budget in a rolling time window."""

    _requests: dict[str, deque[float]] = defaultdict(deque)
    _lock = threading.Lock()

    def __init__(self, *, max_requests: int = 30, window_seconds: int = 60) -> None:
        super().__init__()
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def _identity(self, runtime: Any) -> str:
        context = getattr(runtime, "context", None)
        if isinstance(context, dict):
            for key in ("user_id", "thread_id", "session_id"):
                value = context.get(key)
                if value:
                    return str(value)
        return "global"

    @hook_config(can_jump_to=["end"])
    @override
    def before_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        identity = self._identity(runtime)
        now = time.time()

        with self._lock:
            queue = self._requests[identity]
            while queue and (now - queue[0]) > self.window_seconds:
                queue.popleft()

            if len(queue) >= self.max_requests:
                retry_after = max(1, int(self.window_seconds - (now - queue[0])))
                logger.warning(
                    "rate_limit_exceeded",
                    identity=identity,
                    retry_after_seconds=retry_after,
                )
                msg = AIMessage(
                    content=(
                        "Rate limit reached. "
                        f"Please retry in about {retry_after} seconds."
                    )
                )
                return {"messages": [msg], "jump_to": "end"}

            queue.append(now)

        return None

    async def abefore_model(
        self,
        state: AgentState[ResponseT],
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.before_model(state, runtime)


__all__ = ["RateLimitMiddleware"]

