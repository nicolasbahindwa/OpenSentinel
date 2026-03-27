"""
Dataset management for LangSmith evaluation (2026).

Utilities for creating, managing, and using datasets for offline evaluation.
"""

import logging
from typing import Any, Optional, Union
from datetime import datetime
from langsmith import Client
from langsmith.schemas import Example

logger = logging.getLogger("opensentinel.eval.datasets")


class DatasetManager:
    """
    Manages LangSmith datasets for evaluation.

    Datasets are collections of test examples (input/output pairs) used
    for offline evaluation and regression testing.
    """

    def __init__(self, client: Optional[Client] = None):
        """
        Initialize dataset manager.

        Args:
            client: Optional LangSmith client (creates default if not provided)
        """
        self.client = client or Client()

    def create_dataset(
        self,
        name: str,
        description: Optional[str] = None,
    ) -> str:
        """
        Create a new dataset.

        Args:
            name: Dataset name
            description: Optional description

        Returns:
            Dataset ID
        """
        try:
            dataset = self.client.create_dataset(
                dataset_name=name,
                description=description or f"Dataset created {datetime.now().isoformat()}",
            )
            logger.info(f"Created dataset: {name} (ID: {dataset.id})")
            return str(dataset.id)
        except Exception as e:
            logger.error(f"Failed to create dataset {name}: {e}")
            raise

    def add_example(
        self,
        dataset_name: str,
        inputs: dict[str, Any],
        outputs: Optional[dict[str, Any]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> str:
        """
        Add an example to a dataset.

        Args:
            dataset_name: Name of the dataset
            inputs: Input data for the example
            outputs: Expected output (optional, for reference comparison)
            metadata: Additional metadata

        Returns:
            Example ID
        """
        try:
            # Get dataset
            dataset = self.client.read_dataset(dataset_name=dataset_name)

            # Create example
            example = self.client.create_example(
                dataset_id=dataset.id,
                inputs=inputs,
                outputs=outputs,
                metadata=metadata or {},
            )

            logger.info(f"Added example to dataset {dataset_name}: {example.id}")
            return str(example.id)

        except Exception as e:
            logger.error(f"Failed to add example to {dataset_name}: {e}")
            raise

    def add_examples_bulk(
        self,
        dataset_name: str,
        examples: list[dict[str, Any]],
    ) -> int:
        """
        Add multiple examples to a dataset efficiently.

        Args:
            dataset_name: Name of the dataset
            examples: List of examples, each with 'inputs', optional 'outputs' and 'metadata'

        Returns:
            Number of examples added
        """
        count = 0
        for example in examples:
            try:
                self.add_example(
                    dataset_name=dataset_name,
                    inputs=example.get("inputs", {}),
                    outputs=example.get("outputs"),
                    metadata=example.get("metadata"),
                )
                count += 1
            except Exception as e:
                logger.warning(f"Failed to add example: {e}")
                continue

        logger.info(f"Added {count}/{len(examples)} examples to {dataset_name}")
        return count

    def export_runs_to_dataset(
        self,
        dataset_name: str,
        project_name: str,
        filter_func: Optional[callable] = None,
        limit: int = 100,
    ) -> int:
        """
        Export production runs to a dataset.

        This is the key feedback loop: real production traces become test cases.

        Args:
            dataset_name: Dataset to add examples to
            project_name: Source project to export from
            filter_func: Optional function to filter runs (receives Run object)
            limit: Maximum number of runs to export

        Returns:
            Number of examples created
        """
        try:
            # Get or create dataset
            try:
                dataset = self.client.read_dataset(dataset_name=dataset_name)
            except:
                logger.info(f"Dataset {dataset_name} not found, creating...")
                dataset = self.client.create_dataset(
                    dataset_name=dataset_name,
                    description=f"Exported from {project_name} on {datetime.now().isoformat()}",
                )

            # Get runs from project
            runs = list(self.client.list_runs(
                project_name=project_name,
                limit=limit,
            ))

            # Filter if function provided
            if filter_func:
                runs = [r for r in runs if filter_func(r)]

            # Create examples from runs
            count = 0
            for run in runs:
                try:
                    self.client.create_example(
                        dataset_id=dataset.id,
                        inputs=run.inputs or {},
                        outputs=run.outputs or {},
                        metadata={
                            "run_id": str(run.id),
                            "exported_from": project_name,
                            "exported_at": datetime.now().isoformat(),
                            "run_name": run.name,
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to create example from run {run.id}: {e}")
                    continue

            logger.info(f"Exported {count} runs to dataset {dataset_name}")
            return count

        except Exception as e:
            logger.error(f"Failed to export runs: {e}")
            return 0

    def create_regression_dataset_from_failures(
        self,
        source_project: str,
        dataset_name: str = "regression-tests",
        score_threshold: float = 0.5,
        limit: int = 50,
    ) -> int:
        """
        Create a regression test dataset from production failures.

        Automatically finds low-scoring traces and adds them as test cases.

        Args:
            source_project: Project to analyze
            dataset_name: Name for the regression dataset
            score_threshold: Traces scoring below this are added
            limit: Maximum traces to add

        Returns:
            Number of examples added
        """
        def is_failure(run) -> bool:
            """Check if run is a failure (low score)."""
            # Check feedback scores
            if hasattr(run, "feedback_stats") and run.feedback_stats:
                for stat in run.feedback_stats:
                    if stat.get("avg") and stat["avg"] < score_threshold:
                        return True

            # Check error status
            if run.error:
                return True

            return False

        return self.export_runs_to_dataset(
            dataset_name=dataset_name,
            project_name=source_project,
            filter_func=is_failure,
            limit=limit,
        )

    def list_datasets(self) -> list[dict[str, Any]]:
        """
        List all available datasets.

        Returns:
            List of dataset info dicts
        """
        try:
            datasets = list(self.client.list_datasets())
            return [
                {
                    "id": str(ds.id),
                    "name": ds.name,
                    "description": ds.description,
                    "example_count": ds.example_count,
                    "created_at": ds.created_at,
                }
                for ds in datasets
            ]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            return []

    def get_dataset_stats(self, dataset_name: str) -> dict[str, Any]:
        """
        Get statistics about a dataset.

        Args:
            dataset_name: Name of the dataset

        Returns:
            Dictionary with dataset statistics
        """
        try:
            dataset = self.client.read_dataset(dataset_name=dataset_name)
            examples = list(self.client.list_examples(dataset_id=dataset.id))

            return {
                "name": dataset.name,
                "description": dataset.description,
                "example_count": len(examples),
                "created_at": dataset.created_at,
                "modified_at": dataset.modified_at,
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {dataset_name}: {e}")
            return {}


def create_test_dataset_for_routing(
    dataset_name: str = "routing-test-suite",
    client: Optional[Client] = None,
) -> int:
    """
    Create a test dataset specifically for routing evaluation.

    Pre-populates with common routing scenarios for OpenSentinel.

    Args:
        dataset_name: Name for the dataset
        client: Optional LangSmith client

    Returns:
        Number of examples created
    """
    manager = DatasetManager(client)

    # Create dataset
    try:
        manager.create_dataset(
            name=dataset_name,
            description="Test suite for routing middleware evaluation"
        )
    except:
        logger.info(f"Dataset {dataset_name} already exists")

    # Routing test cases
    examples = [
        {
            "inputs": {"query": "What's the weather in San Francisco?"},
            "outputs": {"expected_route": "weather_agent"},
            "metadata": {"category": "weather", "difficulty": "easy"},
        },
        {
            "inputs": {"query": "Send an email to john@example.com about the meeting"},
            "outputs": {"expected_route": "communication_agent"},
            "metadata": {"category": "email", "difficulty": "medium"},
        },
        {
            "inputs": {"query": "Search the web for latest AI news"},
            "outputs": {"expected_route": "search_agent"},
            "metadata": {"category": "search", "difficulty": "easy"},
        },
        {
            "inputs": {"query": "Calculate 15% tip on $85.50"},
            "outputs": {"expected_route": "calculation_agent"},
            "metadata": {"category": "math", "difficulty": "easy"},
        },
        {
            "inputs": {"query": "What's the stock price of NVDA and send me a summary via email?"},
            "outputs": {
                "expected_route": "multi_step",
                "expected_tools": ["stock_lookup", "gmail_send"]
            },
            "metadata": {"category": "multi_step", "difficulty": "hard"},
        },
    ]

    return manager.add_examples_bulk(dataset_name, examples)


def create_test_dataset_for_tools(
    dataset_name: str = "tool-test-suite",
    client: Optional[Client] = None,
) -> int:
    """
    Create a test dataset for tool evaluation.

    Args:
        dataset_name: Name for the dataset
        client: Optional LangSmith client

    Returns:
        Number of examples created
    """
    manager = DatasetManager(client)

    # Create dataset
    try:
        manager.create_dataset(
            name=dataset_name,
            description="Test suite for tool correctness evaluation"
        )
    except:
        logger.info(f"Dataset {dataset_name} already exists")

    # Tool test cases
    examples = [
        {
            "inputs": {
                "tool": "tavily_search",
                "args": {"query": "LangChain latest release"}
            },
            "outputs": {"expected_type": "dict"},
            "metadata": {"tool_category": "search", "risk_level": "low"},
        },
        {
            "inputs": {
                "tool": "calculator",
                "args": {"expression": "2 + 2"}
            },
            "outputs": {"expected_result": 4, "expected_type": "number"},
            "metadata": {"tool_category": "calculation", "risk_level": "low"},
        },
    ]

    return manager.add_examples_bulk(dataset_name, examples)


def create_tool_integration_dataset(
    dataset_name: str = "tool-integration-tests",
    client: Optional[Client] = None,
) -> int:
    """
    Create an integration test dataset with one example per agent tool.

    Each example has a query designed to trigger a specific tool,
    the expected tool name, and the expected output type.

    Args:
        dataset_name: Name for the dataset
        client: Optional LangSmith client

    Returns:
        Number of examples created
    """
    manager = DatasetManager(client)

    try:
        manager.create_dataset(
            name=dataset_name,
            description="Integration tests: one example per tool, verifies each tool is callable and returns valid output",
        )
    except Exception:
        logger.info(f"Dataset {dataset_name} already exists")

    examples = [
        # --- internet_search (Tavily API) ---
        {
            "inputs": {"query": "Search for the latest SpaceX launch news"},
            "outputs": {
                "expected_tool": "internet_search",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "internet_search",
                "dependency": "tavily_api_key",
                "risk_level": "low",
            },
        },
        # --- weather_lookup (Open-Meteo, free) ---
        {
            "inputs": {"query": "What is the current weather in Tokyo, Japan?"},
            "outputs": {
                "expected_tool": "weather_lookup",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "weather_lookup",
                "dependency": "open_meteo_api",
                "risk_level": "low",
            },
        },
        # --- file_browser (local filesystem) ---
        {
            "inputs": {"query": "List the files on my Desktop"},
            "outputs": {
                "expected_tool": "file_browser",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "file_browser",
                "dependency": "local_filesystem",
                "risk_level": "medium",
            },
        },
        # --- tool_search (internal registry) ---
        {
            "inputs": {"query": "What tools do you have available? Search your tools."},
            "outputs": {
                "expected_tool": "tool_search",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "tool_search",
                "dependency": "none",
                "risk_level": "low",
            },
        },
        # --- system_status (psutil) ---
        {
            "inputs": {"query": "Show me the current CPU and memory usage of my system"},
            "outputs": {
                "expected_tool": "system_status",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "system_status",
                "dependency": "psutil",
                "risk_level": "low",
            },
        },
        # --- web_browser (Playwright) ---
        {
            "inputs": {"query": "Browse https://example.com and tell me what's on the page"},
            "outputs": {
                "expected_tool": "web_browser",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "web_browser",
                "dependency": "playwright",
                "risk_level": "low",
            },
        },
        # --- crypto (CoinGecko, free) ---
        {
            "inputs": {"query": "What is the current price of Bitcoin in USD?"},
            "outputs": {
                "expected_tool": "crypto",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "crypto",
                "dependency": "coingecko_api",
                "risk_level": "low",
            },
        },
        # --- currency (Frankfurter, free) ---
        {
            "inputs": {"query": "Convert 100 US dollars to euros"},
            "outputs": {
                "expected_tool": "currency",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "currency",
                "dependency": "frankfurter_api",
                "risk_level": "low",
            },
        },
        # --- yahoo_finance (yfinance) ---
        {
            "inputs": {"query": "Get me the current stock price of Apple (AAPL)"},
            "outputs": {
                "expected_tool": "yahoo_finance",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "yahoo_finance",
                "dependency": "yfinance",
                "risk_level": "low",
            },
        },
        # --- gmail (Google OAuth) ---
        {
            "inputs": {"query": "Show me my latest emails from Gmail inbox"},
            "outputs": {
                "expected_tool": "gmail",
                "expected_output_type": "dict",
            },
            "metadata": {
                "tool": "gmail",
                "dependency": "google_oauth",
                "risk_level": "medium",
            },
        },
    ]

    return manager.add_examples_bulk(dataset_name, examples)


__all__ = [
    "DatasetManager",
    "create_test_dataset_for_routing",
    "create_test_dataset_for_tools",
    "create_tool_integration_dataset",
]
