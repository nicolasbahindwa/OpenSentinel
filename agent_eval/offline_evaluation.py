"""
Offline evaluation runner for LangSmith (2026).

Run evaluations against curated datasets before deployment.
This is your CI/CD integration for quality gates.

Uses the LangSmith API: client.evaluate()
"""

import logging
import sys
from typing import Any, Optional, Callable, List, Dict
from langsmith import Client
from .config import OfflineEvalConfig
from .evaluators import (
    tool_correctness,
    routing_correctness,
    trajectory,
    safety,
)

logger = logging.getLogger("opensentinel.eval.offline")


class OfflineEvaluator:
    """
    Runs offline evaluations against datasets.

    Offline evaluation is for pre-deployment testing:
    - Run during development
    - Run in CI/CD pipelines
    - Compare prompt/model versions
    - Catch regressions before production

    Uses client.evaluate() - the current LangSmith API
    """

    def __init__(
        self,
        config: Optional[OfflineEvalConfig] = None,
        client: Optional[Client] = None,
    ):
        """
        Initialize offline evaluator.

        Args:
            config: Optional evaluation configuration
            client: Optional LangSmith client
        """
        self.config = config or OfflineEvalConfig()
        self.client = client or Client()

    def evaluate_agent(
        self,
        agent_or_factory: Callable,
        dataset_name: str,
        experiment_name: Optional[str] = None,
        evaluators: Optional[list] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate agent against a dataset.

        This is the main entry point for offline evaluation.
        Uses client.run_on_dataset() - the correct 2026 API.

        Args:
            agent_or_factory: Your agent (CompiledStateGraph) or factory function
            dataset_name: Name of the dataset to evaluate against
            experiment_name: Optional name for this evaluation run
            evaluators: Optional list of evaluators (uses defaults if None)
            metadata: Optional metadata for the experiment

        Returns:
            Dictionary with evaluation results

        Example:
            >>> from agent import create_agent
            >>> from agent_eval import OfflineEvaluator
            >>>
            >>> evaluator = OfflineEvaluator()
            >>> results = evaluator.evaluate_agent(
            ...     agent_or_factory=create_agent(),  # Your LangGraph agent
            ...     dataset_name="regression-tests",
            ...     experiment_name="fix-routing-v2",
            ... )
            >>> print(f"Results: {results}")
        """
        # Use default evaluators if none provided
        if evaluators is None:
            evaluators = [
                tool_correctness,
                routing_correctness,
                trajectory,
                safety,
            ]

        # Also support openevals library evaluators
        try:
            from langchain import hub
            # Add pre-built evaluators from openevals
            # evaluators.append(hub.pull("langchain-ai/cot-qa"))
        except:
            pass

        # Generate experiment name if not provided
        if experiment_name is None:
            from datetime import datetime
            experiment_name = f"{self.config.experiment_prefix}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        logger.info(
            f"Starting evaluation: {experiment_name} "
            f"on dataset: {dataset_name}"
        )

        try:
            # Wrap agent to match LangSmith's expected target signature:
            # target(inputs: dict) -> dict
            # Dataset examples store inputs as {"query": "..."} but the
            # agent expects {"messages": [{"role": "user", "content": "..."}]}.
            def _target(inputs: dict) -> dict:
                if "messages" not in inputs:
                    query = inputs.get("query") or inputs.get("input") or str(inputs)
                    inputs = {"messages": [{"role": "user", "content": query}]}

                result = agent_or_factory.invoke(inputs)
                if not isinstance(result, dict):
                    return {"output": str(result)}

                # Post-process LangGraph state into evaluator-friendly output.
                # Extract tool calls and final answer from the messages list.
                messages = result.get("messages", [])
                tool_calls = []
                final_output = ""
                for msg in messages:
                    # Extract tool calls from AIMessages
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        for tc in msg.tool_calls:
                            tool_calls.append(tc.get("name") or tc.get("function", {}).get("name", "unknown"))
                    # Track last assistant text as final output
                    content = getattr(msg, "content", "") or ""
                    role = getattr(msg, "type", "") or ""
                    if role in ("ai", "assistant") and content:
                        final_output = content

                result["tool_calls"] = tool_calls
                result["output"] = final_output
                return result

            # Run evaluation using LangSmith's evaluate() API
            experiment_results = self.client.evaluate(
                _target,
                data=dataset_name,
                evaluators=evaluators,
                experiment_prefix=experiment_name,
                metadata=metadata or {},
                max_concurrency=self.config.max_concurrency,
                num_repetitions=self.config.num_repetitions,
                blocking=True,
            )

            logger.info(f"Evaluation complete: {experiment_name}")

            # Collect scores from results.
            # ExperimentResults is iterable; each item is a dict with
            # "run", "example", and "evaluation_results" keys.
            scores: Dict[str, list] = {}
            try:
                for result in experiment_results:
                    eval_results = result.get("evaluation_results", {})
                    er_list = eval_results.get("results", []) if isinstance(eval_results, dict) else getattr(eval_results, "results", [])
                    for er in er_list:
                        key = getattr(er, "key", None) or er.get("key") if isinstance(er, dict) else getattr(er, "key", None)
                        score = getattr(er, "score", None) if not isinstance(er, dict) else er.get("score")
                        if key and score is not None:
                            scores.setdefault(key, []).append(score)
            except Exception as e:
                logger.warning(f"Could not iterate results: {e}")

            aggregate_metrics = {
                k: sum(v) / len(v) for k, v in scores.items() if v
            }
            logger.info(f"Aggregate Results: {aggregate_metrics}")

            return {
                "experiment_name": experiment_name,
                "dataset_name": dataset_name,
                "results": experiment_results,
                "aggregate_metrics": aggregate_metrics,
            }

        except Exception as e:
            logger.error(f"Evaluation failed: {e}")
            raise

    def compare_experiments(
        self,
        experiment1_name: str,
        experiment2_name: str,
    ) -> dict[str, Any]:
        """
        Compare results from two experiments.

        Useful for A/B testing prompts, models, or configurations.

        NOTE: LangSmith 2026 has built-in comparison UI at:
        Project → Experiments → Select 2 experiments → Compare

        This provides programmatic access to comparison.

        Args:
            experiment1_name: First experiment name
            experiment2_name: Second experiment name

        Returns:
            Comparison statistics
        """
        logger.info(f"Comparing experiments: {experiment1_name} vs {experiment2_name}")
        logger.info("💡 TIP: Use LangSmith UI for visual comparison:")
        logger.info(f"   Go to Project → Experiments → Compare '{experiment1_name}' vs '{experiment2_name}'")

        try:
            # Get runs from both experiments
            exp1_runs = list(self.client.list_runs(
                project_name=experiment1_name,
                limit=1000,
            ))

            exp2_runs = list(self.client.list_runs(
                project_name=experiment2_name,
                limit=1000,
            ))

            # Calculate aggregate scores for each
            exp1_scores = self._aggregate_feedback_scores(exp1_runs)
            exp2_scores = self._aggregate_feedback_scores(exp2_runs)

            comparison = {
                "experiment1": experiment1_name,
                "experiment2": experiment2_name,
                "experiment1_scores": exp1_scores,
                "experiment2_scores": exp2_scores,
                "improvements": {},
                "winner": None,
            }

            # Calculate improvements
            total_improvement = 0
            for key in exp1_scores:
                if key in exp2_scores:
                    diff = exp2_scores[key] - exp1_scores[key]
                    comparison["improvements"][key] = {
                        "baseline": exp1_scores[key],
                        "new": exp2_scores[key],
                        "diff": diff,
                        "improved": diff > 0,
                    }
                    total_improvement += diff

            # Determine winner
            comparison["winner"] = experiment2_name if total_improvement > 0 else experiment1_name

            logger.info(f"Comparison complete. Winner: {comparison['winner']}")
            return comparison

        except Exception as e:
            logger.error(f"Comparison failed: {e}")
            return {}

    def _aggregate_feedback_scores(self, runs: List) -> Dict[str, float]:
        """Aggregate feedback scores from runs."""
        scores = {}
        for run in runs:
            if hasattr(run, "feedback_stats") and run.feedback_stats:
                for stat in run.feedback_stats:
                    key = stat.get("key")
                    if key and "avg" in stat:
                        if key not in scores:
                            scores[key] = []
                        scores[key].append(stat["avg"])

        # Calculate averages
        return {
            key: sum(values) / len(values) if values else 0.0
            for key, values in scores.items()
        }

    def check_quality_gates(
        self,
        results: Dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """
        Check if evaluation meets quality gates.

        Use this in CI/CD to block deployments if scores are too low.

        Args:
            results: Evaluation results dict from evaluate_agent()

        Returns:
            Tuple of (passed, list of failures)

        Example:
            >>> results = evaluator.evaluate_agent(...)
            >>> passed, failures = evaluator.check_quality_gates(results)
            >>> if not passed:
            ...     print(f"Quality gates failed: {failures}")
            ...     sys.exit(1)  # Block deployment
        """
        failures = []
        metrics = results.get("aggregate_metrics", {})

        # Check each metric against thresholds
        if metrics.get("tool_correctness", 0) < self.config.min_tool_correctness:
            failures.append(
                f"Tool correctness {metrics.get('tool_correctness', 0):.2f} "
                f"< {self.config.min_tool_correctness}"
            )

        if metrics.get("routing_correctness", 0) < self.config.min_routing_correctness:
            failures.append(
                f"Routing correctness {metrics.get('routing_correctness', 0):.2f} "
                f"< {self.config.min_routing_correctness}"
            )

        if metrics.get("trajectory", 0) < self.config.min_trajectory_score:
            failures.append(
                f"Trajectory score {metrics.get('trajectory', 0):.2f} "
                f"< {self.config.min_trajectory_score}"
            )

        if metrics.get("safety", 0) < self.config.min_safety_score:
            failures.append(
                f"Safety score {metrics.get('safety', 0):.2f} "
                f"< {self.config.min_safety_score}"
            )

        passed = len(failures) == 0

        if passed:
            logger.info("✓ All quality gates passed")
        else:
            logger.warning(f"✗ Quality gates failed: {len(failures)} issues")
            for failure in failures:
                logger.warning(f"  - {failure}")

        return passed, failures

    def run_regression_tests(
        self,
        agent_or_factory: Callable,
        dataset_name: str = "regression-tests",
    ) -> bool:
        """
        Run regression tests and check quality gates.

        Convenience method for CI/CD integration.

        Args:
            agent_or_factory: Your agent or factory function
            dataset_name: Regression test dataset

        Returns:
            True if tests pass, False otherwise

        Example:
            >>> # In your CI pipeline (GitHub Actions, etc.)
            >>> from agent import create_agent
            >>> from agent_eval import OfflineEvaluator
            >>>
            >>> evaluator = OfflineEvaluator()
            >>> passed = evaluator.run_regression_tests(create_agent())
            >>> sys.exit(0 if passed else 1)
        """
        logger.info(f"Running regression tests against {dataset_name}")

        try:
            results = self.evaluate_agent(
                agent_or_factory=agent_or_factory,
                dataset_name=dataset_name,
                experiment_name="regression-test",
            )

            passed, failures = self.check_quality_gates(results)

            return passed

        except Exception as e:
            logger.error(f"Regression tests failed with error: {e}")
            return False


def evaluate_routing_changes(
    agent_or_factory: Callable,
    baseline_experiment: str,
    new_experiment_name: str = "routing-v2",
    dataset_name: str = "routing-test-suite",
) -> dict[str, Any]:
    """
    Evaluate routing changes with automatic comparison to baseline.

    Use this when modifying routing logic to ensure you don't regress.

    Args:
        agent_or_factory: Your agent or factory function
        baseline_experiment: Name of baseline experiment to compare against
        new_experiment_name: Name for the new experiment
        dataset_name: Dataset to evaluate on

    Returns:
        Comparison results

    Example:
        >>> from agent import create_agent
        >>> from agent_eval import evaluate_routing_changes
        >>>
        >>> comparison = evaluate_routing_changes(
        ...     agent_or_factory=create_agent(),
        ...     baseline_experiment="routing-v1",
        ...     new_experiment_name="routing-v2",
        ... )
        >>> if comparison["winner"] == "routing-v2":
        ...     print("New routing is better!")
    """
    evaluator = OfflineEvaluator()

    # Run evaluation with routing-focused evaluators
    results = evaluator.evaluate_agent(
        agent_or_factory=agent_or_factory,
        dataset_name=dataset_name,
        experiment_name=new_experiment_name,
        evaluators=[routing_correctness, trajectory],
    )

    # Compare to baseline
    comparison = evaluator.compare_experiments(
        experiment1_name=baseline_experiment,
        experiment2_name=new_experiment_name,
    )

    return comparison


__all__ = [
    "OfflineEvaluator",
    "evaluate_routing_changes",
]
