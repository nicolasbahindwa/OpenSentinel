"""
Provider-neutral observability configuration.

Observability backends (Sentry, Prometheus, OTLP collectors, etc.) are
integration concerns and should be wired by the orchestrator/adapters.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

from .base import BaseConfig, get_env_bool


@dataclass
class MetricsConfig(BaseConfig):
    """
    Observability configuration.

    Attributes:
        observability_enabled: Master switch for observability
        traces_enabled: Enable distributed traces
        metrics_enabled: Enable application metrics
        logs_enabled: Enable structured logs export
        telemetry_enabled: Enable anonymous product telemetry
        exporter: Exporter type (none, console, otlp, custom)
        endpoint: Export endpoint (required for otlp/custom exporters)
        headers: Optional headers for exporter auth/routing
        sample_rate: Trace/sample rate (0.0-1.0)
        custom_metrics_enabled: Enable application-defined metrics
    """

    observability_enabled: bool = True
    traces_enabled: bool = True
    metrics_enabled: bool = True
    logs_enabled: bool = True
    telemetry_enabled: bool = False

    exporter: str = "none"
    endpoint: Optional[str] = None
    headers: Optional[str] = None
    sample_rate: float = 0.1

    custom_metrics_enabled: bool = True

    @classmethod
    def from_env(cls) -> "MetricsConfig":
        """Load observability configuration from environment variables."""
        exporter = os.getenv("OBSERVABILITY_EXPORTER", "none")
        endpoint = os.getenv("OBSERVABILITY_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
        headers = os.getenv("OBSERVABILITY_HEADERS") or os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
        sample_rate_raw = os.getenv("OBSERVABILITY_SAMPLE_RATE") or os.getenv("OTEL_TRACES_SAMPLER_ARG") or "0.1"

        return cls(
            observability_enabled=get_env_bool("OBSERVABILITY_ENABLED", True),
            traces_enabled=get_env_bool("TRACES_ENABLED", True),
            metrics_enabled=get_env_bool("METRICS_ENABLED", True),
            logs_enabled=get_env_bool("LOGS_ENABLED", True),
            telemetry_enabled=get_env_bool("TELEMETRY_ENABLED", False),
            exporter=exporter.lower(),
            endpoint=endpoint,
            headers=headers,
            sample_rate=float(sample_rate_raw),
            custom_metrics_enabled=get_env_bool("CUSTOM_METRICS_ENABLED", True),
        )

    def validate(self) -> List[str]:
        """Validate observability configuration."""
        errors = []

        valid_exporters = {"none", "console", "otlp", "custom"}
        if self.exporter not in valid_exporters:
            errors.append(
                f"MetricsConfig: exporter must be one of {sorted(valid_exporters)}, got '{self.exporter}'"
            )

        if self.exporter in {"otlp", "custom"} and not self.endpoint:
            errors.append("MetricsConfig: endpoint is required when exporter is 'otlp' or 'custom'")

        if self.endpoint and not (
            self.endpoint.startswith("http://")
            or self.endpoint.startswith("https://")
            or self.endpoint.startswith("grpc://")
        ):
            errors.append(
                "MetricsConfig: endpoint must start with http://, https://, or grpc://"
            )

        if not (0.0 <= self.sample_rate <= 1.0):
            errors.append(
                f"MetricsConfig: sample_rate must be between 0.0-1.0, got {self.sample_rate}"
            )

        return errors
