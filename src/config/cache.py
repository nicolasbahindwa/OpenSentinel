"""
Cache configuration.

Contains settings for caching layer including memory and Redis backends.
"""

import os
from dataclasses import dataclass
from typing import List, Optional

from .base import (
    BaseConfig,
    CacheBackend,
    get_env_bool,
    get_env_int,
    get_env_optional,
    validate_port,
)


@dataclass
class CacheConfig(BaseConfig):
    """
    Cache configuration.

    Attributes:
        enabled: Whether caching is enabled
        backend: Cache backend type (memory or redis)
        default_ttl_seconds: Default time-to-live for cache entries
        max_size: Maximum cache size (for memory backend)
        redis_host: Redis server hostname
        redis_port: Redis server port
        redis_db: Redis database number
        redis_password: Redis authentication password
        redis_key_prefix: Key prefix for all cache entries
        redis_ssl_enabled: Enable SSL/TLS for Redis connection
    """

    enabled: bool = True
    backend: CacheBackend = CacheBackend.MEMORY
    default_ttl_seconds: int = 3600
    max_size: int = 10000

    # Redis specific
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_key_prefix: str = "opensentinel:"
    redis_ssl_enabled: bool = False

    @classmethod
    def from_env(cls) -> "CacheConfig":
        """Load cache configuration from environment variables"""
        return cls(
            enabled=get_env_bool("CACHE_ENABLED", True),
            backend=CacheBackend(os.getenv("CACHE_BACKEND", "memory")),
            default_ttl_seconds=get_env_int("CACHE_DEFAULT_TTL_SECONDS", 3600),
            max_size=get_env_int("CACHE_MAX_SIZE", 10000),
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=get_env_int("REDIS_PORT", 6379),
            redis_db=get_env_int("REDIS_DB", 0),
            redis_password=get_env_optional("REDIS_PASSWORD"),
            redis_key_prefix=os.getenv("REDIS_KEY_PREFIX", "opensentinel:"),
            redis_ssl_enabled=get_env_bool("REDIS_SSL_ENABLED", False),
        )

    def validate(self) -> List[str]:
        """Validate cache configuration"""
        errors = []

        if self.default_ttl_seconds < 1:
            errors.append("CacheConfig: default_ttl_seconds must be at least 1")

        if self.max_size < 1:
            errors.append("CacheConfig: max_size must be at least 1")

        # Validate Redis-specific settings
        if self.backend == CacheBackend.REDIS:
            if not self.redis_host:
                errors.append("CacheConfig: redis_host is required when using Redis backend")

            if error := validate_port(self.redis_port, "redis_port"):
                errors.append(f"CacheConfig: {error}")

            if self.redis_db < 0:
                errors.append("CacheConfig: redis_db must be non-negative")

            # Check if redis package is available
            try:
                import redis
            except ImportError:
                errors.append("CacheConfig: Redis backend requires 'redis' package: pip install redis")

        return errors

    def is_redis(self) -> bool:
        """Check if using Redis backend"""
        return self.backend == CacheBackend.REDIS

    def is_memory(self) -> bool:
        """Check if using memory backend"""
        return self.backend == CacheBackend.MEMORY
