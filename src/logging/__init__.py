"""
Professional logging system for OpenSentinel.

Provides:
- Structured JSON logging for production
- Colored text logging for development
- Automatic log rotation
- Sensitive data redaction
- Operation tracking with timing
- Security event logging

Usage:
    from logging import get_logger, operation, log_security_event

    logger = get_logger(__name__)
    logger.info("Message", extra={"key": "value"})

    # Track operations with automatic timing
    with operation("process_task", task_id="123"):
        # Your code here
        pass

    # Log security events
    log_security_event(
        logger,
        event_type="unauthorized_access",
        severity="high",
        details={"user_id": "123", "resource": "/admin"}
    )
"""

from .logger import (
    setup_logging,
    get_logger,
    operation,
    log_exception,
    log_performance,
    log_security_event,
    OperationLogger,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "operation",
    "log_exception",
    "log_performance",
    "log_security_event",
    "OperationLogger",
]
