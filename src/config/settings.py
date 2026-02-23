"""
Production-Grade Configuration Management for OpenSentinel

Main settings aggregator that brings together all configuration sections.

Features:
- Type-safe configuration with dataclasses
- Environment variable loading with validation
- Support for .env files
- Proper defaults for all settings
- Configuration validation on startup
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

import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

# Import all configuration sections
from .core import CoreConfig
from .cache import CacheConfig
from .security import SecurityConfig
from .logging_config import LoggingConfig
from .metrics import MetricsConfig
from .external_apis import ExternalAPIsConfig
from .base import Environment


# ══════════════════════════════════════════════════════════════════════════
# MAIN SETTINGS CLASS
# ══════════════════════════════════════════════════════════════════════════

@dataclass
class Settings:
    """
    Main settings class that aggregates all configuration sections.

    This is the single source of truth for all application configuration.
    Load it once at startup and use throughout the application.

    Attributes:
        core: Core application settings
        cache: Cache configuration
        security: Security and permissions configuration
        logging: Logging configuration
        metrics: Metrics and telemetry configuration
        external_apis: External APIs configuration
    """

    core: CoreConfig
    cache: CacheConfig
    security: SecurityConfig
    logging: LoggingConfig
    metrics: MetricsConfig
    external_apis: ExternalAPIsConfig

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Load all configuration from environment variables.

        This should be called once at application startup.

        Returns:
            Settings: Fully loaded and validated settings

        Raises:
            ValueError: If configuration validation fails
        """
        # Load environment variables from .env file if present
        cls._load_env_file()

        # Load each configuration section
        settings = cls(
            core=CoreConfig.from_env(),
            cache=CacheConfig.from_env(),
            security=SecurityConfig.from_env(),
            logging=LoggingConfig.from_env(),
            metrics=MetricsConfig.from_env(),
            external_apis=ExternalAPIsConfig.from_env(),
        )

        # Validate configuration
        errors = settings.validate()
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {err}" for err in errors)
            raise ValueError(error_msg)

        return settings

    @staticmethod
    def _load_env_file():
        """Load environment variables from .env file if present"""
        env_file = Path.cwd() / ".env"
        if env_file.exists():
            try:
                from dotenv import load_dotenv
                load_dotenv(env_file)
            except ImportError:
                # python-dotenv not installed, try manual parsing
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
                            os.environ.setdefault(key.strip(), value.strip())

    def validate(self) -> List[str]:
        """
        Validate all configuration sections.

        Returns:
            List[str]: List of validation errors (empty if valid)
        """
        errors = []

        # Validate each section
        errors.extend(self.core.validate())
        errors.extend(self.cache.validate())
        errors.extend(self.security.validate())
        errors.extend(self.logging.validate())
        errors.extend(self.metrics.validate())
        errors.extend(self.external_apis.validate())

        # Cross-section validation
        errors.extend(self._validate_cross_section())

        return errors

    def _validate_cross_section(self) -> List[str]:
        """
        Validate configuration across multiple sections.

        Returns:
            List[str]: List of cross-section validation errors
        """
        errors = []

        # Production environment checks
        if self.core.environment == Environment.PRODUCTION:
            # Ensure debug mode is disabled
            if self.core.debug:
                errors.append("DEBUG mode must be disabled in production")

            # Ensure logging is set to file or both in production
            if self.logging.log_output == "console":
                errors.append("Production logging should write to file (set LOG_OUTPUT=file or both)")

            # Warn if sensitive data redaction is disabled
            if not self.logging.redact_sensitive_data:
                errors.append("Sensitive data redaction should be enabled in production")

        return errors

    # ═══════════════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS
    # ═══════════════════════════════════════════════════════════════════════

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.core.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.core.environment == Environment.DEVELOPMENT

    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.core.environment == Environment.STAGING

    def ensure_directories(self):
        """
        Ensure all necessary directories exist.

        Creates directories for:
        - Logs
        - Permissions configuration
        - Audit logs
        """
        self.security.ensure_directories()
        self.logging.ensure_log_directory()


# ══════════════════════════════════════════════════════════════════════════
# GLOBAL SETTINGS INSTANCE (SINGLETON)
# ══════════════════════════════════════════════════════════════════════════

_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get the global settings instance.

    Loads settings on first call, then returns cached instance.

    Returns:
        Settings: Global settings instance

    Usage:
        from config import get_settings

        settings = get_settings()
        log_level = settings.logging.log_level
    """
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
        _settings.ensure_directories()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload of settings from environment.

    Useful for testing. In production, settings should be loaded once.

    Returns:
        Settings: Newly loaded settings instance
    """
    global _settings
    _settings = Settings.from_env()
    _settings.ensure_directories()
    return _settings


# Create global settings instance on module import
settings = get_settings()
