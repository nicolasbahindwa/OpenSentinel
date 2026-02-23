"""
Production-Grade Logging System for OpenSentinel

Features:
- Structured JSON logging for production
- Human-readable text logging for development
- Automatic log rotation (size and time-based)
- Sensitive data redaction
- Context managers for operation tracking
- Performance metrics logging
- Multiple output destinations (console, file, both)
- Thread-safe logging

Usage:
    from logging import get_logger

    logger = get_logger(__name__)
    logger.info("Application started", extra={"version": "2.0.0"})

    # With operation tracking
    with logger.operation("process_email"):
        # Your code here
        logger.info("Email processed", extra={"email_id": "12345"})
"""

import logging
import logging.handlers
import json
import sys
import re
import time
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
from datetime import datetime

from config import settings, LogLevel, LogFormat


# ══════════════════════════════════════════════════════════════════════════
# CUSTOM FORMATTERS
# ══════════════════════════════════════════════════════════════════════════

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs as JSON objects with:
    - timestamp (ISO 8601)
    - level
    - logger name
    - message
    - extra fields
    - exception info (if present)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Redact sensitive data if enabled
        if settings.logging.redact_sensitive_data:
            log_data = self._redact_sensitive(log_data)

        return json.dumps(log_data)

    def _redact_sensitive(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive information from log data"""
        sensitive_patterns = [
            (r'api[_-]?key["\s:=]+[\w\-]+', 'api_key="***REDACTED***"'),
            (r'password["\s:=]+[\w\-]+', 'password="***REDACTED***"'),
            (r'token["\s:=]+[\w\-]+', 'token="***REDACTED***"'),
            (r'secret["\s:=]+[\w\-]+', 'secret="***REDACTED***"'),
            (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '***EMAIL_REDACTED***'),
        ]

        def redact_string(text: str) -> str:
            for pattern, replacement in sensitive_patterns:
                text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            return text

        # Redact message
        if "message" in data and isinstance(data["message"], str):
            data["message"] = redact_string(data["message"])

        # Redact extra fields
        for key, value in data.items():
            if isinstance(value, str):
                data[key] = redact_string(value)
            elif isinstance(value, dict):
                data[key] = self._redact_sensitive(value)

        return data


class ColoredTextFormatter(logging.Formatter):
    """
    Colored text formatter for console output.

    Adds colors to log levels for better readability in development.
    """

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors"""
        # Add color to level name
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"

        # Format the message
        formatted = super().format(record)

        return formatted


# ══════════════════════════════════════════════════════════════════════════
# LOGGER SETUP
# ══════════════════════════════════════════════════════════════════════════

def setup_logging() -> None:
    """
    Setup logging configuration based on settings.

    This should be called once at application startup.
    """
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.logging.log_level.value))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Choose formatter based on configuration
    if settings.logging.log_format == LogFormat.JSON:
        formatter = JSONFormatter()
    else:
        if settings.is_development():
            formatter = ColoredTextFormatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        else:
            formatter = logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )

    # Console handler
    if settings.logging.log_output in ["console", "both"]:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)

    # File handler with rotation
    if settings.logging.log_output in ["file", "both"]:
        # Ensure log directory exists
        log_file = settings.logging.log_file_path
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if settings.logging.log_file_rotation == "size":
            # Size-based rotation
            file_handler = logging.handlers.RotatingFileHandler(
                filename=log_file,
                maxBytes=settings.logging.log_file_max_bytes,
                backupCount=settings.logging.log_file_backup_count,
                encoding="utf-8",
            )
        else:
            # Time-based rotation (daily)
            file_handler = logging.handlers.TimedRotatingFileHandler(
                filename=log_file,
                when="midnight",
                interval=1,
                backupCount=settings.logging.log_file_backup_count,
                encoding="utf-8",
            )

        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Log startup message
    root_logger.info(
        "Logging system initialized",
        extra={
            "log_level": settings.logging.log_level.value,
            "log_format": settings.logging.log_format.value,
            "log_output": settings.logging.log_output,
        },
    )


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ══════════════════════════════════════════════════════════════════════════
# CONTEXT MANAGERS FOR OPERATION TRACKING
# ══════════════════════════════════════════════════════════════════════════

class OperationLogger:
    """
    Context manager for tracking operations with automatic timing.

    Usage:
        logger = get_logger(__name__)
        with OperationLogger(logger, "process_email", email_id="12345"):
            # Your code here
            pass
    """

    def __init__(
        self,
        logger: logging.Logger,
        operation: str,
        level: int = logging.INFO,
        **extra
    ):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.extra = extra
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(
            self.level,
            f"Operation started: {self.operation}",
            extra=self.extra,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time

        if exc_type is None:
            self.logger.log(
                self.level,
                f"Operation completed: {self.operation}",
                extra={
                    **self.extra,
                    "duration_seconds": round(duration, 3),
                    "status": "success",
                },
            )
        else:
            self.logger.error(
                f"Operation failed: {self.operation}",
                exc_info=(exc_type, exc_val, exc_tb),
                extra={
                    **self.extra,
                    "duration_seconds": round(duration, 3),
                    "status": "error",
                    "error_type": exc_type.__name__ if exc_type else None,
                },
            )

        # Don't suppress exceptions
        return False


# Convenience function
@contextmanager
def operation(operation_name: str, logger: Optional[logging.Logger] = None, **extra):
    """
    Convenience context manager for operation tracking.

    Args:
        operation_name: Name of the operation
        logger: Logger instance (or use root logger)
        **extra: Additional context to log

    Usage:
        with operation("process_email", email_id="123"):
            # Your code
            pass
    """
    if logger is None:
        logger = logging.getLogger()

    with OperationLogger(logger, operation_name, **extra):
        yield


# ══════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def log_exception(logger: logging.Logger, message: str, **extra):
    """
    Log an exception with full traceback.

    Args:
        logger: Logger instance
        message: Error message
        **extra: Additional context
    """
    logger.exception(message, extra=extra)


def log_performance(
    logger: logging.Logger,
    operation: str,
    duration_seconds: float,
    **extra
):
    """
    Log performance metrics for an operation.

    Args:
        logger: Logger instance
        operation: Operation name
        duration_seconds: How long it took
        **extra: Additional metrics
    """
    logger.info(
        f"Performance: {operation}",
        extra={
            "operation": operation,
            "duration_seconds": round(duration_seconds, 3),
            **extra,
        },
    )


def log_security_event(
    logger: logging.Logger,
    event_type: str,
    severity: str,
    details: Dict[str, Any],
):
    """
    Log a security-related event.

    Args:
        logger: Logger instance
        event_type: Type of security event
        severity: low, medium, high, critical
        details: Event details
    """
    logger.warning(
        f"Security event: {event_type}",
        extra={
            "event_type": event_type,
            "severity": severity,
            "security_event": True,
            **details,
        },
    )


# ══════════════════════════════════════════════════════════════════════════
# INITIALIZE LOGGING ON MODULE IMPORT
# ══════════════════════════════════════════════════════════════════════════

# Auto-setup logging when module is imported
try:
    setup_logging()
except Exception as e:
    # Fallback to basic logging if setup fails
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )
    logging.error(f"Failed to setup logging system: {e}")
