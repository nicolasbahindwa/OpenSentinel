"""
Core application configuration.

Contains fundamental settings like app name, version, environment, and secrets.
"""

import os
import secrets
from dataclasses import dataclass
from typing import List

from .base import BaseConfig, Environment, get_env_bool


@dataclass
class CoreConfig(BaseConfig):
    """
    Core application settings.

    Attributes:
        app_name: Application name
        app_version: Application version
        environment: Runtime environment (development, staging, production)
        debug: Debug mode flag (NEVER enable in production)
        secret_key: Secret key for encryption (auto-generated if not provided)
    """

    app_name: str = "OpenSentinel"
    app_version: str = "2.0.0"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    secret_key: str = ""

    def __post_init__(self):
        """Generate secret key if not provided"""
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(32)

    @classmethod
    def from_env(cls) -> "CoreConfig":
        """Load core configuration from environment variables"""
        return cls(
            app_name=os.getenv("APP_NAME", "OpenSentinel"),
            app_version=os.getenv("APP_VERSION", "2.0.0"),
            environment=Environment(os.getenv("OPENSENTINEL_ENV", "development")),
            debug=get_env_bool("DEBUG", False),
            secret_key=os.getenv("SECRET_KEY", ""),
        )

    def validate(self) -> List[str]:
        """Validate core configuration"""
        errors = []

        # Validate environment-specific rules
        if self.environment == Environment.PRODUCTION:
            if self.debug:
                errors.append("CoreConfig: DEBUG mode must be disabled in production")

            if len(self.secret_key) < 32:
                errors.append("CoreConfig: SECRET_KEY must be at least 32 characters in production")

        # Validate secret key length
        if self.secret_key and len(self.secret_key) < 16:
            errors.append("CoreConfig: SECRET_KEY must be at least 16 characters")

        return errors

    def is_production(self) -> bool:
        """Check if running in production environment"""
        return self.environment == Environment.PRODUCTION

    def is_development(self) -> bool:
        """Check if running in development environment"""
        return self.environment == Environment.DEVELOPMENT

    def is_staging(self) -> bool:
        """Check if running in staging environment"""
        return self.environment == Environment.STAGING
