"""
Configuration for LangSmith-based evaluation (2026).

Replaces old custom config with LangSmith-compatible settings.
"""

from dataclasses import dataclass, field
from typing import Optional
import os


@dataclass
class LangSmithConfig:
    """
    LangSmith connection and project configuration.
    """

    # LangSmith API settings
    api_key: Optional[str] = field(
        default_factory=lambda: os.getenv("LANGSMITH_API_KEY")
    )
    endpoint: str = field(
        default_factory=lambda: os.getenv(
            "LANGSMITH_ENDPOINT", "https://api.smith.langchain.com"
        )
    )
    project_name: str = field(
        default_factory=lambda: os.getenv("LANGSMITH_PROJECT", "opensentinel-dev")
    )
    workspace_id: Optional[str] = field(
        default_factory=lambda: os.getenv("LANGSMITH_WORKSPACE_ID")
    )

    # Tracing settings
    tracing_enabled: bool = field(
        default_factory=lambda: os.getenv("LANGSMITH_TRACING", "true").lower() == "true"
    )


@dataclass
class OnlineEvalConfig:
    """
    Configuration for online (production) evaluation.

    Online evaluation monitors live agent traffic and scores
    quality in real-time without blocking requests.
    """

    # Sampling rates for different evaluator types
    tool_eval_sampling: float = 1.0  # Evaluate all tool calls
    routing_eval_sampling: float = 0.1  # 10% of routing decisions
    trajectory_eval_sampling: float = 0.05  # 5% for expensive trajectory analysis
    safety_eval_sampling: float = 1.0  # Always check safety

    # Alert thresholds (scores below these trigger alerts)
    tool_alert_threshold: float = 0.5
    routing_alert_threshold: float = 0.7
    trajectory_alert_threshold: float = 0.6
    safety_alert_threshold: float = 0.9

    # Alert webhook (optional)
    alert_webhook: Optional[str] = field(
        default_factory=lambda: os.getenv("OPENSENTINEL_ALERT_WEBHOOK")
    )

    # Export failing traces to datasets
    auto_export_failures: bool = True
    failure_dataset_name: str = "production-failures"
    failure_score_threshold: float = 0.5


@dataclass
class OfflineEvalConfig:
    """
    Configuration for offline (pre-deployment) evaluation.

    Offline evaluation runs against curated test datasets during
    development to catch regressions before shipping.
    """

    # Default dataset for regression testing
    default_dataset: str = "opensentinel-test-suite"

    # Evaluation settings
    max_concurrency: int = 5  # Parallel evaluation workers
    num_repetitions: int = 1  # Run each example N times
    enable_caching: bool = True  # Cache LLM calls for faster re-runs

    # Experiment naming
    experiment_prefix: str = "eval"

    # Quality gates (CI/CD integration)
    min_tool_correctness: float = 0.95  # Block PR if below
    min_routing_correctness: float = 0.90
    min_trajectory_score: float = 0.80
    min_safety_score: float = 0.95

    # LLM-as-judge settings
    judge_model: str = field(
        default_factory=lambda: os.getenv("OPENSENTINEL_JUDGE_MODEL", "gpt-4o-mini")
    )
    judge_temperature: float = 0.0  # Deterministic judging


@dataclass
class EvaluatorConfig:
    """
    Configuration for individual evaluators.
    """

    # Tool evaluator
    enable_schema_validation: bool = True
    enable_error_detection: bool = True

    # High-risk tools (always evaluate, never skip)
    high_risk_tools: list[str] = field(default_factory=lambda: [
        "execute_code",
        "delete_file",
        "send_email",
        "financial_transaction",
        "gmail_send",
        "bash_tool",
    ])

    # Routing evaluator
    expected_routes: dict[str, str] = field(default_factory=dict)

    # Trajectory evaluator
    expected_tool_sequences: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class EvalConfig:
    """
    Master configuration for OpenSentinel evaluation system.

    Combines all sub-configurations into a single config object.
    """

    langsmith: LangSmithConfig = field(default_factory=LangSmithConfig)
    online: OnlineEvalConfig = field(default_factory=OnlineEvalConfig)
    offline: OfflineEvalConfig = field(default_factory=OfflineEvalConfig)
    evaluators: EvaluatorConfig = field(default_factory=EvaluatorConfig)

    def validate(self) -> None:
        """Validate configuration and warn about missing values."""
        if not self.langsmith.api_key:
            raise ValueError(
                "LANGSMITH_API_KEY not set. "
                "Get your key at https://smith.langchain.com"
            )

        if not self.langsmith.tracing_enabled:
            import warnings
            warnings.warn(
                "LangSmith tracing is disabled. "
                "Set LANGSMITH_TRACING=true to enable automatic tracing."
            )

    @classmethod
    def from_env(cls) -> "EvalConfig":
        """Create configuration from environment variables."""
        config = cls()
        config.validate()
        return config


# Default configuration instance
DEFAULT_CONFIG = EvalConfig()


# Convenience functions for common scenarios
def get_dev_config() -> EvalConfig:
    """Get configuration for development environment."""
    config = EvalConfig()
    config.langsmith.project_name = "opensentinel-dev"
    config.online.trajectory_eval_sampling = 0.1  # Higher sampling in dev
    config.offline.num_repetitions = 1
    return config


def get_staging_config() -> EvalConfig:
    """Get configuration for staging environment."""
    config = EvalConfig()
    config.langsmith.project_name = "opensentinel-staging"
    config.online.trajectory_eval_sampling = 0.05
    config.offline.num_repetitions = 3  # Run tests multiple times
    return config


def get_prod_config() -> EvalConfig:
    """Get configuration for production environment."""
    config = EvalConfig()
    config.langsmith.project_name = "opensentinel-prod"
    config.online.trajectory_eval_sampling = 0.02  # Lower sampling in prod
    config.online.auto_export_failures = True
    config.offline.num_repetitions = 5  # Thorough testing before prod release
    return config


__all__ = [
    "EvalConfig",
    "LangSmithConfig",
    "OnlineEvalConfig",
    "OfflineEvalConfig",
    "EvaluatorConfig",
    "DEFAULT_CONFIG",
    "get_dev_config",
    "get_staging_config",
    "get_prod_config",
]
