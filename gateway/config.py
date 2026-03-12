"""Gateway configuration — validated via pydantic-settings."""

from __future__ import annotations

from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import field_validator

    class GatewayConfig(BaseSettings):
        """Settings for the CLI gateway. All fields map to env vars with the
        prefix ``LANGGRAPH_GATEWAY_`` (e.g. ``LANGGRAPH_GATEWAY_URL``)."""

        model_config = SettingsConfigDict(
            env_prefix="LANGGRAPH_GATEWAY_",
            env_file=".env",
            env_file_encoding="utf-8",
            extra="ignore",
        )

        url: str = "http://localhost:2024"
        assistant_id: str = "agent"
        timeout: float = 300.0   # 5 min — browser tasks can be slow
        # Directory where scheduler state is persisted
        state_dir: Path = Path.home() / ".opensentinel"

        @field_validator("timeout", mode="before")
        @classmethod
        def _positive_timeout(cls, v: object) -> float:
            try:
                v = float(v)
            except (TypeError, ValueError):
                raise ValueError(f"timeout must be a number, got {v!r}")
            if v <= 0:
                raise ValueError("timeout must be positive")
            return v

        @field_validator("url", mode="before")
        @classmethod
        def _valid_url(cls, v: object) -> str:
            v = str(v).rstrip("/")
            if not v.startswith(("http://", "https://")):
                raise ValueError(f"url must start with http:// or https://, got {v!r}")
            return v

except ImportError:
    # Fallback when pydantic-settings is not installed
    import os

    class GatewayConfig:  # type: ignore[no-redef]
        """Minimal fallback config (pydantic-settings not available)."""

        def __init__(self) -> None:
            self.url: str = os.getenv("LANGGRAPH_GATEWAY_URL", "http://localhost:2024").rstrip("/")
            self.assistant_id: str = os.getenv("LANGGRAPH_GATEWAY_ASSISTANT_ID", "agent")
            self.state_dir: Path = Path.home() / ".opensentinel"
            try:
                self.timeout: float = float(os.getenv("LANGGRAPH_GATEWAY_TIMEOUT", "300"))
            except ValueError:
                self.timeout = 120.0
