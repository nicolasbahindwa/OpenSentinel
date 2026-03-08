"""Observability middleware for timing and routing telemetry."""

from __future__ import annotations

import logging
import time
from typing import Annotated, Any

from langchain.agents.middleware.types import (
    AgentMiddleware,
    AgentState,
    ContextT,
    PrivateStateAttr,
    ResponseT,
)
from typing_extensions import NotRequired, TypedDict, override

logger = logging.getLogger("agent.middleware.observability")


class ObservabilityState(AgentState[ResponseT], total=False):
    obs_started_at: Annotated[NotRequired[float], PrivateStateAttr]
    obs_model_started_at: Annotated[NotRequired[float], PrivateStateAttr]
    route_decision: NotRequired[str]


class ObservabilityMiddleware(
    AgentMiddleware[ObservabilityState, ContextT, ResponseT]
):
    """Emit lightweight logs for agent lifecycle and model latency."""

    state_schema = ObservabilityState

    @override
    def before_agent(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return {"obs_started_at": time.time()}

    async def abefore_agent(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.before_agent(state, runtime)

    @override
    def before_model(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return {"obs_model_started_at": time.time()}

    async def abefore_model(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.before_model(state, runtime)

    @override
    def after_model(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        model_start = state.get("obs_model_started_at")
        if model_start is not None:
            model_ms = int((time.time() - model_start) * 1000)
            route = state.get("route_decision", "unknown")
            logger.info("model_call_completed route=%s latency_ms=%s", route, model_ms)
        return None

    async def aafter_model(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.after_model(state, runtime)

    @override
    def after_agent(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        started_at = state.get("obs_started_at")
        if started_at is not None:
            total_ms = int((time.time() - started_at) * 1000)
            logger.info("agent_turn_completed latency_ms=%s", total_ms)
        return None

    async def aafter_agent(
        self,
        state: ObservabilityState,
        runtime: Any,
    ) -> dict[str, Any] | None:
        return self.after_agent(state, runtime)


__all__ = ["ObservabilityMiddleware"]

