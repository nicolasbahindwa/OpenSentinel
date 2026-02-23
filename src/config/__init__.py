"""
Configuration module for OpenSentinel.

Provides production-grade configuration management with:
- Type-safe settings from environment variables
- Validation on startup
- Singleton pattern for global access
- Separation of concerns (Cache, Security, observability, etc.)

Usage:
    from config import settings

    # Access configuration
    log_level = settings.logging.log_level

    # Check environment
    if settings.is_production():
        # Production-specific logic
        pass
"""

# ═══════════════════════════════════════════════════════════════════════════
# MAIN EXPORTS (Most commonly used)
# ═══════════════════════════════════════════════════════════════════════════

from .settings import (
    Settings,
    get_settings,
    reload_settings,
    settings,  # Global singleton instance
)

# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION SECTIONS (For direct access if needed)
# ═══════════════════════════════════════════════════════════════════════════

from .core import CoreConfig
from .cache import CacheConfig
from .security import SecurityConfig
from .logging_config import LoggingConfig
from .metrics import MetricsConfig
from .external_apis import ExternalAPIsConfig

# ═══════════════════════════════════════════════════════════════════════════
# ENUMS (For type checking and validation)
# ═══════════════════════════════════════════════════════════════════════════

from .base import (
    Environment,
    LogLevel,
    LogFormat,
    CacheBackend,
    RoutingStrategy,
)

# ═══════════════════════════════════════════════════════════════════════════
# UTILITY FUNCTIONS (Helper functions for config parsing)
# ═══════════════════════════════════════════════════════════════════════════

from .base import (
    get_env_bool,
    get_env_int,
    get_env_float,
    get_env_list,
    expand_path,
    validate_api_key,
    validate_url,
    validate_port,
)


# ═══════════════════════════════════════════════════════════════════════════
# __ALL__ DEFINITION (Controls "from config import *")
# ═══════════════════════════════════════════════════════════════════════════

__all__ = [
    # ───────────────────────────────────────────────────────────────────────
    # Main Settings (Primary interface)
    # ───────────────────────────────────────────────────────────────────────
    "settings",          # Global singleton - USE THIS for most cases
    "get_settings",      # Function to get global singleton
    "reload_settings",   # Function to reload (testing only)
    "Settings",          # Settings class (rarely needed directly)

    # ───────────────────────────────────────────────────────────────────────
    # Configuration Sections
    # ───────────────────────────────────────────────────────────────────────
    "CoreConfig",
    "CacheConfig",
    "SecurityConfig",
    "LoggingConfig",
    "MetricsConfig",
    "ExternalAPIsConfig",

    # ───────────────────────────────────────────────────────────────────────
    # Enums
    # ───────────────────────────────────────────────────────────────────────
    "Environment",
    "LogLevel",
    "LogFormat",
    "CacheBackend",
    "RoutingStrategy",

    # ───────────────────────────────────────────────────────────────────────
    # Utility Functions
    # ───────────────────────────────────────────────────────────────────────
    "get_env_bool",
    "get_env_int",
    "get_env_float",
    "get_env_list",
    "expand_path",
    "validate_api_key",
    "validate_url",
    "validate_port",
]
