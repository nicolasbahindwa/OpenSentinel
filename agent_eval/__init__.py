"""
OpenSentinel Agent Evaluation (2026 LangSmith).

Modern evaluation framework aligned with LangSmith 2026 best practices:
- Native LangSmith integration
- Online evaluators (UI-configured)
- Offline dataset-driven testing
- Multi-turn conversation evaluation
- Trajectory analysis
- CI/CD quality gates

Quick Start:
    1. Enable tracing in .env:
        LANGSMITH_TRACING=true
        LANGSMITH_API_KEY=your_key

    2. Online evaluation (production):
        >>> from agent_eval import setup_production_tracing
        >>> helper = setup_production_tracing()
        >>> helper.print_setup_instructions()  # Configure in UI

    3. Offline evaluation (development):
        >>> from agent import create_agent
        >>> from agent_eval import OfflineEvaluator
        >>> evaluator = OfflineEvaluator()
        >>> results = evaluator.evaluate_agent(
        ...     agent_or_factory=create_agent(),
        ...     dataset_name="regression-tests"
        ... )

    4. Dataset management:
        >>> from agent_eval import DatasetManager
        >>> manager = DatasetManager()
        >>> manager.create_dataset("my-tests")
        >>> manager.add_example("my-tests", inputs={...}, outputs={...})
"""

# Configuration
from .config import (
    EvalConfig,
    LangSmithConfig,
    OnlineEvalConfig,
    OfflineEvalConfig,
    EvaluatorConfig,
    DEFAULT_CONFIG,
    get_dev_config,
    get_staging_config,
    get_prod_config,
)

# Evaluators (LangSmith-compatible functions for client.evaluate())
from .evaluators import (
    tool_correctness,
    routing_correctness,
    trajectory,
    safety,
    conversation_success,
    tool_was_called,
    tool_error_detail,
)

# Online evaluation (production monitoring)
from .online_evaluation import (
    OnlineEvaluationHelper,
    setup_production_tracing,
)

# Offline evaluation (pre-deployment testing)
from .offline_evaluation import (
    OfflineEvaluator,
    evaluate_routing_changes,
)

# Dataset management
from .datasets import (
    DatasetManager,
    create_test_dataset_for_routing,
    create_test_dataset_for_tools,
    create_tool_integration_dataset,
)

__version__ = "2.0.0"  # 2026 LangSmith-native version

__all__ = [
    # Configuration
    "EvalConfig",
    "LangSmithConfig",
    "OnlineEvalConfig",
    "OfflineEvalConfig",
    "EvaluatorConfig",
    "DEFAULT_CONFIG",
    "get_dev_config",
    "get_staging_config",
    "get_prod_config",
    # Evaluators
    "tool_correctness",
    "routing_correctness",
    "trajectory",
    "safety",
    "conversation_success",
    "tool_was_called",
    "tool_error_detail",
    # Online evaluation
    "OnlineEvaluationHelper",
    "setup_production_tracing",
    # Offline evaluation
    "OfflineEvaluator",
    "evaluate_routing_changes",
    # Datasets
    "DatasetManager",
    "create_test_dataset_for_routing",
    "create_test_dataset_for_tools",
    "create_tool_integration_dataset",
]
