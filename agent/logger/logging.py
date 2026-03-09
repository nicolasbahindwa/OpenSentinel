"""Structured logging with error caching for OpenSentinel.

Uses structlog for structured JSON logging and maintains an in-memory
ring buffer of recent errors for diagnostics and middleware inspection.
"""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime, timezone
from typing import Any

import structlog


# ---------------------------------------------------------------------------
# Error cache — thread-safe ring buffer of recent errors
# ---------------------------------------------------------------------------

_ERROR_CACHE_MAX = 200
_error_lock = threading.Lock()
_error_cache: deque[dict[str, Any]] = deque(maxlen=_ERROR_CACHE_MAX)


def _cache_errors(
    logger: structlog.types.WrappedLogger,
    method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor: cache ERROR and CRITICAL events."""
    level = event_dict.get("level", "")
    if level in ("error", "critical"):
        entry = {
            "timestamp": event_dict.get(
                "timestamp", datetime.now(timezone.utc).isoformat()
            ),
            "level": level,
            "event": event_dict.get("event", ""),
            "logger": event_dict.get("logger", ""),
            **{
                k: v
                for k, v in event_dict.items()
                if k not in ("timestamp", "level", "event", "logger", "_record")
            },
        }
        with _error_lock:
            _error_cache.append(entry)
    return event_dict


def get_cached_errors(last_n: int | None = None) -> list[dict[str, Any]]:
    """Return a snapshot of cached errors, newest last.

    Args:
        last_n: If given, return only the *last_n* most recent errors.
    """
    with _error_lock:
        items = list(_error_cache)
    if last_n is not None:
        items = items[-last_n:]
    return items


def clear_cached_errors() -> int:
    """Clear the error cache, returning the number of entries removed."""
    with _error_lock:
        count = len(_error_cache)
        _error_cache.clear()
    return count


# ---------------------------------------------------------------------------
# Structlog configuration
# ---------------------------------------------------------------------------

_configured = False


def configure_logging(
    *,
    json_output: bool = True,
    log_level: str = "INFO",
) -> None:
    """Configure structlog once for the whole process.

    Call this early in application startup (e.g. in ``agent.py``).

    Args:
        json_output: If True render logs as JSON lines; otherwise use
                     coloured console output (useful for local development).
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    global _configured
    if _configured:
        return
    _configured = True

    import logging

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        _cache_errors,
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Also route stdlib logging through structlog so existing
    # ``logging.getLogger()`` calls get the same structured output.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, log_level.upper(), logging.INFO))


# ---------------------------------------------------------------------------
# Public API — get_logger
# ---------------------------------------------------------------------------


def get_logger(name: str | None = None, **initial_binds: Any) -> structlog.stdlib.BoundLogger:
    """Return a structlog bound logger.

    Args:
        name: Logger name (e.g. ``"agent.tools.weather"``).
              Passed to stdlib ``getLogger`` under the hood.
        **initial_binds: Key-value pairs permanently bound to every log
                         entry from this logger.

    Example::

        from agent.logger import get_logger
        log = get_logger("agent.middleware.routing", component="routing")
        log.info("route_matched", route="weather", latency_ms=42)
    """
    log = structlog.get_logger(name)
    if initial_binds:
        log = log.bind(**initial_binds)
    return log
