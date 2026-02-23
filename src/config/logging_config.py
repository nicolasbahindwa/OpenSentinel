"""
Logging configuration.

Contains settings for log output, formats, rotation, and sensitive data handling.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from .base import BaseConfig, LogLevel, LogFormat, expand_path


@dataclass
class LoggingConfig(BaseConfig):
    """
    Logging configuration.

    Attributes:
        log_level: Minimum log level to output
        log_format: Output format (json or text)
        log_output: Where to send logs (console, file, both)
        log_file_path: Path to log file
        log_file_rotation: Rotation strategy (size or time)
        log_file_max_bytes: Max file size before rotation (if size-based)
        log_file_backup_count: Number of backup files to keep
        redact_sensitive_data: Automatically redact API keys, passwords, etc.
    """

    log_level: LogLevel = LogLevel.INFO
    log_format: LogFormat = LogFormat.TEXT
    log_output: str = "both"  # console, file, both
    log_file_path: Path = field(
        default_factory=lambda: Path.home() / ".opensentinel" / "logs" / "opensentinel.log"
    )
    log_file_rotation: str = "size"  # size or time
    log_file_max_bytes: int = 10 * 1024 * 1024  # 10 MB
    log_file_backup_count: int = 5
    redact_sensitive_data: bool = True

    @classmethod
    def from_env(cls) -> "LoggingConfig":
        """Load logging configuration from environment variables"""
        # Parse log level
        log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
        try:
            log_level = LogLevel(log_level_str)
        except ValueError:
            log_level = LogLevel.INFO

        # Parse log format
        log_format_str = os.getenv("LOG_FORMAT", "text").lower()
        try:
            log_format = LogFormat(log_format_str)
        except ValueError:
            log_format = LogFormat.TEXT

        # Parse log file path with expansion
        log_file = expand_path(
            os.getenv("LOG_FILE_PATH", "~/.opensentinel/logs/opensentinel.log")
        )

        return cls(
            log_level=log_level,
            log_format=log_format,
            log_output=os.getenv("LOG_OUTPUT", "both"),
            log_file_path=Path(log_file),
            log_file_rotation=os.getenv("LOG_FILE_ROTATION", "size"),
            log_file_max_bytes=int(os.getenv("LOG_FILE_MAX_BYTES", str(10 * 1024 * 1024))),
            log_file_backup_count=int(os.getenv("LOG_FILE_BACKUP_COUNT", "5")),
            redact_sensitive_data=os.getenv("REDACT_SENSITIVE_DATA", "true").lower() in ("true", "1", "yes"),
        )

    def validate(self) -> List[str]:
        """Validate logging configuration"""
        errors = []

        # Validate log output
        valid_outputs = ["console", "file", "both"]
        if self.log_output not in valid_outputs:
            errors.append(
                f"LoggingConfig: log_output must be one of {valid_outputs}, got '{self.log_output}'"
            )

        # Validate rotation strategy
        valid_rotations = ["size", "time"]
        if self.log_file_rotation not in valid_rotations:
            errors.append(
                f"LoggingConfig: log_file_rotation must be one of {valid_rotations}, got '{self.log_file_rotation}'"
            )

        # Validate file size
        if self.log_file_max_bytes < 1024:  # Minimum 1 KB
            errors.append(
                f"LoggingConfig: log_file_max_bytes must be at least 1024 bytes, got {self.log_file_max_bytes}"
            )

        # Validate backup count
        if self.log_file_backup_count < 0:
            errors.append(
                f"LoggingConfig: log_file_backup_count must be non-negative, got {self.log_file_backup_count}"
            )

        # Ensure log directory can be created (if file output enabled)
        if self.log_output in ["file", "both"]:
            try:
                self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"LoggingConfig: Cannot create log directory: {e}")

        return errors

    def ensure_log_directory(self):
        """Create log directory if it doesn't exist"""
        self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
