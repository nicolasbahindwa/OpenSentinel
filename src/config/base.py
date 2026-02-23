"""
Base configuration classes and shared utilities.

Provides abstract base classes and common patterns that all config
sections can inherit from.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum


# ══════════════════════════════════════════════════════════════════════════
# ENUMS
# ══════════════════════════════════════════════════════════════════════════

class Environment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """Logging levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(str, Enum):
    """Log output format"""
    JSON = "json"
    TEXT = "text"


class CacheBackend(str, Enum):
    """Cache backend type"""
    MEMORY = "memory"
    REDIS = "redis"


class RoutingStrategy(str, Enum):
    """LLM routing strategy"""
    COST = "cost"
    QUALITY = "quality"
    SPEED = "speed"
    BALANCED = "balanced"
    COMPLEXITY = "complexity"


# ══════════════════════════════════════════════════════════════════════════
# BASE CLASSES
# ══════════════════════════════════════════════════════════════════════════

class BaseConfig(ABC):
    """
    Abstract base class for all configuration sections.

    Provides common interface for loading from environment and validation.
    """

    @classmethod
    @abstractmethod
    def from_env(cls) -> "BaseConfig":
        """
        Load configuration from environment variables.

        Must be implemented by all config sections.
        """
        pass

    def validate(self) -> List[str]:
        """
        Validate configuration and return list of errors.

        Override this method to add section-specific validation.

        Returns:
            List of validation error messages (empty if valid)
        """
        return []

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert configuration to dictionary.

        By default, uses dataclass fields. Override for custom behavior.
        """
        if hasattr(self, "__dataclass_fields__"):
            return {
                field: getattr(self, field)
                for field in self.__dataclass_fields__
            }
        return {}


# ══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════

def get_env_bool(key: str, default: bool = False) -> bool:
    """
    Get boolean value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Boolean value
    """
    value = os.getenv(key, str(default))
    return value.lower() in ("true", "1", "yes", "on")


def get_env_int(key: str, default: int) -> int:
    """
    Get integer value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Integer value
    """
    try:
        return int(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_float(key: str, default: float) -> float:
    """
    Get float value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set

    Returns:
        Float value
    """
    try:
        return float(os.getenv(key, str(default)))
    except ValueError:
        return default


def get_env_list(key: str, default: Optional[List[str]] = None, separator: str = ",") -> List[str]:
    """
    Get list value from environment variable.

    Args:
        key: Environment variable name
        default: Default value if not set
        separator: String separator (default: comma)

    Returns:
        List of strings
    """
    if default is None:
        default = []

    value = os.getenv(key, "")
    if not value:
        return default

    return [item.strip() for item in value.split(separator) if item.strip()]


def get_env_optional(key: str) -> Optional[str]:
    """
    Get optional string value from environment variable.

    Args:
        key: Environment variable name

    Returns:
        String value or None if not set
    """
    value = os.getenv(key)
    return value if value else None


def expand_path(path: str) -> str:
    """
    Expand user home directory and environment variables in path.

    Args:
        path: Path string (may contain ~ or $VAR)

    Returns:
        Expanded path
    """
    return os.path.expanduser(os.path.expandvars(path))


# ══════════════════════════════════════════════════════════════════════════
# VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════════════════

def validate_api_key(key: Optional[str], provider_name: str, required: bool = True) -> Optional[str]:
    """
    Validate API key format and presence.

    Args:
        key: API key to validate
        provider_name: Name of the provider (for error messages)
        required: Whether the key is required

    Returns:
        Error message if invalid, None if valid
    """
    if not key:
        if required:
            return f"{provider_name}: API key is required"
        return None

    if len(key) < 10:
        return f"{provider_name}: API key seems too short (minimum 10 characters)"

    return None


def validate_url(url: Optional[str], field_name: str, required: bool = False) -> Optional[str]:
    """
    Validate URL format.

    Args:
        url: URL to validate
        field_name: Name of the field (for error messages)
        required: Whether the URL is required

    Returns:
        Error message if invalid, None if valid
    """
    if not url:
        if required:
            return f"{field_name}: URL is required"
        return None

    if not (url.startswith("http://") or url.startswith("https://")):
        return f"{field_name}: URL must start with http:// or https://"

    return None


def validate_port(port: int, field_name: str) -> Optional[str]:
    """
    Validate port number.

    Args:
        port: Port number to validate
        field_name: Name of the field (for error messages)

    Returns:
        Error message if invalid, None if valid
    """
    if port < 1 or port > 65535:
        return f"{field_name}: Port must be between 1 and 65535"

    return None


def validate_file_exists(path: str, field_name: str, required: bool = False) -> Optional[str]:
    """
    Validate that a file exists.

    Args:
        path: File path to validate
        field_name: Name of the field (for error messages)
        required: Whether the file must exist

    Returns:
        Error message if invalid, None if valid
    """
    import os

    if not os.path.exists(path):
        if required:
            return f"{field_name}: File not found at {path}"
        return None

    if not os.path.isfile(path):
        return f"{field_name}: Path exists but is not a file: {path}"

    return None
