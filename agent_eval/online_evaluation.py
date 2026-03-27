"""
LangSmith online evaluation setup for production monitoring (2026).

IMPORTANT: Online evaluators are configured via LangSmith UI, not SDK.
This module provides utilities for tagging traces and monitoring results.

Online evaluation monitors real production traffic and automatically scores
agent performance without blocking user requests.
"""

import logging
from typing import Any, Optional, Dict, List
from langsmith import Client

logger = logging.getLogger("opensentinel.eval.online")


class OnlineEvaluationHelper:
    """
    Helper for production monitoring with LangSmith online evaluators.

    NOTE: Online evaluators are configured in the LangSmith UI:
    1. Go to your project → Evaluators tab → + New
    2. Select evaluator type (llm-as-judge or code)
    3. Configure filters (tags, metadata)
    4. Set sampling rate
    5. Alerts auto-configured via Rules tab

    This class helps you:
    - Tag traces for filtering
    - Add metadata for evaluator targeting
    - Query evaluation results
    - Export failing traces to datasets
    """

    def __init__(
        self,
        project_name: str = "opensentinel-prod",
        client: Optional[Client] = None,
    ):
        """
        Initialize online evaluation helper.

        Args:
            project_name: LangSmith project to monitor
            client: Optional LangSmith client (uses env var if not provided)
        """
        self.client = client or Client()
        self.project_name = project_name

    def get_trace_tags_for_tool_eval(self, tool_name: str) -> List[str]:
        """
        Get recommended tags for tool evaluation.

        Use these tags when invoking your agent to enable filtering
        in online evaluators.

        Args:
            tool_name: Name of the tool being called

        Returns:
            List of tags to attach to the trace

        Example:
            >>> helper = OnlineEvaluationHelper()
            >>> tags = helper.get_trace_tags_for_tool_eval("tavily_search")
            >>> # Then pass to agent:
            >>> agent.invoke(
            ...     {"messages": [...]},
            ...     config={"tags": tags}
            ... )
        """
        tags = ["production", f"tool:{tool_name}"]

        # Add risk tags for high-risk tools
        HIGH_RISK_TOOLS = {
            "execute_code",
            "delete_file",
            "send_email",
            "financial_transaction",
            "gmail_send",
            "bash_tool",
        }

        if tool_name in HIGH_RISK_TOOLS:
            tags.append("high-risk")

        return tags

    def get_trace_metadata_for_routing(
        self,
        route_decision: str,
        intent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get recommended metadata for routing evaluation.

        Attach this metadata to traces for routing evaluators to filter on.

        Args:
            route_decision: Which route was taken
            intent: Optional user intent classification

        Returns:
            Metadata dict to attach to trace

        Example:
            >>> metadata = helper.get_trace_metadata_for_routing(
            ...     route_decision="weather_agent",
            ...     intent="weather_query"
            ... )
            >>> agent.invoke(
            ...     {"messages": [...]},
            ...     config={"metadata": metadata, "tags": ["routing"]}
            ... )
        """
        metadata = {
            "route_decision": route_decision,
            "evaluation_category": "routing",
        }

        if intent:
            metadata["user_intent"] = intent

        return metadata

    def get_configuration_guide(self) -> dict[str, Any]:
        """
        Get step-by-step guide for configuring online evaluators in LangSmith UI.

        Returns:
            Dictionary with setup instructions for each evaluator type
        """
        return {
            "tool_correctness": {
                "type": "code",
                "description": "Fast technical validation of tool calls",
                "setup_steps": [
                    "1. Go to LangSmith UI → Your Project → Evaluators tab",
                    "2. Click '+ New Evaluator'",
                    "3. Select 'Code Evaluator'",
                    "4. Filter: tag:tool:* (matches all tool calls)",
                    "5. Sampling: 100% (evaluate all tools)",
                    "6. Code: Check for errors in output",
                    "7. Save evaluator",
                ],
                "filter_example": "tag:tool:tavily_search",
                "sampling_rate": 1.0,
            },
            "routing_correctness": {
                "type": "llm-as-judge",
                "description": "Validate routing decisions to subagents",
                "setup_steps": [
                    "1. Go to LangSmith UI → Your Project → Evaluators tab",
                    "2. Click '+ New Evaluator'",
                    "3. Select 'LLM-as-Judge'",
                    "4. Filter: tag:routing",
                    "5. Sampling: 10%",
                    "6. Prompt: 'Was the routing decision correct based on user intent?'",
                    "7. Save evaluator",
                ],
                "filter_example": "tag:routing && metadata.user_intent",
                "sampling_rate": 0.1,
            },
            "trajectory_quality": {
                "type": "llm-as-judge",
                "description": "Evaluate full agent decision path",
                "setup_steps": [
                    "1. Go to LangSmith UI → Your Project → Evaluators tab",
                    "2. Click '+ New Evaluator'",
                    "3. Select 'LLM-as-Judge'",
                    "4. Filter: tag:production",
                    "5. Sampling: 5%",
                    "6. Prompt: 'Evaluate the agent's tool call sequence. Was it logical and efficient?'",
                    "7. Enable 'Evaluate child runs' to see full trajectory",
                    "8. Save evaluator",
                ],
                "filter_example": "tag:production",
                "sampling_rate": 0.05,
            },
            "safety_compliance": {
                "type": "code",
                "description": "Monitor guardrails and high-risk operations",
                "setup_steps": [
                    "1. Go to LangSmith UI → Your Project → Evaluators tab",
                    "2. Click '+ New Evaluator'",
                    "3. Select 'Code Evaluator'",
                    "4. Filter: tag:high-risk",
                    "5. Sampling: 100% (evaluate all high-risk)",
                    "6. Code: Check for guardrail triggers",
                    "7. Set up alert: Rules tab → New Rule → Score < 0.9 → Webhook",
                    "8. Save evaluator",
                ],
                "filter_example": "tag:high-risk",
                "sampling_rate": 1.0,
            },
            "multi_turn_conversations": {
                "type": "llm-as-judge",
                "description": "Evaluate complete conversation threads (NEW 2026!)",
                "setup_steps": [
                    "1. Go to LangSmith UI → Your Project → Evaluators tab",
                    "2. Click '+ New Evaluator'",
                    "3. Select 'LLM-as-Judge'",
                    "4. Target: 'Threads' (not single runs!)",
                    "5. Filter: tag:conversation",
                    "6. Sampling: 5%",
                    "7. Prompt: 'Did the agent accomplish the user's goal across the full conversation?'",
                    "8. Criteria: resolved_user_issue, helpful, appropriate",
                    "9. Save evaluator",
                ],
                "filter_example": "tag:conversation && thread_id",
                "sampling_rate": 0.05,
                "note": "Multi-turn evaluators work on threads, not individual runs!",
            },
        }

    def get_evaluation_stats(self, days: int = 7) -> dict[str, Any]:
        """
        Get evaluation statistics from LangSmith.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with evaluation metrics
        """
        try:
            # Query runs with feedback (evaluation scores)
            runs = list(self.client.list_runs(
                project_name=self.project_name,
                is_root=True,
                limit=1000,
            ))

            # Aggregate feedback scores
            total_runs = len(runs)
            runs_with_feedback = 0
            feedback_scores = {}

            for run in runs:
                if hasattr(run, "feedback_stats") and run.feedback_stats:
                    runs_with_feedback += 1
                    for stat in run.feedback_stats:
                        key = stat.get("key", "unknown")
                        if key not in feedback_scores:
                            feedback_scores[key] = []
                        if "avg" in stat:
                            feedback_scores[key].append(stat["avg"])

            # Calculate averages
            stats = {
                "total_runs": total_runs,
                "runs_with_feedback": runs_with_feedback,
                "coverage": runs_with_feedback / total_runs if total_runs > 0 else 0,
                "avg_scores": {},
            }

            for key, scores in feedback_scores.items():
                stats["avg_scores"][key] = sum(scores) / len(scores) if scores else 0

            return stats

        except Exception as e:
            logger.error(f"Failed to get evaluation stats: {e}")
            return {}

    def export_failing_traces_to_dataset(
        self,
        dataset_name: str,
        score_threshold: float = 0.5,
        feedback_key: Optional[str] = None,
        limit: int = 100,
    ) -> int:
        """
        Export failing traces to a dataset for offline evaluation.

        This is the feedback loop: production failures become test cases.

        Args:
            dataset_name: Name for the new dataset
            score_threshold: Traces scoring below this become examples
            feedback_key: Optional specific feedback key to filter on
            limit: Maximum number of traces to export

        Returns:
            Number of examples added to dataset
        """
        try:
            logger.info(
                f"Exporting failing traces (score < {score_threshold}) "
                f"to dataset: {dataset_name}"
            )

            # Get or create dataset
            try:
                dataset = self.client.read_dataset(dataset_name=dataset_name)
            except:
                dataset = self.client.create_dataset(
                    dataset_name=dataset_name,
                    description=f"Failing traces from {self.project_name}",
                )

            # Query for runs with low scores
            runs = list(self.client.list_runs(
                project_name=self.project_name,
                is_root=True,
                limit=limit,
            ))

            # Filter for failing runs
            failing_runs = []
            for run in runs:
                if hasattr(run, "feedback_stats") and run.feedback_stats:
                    for stat in run.feedback_stats:
                        if feedback_key and stat.get("key") != feedback_key:
                            continue
                        if stat.get("avg", 1.0) < score_threshold:
                            failing_runs.append(run)
                            break

            # Add to dataset
            count = 0
            for run in failing_runs:
                try:
                    self.client.create_example(
                        dataset_id=dataset.id,
                        inputs=run.inputs or {},
                        outputs=run.outputs or {},
                        metadata={
                            "run_id": str(run.id),
                            "failure_type": "low_score",
                            "original_score": 0.0,  # TODO: Extract actual score
                            "tags": run.tags if hasattr(run, "tags") else [],
                        }
                    )
                    count += 1
                except Exception as e:
                    logger.warning(f"Failed to add run {run.id}: {e}")
                    continue

            logger.info(f"Added {count} failing traces to dataset {dataset_name}")
            return count

        except Exception as e:
            logger.error(f"Failed to export failing traces: {e}")
            return 0

    def print_setup_instructions(self) -> None:
        """
        Print detailed setup instructions for online evaluators.

        Call this to get step-by-step guide for LangSmith UI configuration.
        """
        guide = self.get_configuration_guide()

        print("\n" + "="*70)
        print("LANGSMITH ONLINE EVALUATORS SETUP GUIDE")
        print("="*70 + "\n")

        print("Online evaluators are configured in the LangSmith UI (not SDK).")
        print("Follow these steps for each evaluator type:\n")

        for name, config in guide.items():
            print(f"\n📊 {name.upper().replace('_', ' ')}")
            print(f"   Type: {config['type']}")
            print(f"   {config['description']}\n")

            print("   Setup Steps:")
            for step in config["setup_steps"]:
                print(f"   {step}")

            print(f"\n   Filter Example: {config['filter_example']}")
            print(f"   Sampling Rate: {config['sampling_rate']*100}%")

            if "note" in config:
                print(f"   ⚠️  NOTE: {config['note']}")

        print("\n" + "="*70)
        print("ALERTING SETUP")
        print("="*70 + "\n")
        print("1. Go to Project → Rules tab")
        print("2. Click '+ New Rule'")
        print("3. Condition: Feedback score < threshold")
        print("4. Action: Webhook or Slack notification")
        print("5. Save rule\n")

        print("Your traces will be automatically evaluated and monitored!")
        print("View results in: Project → Traces → Filter by feedback scores\n")


def setup_production_tracing(
    project_name: str = "opensentinel-prod",
) -> OnlineEvaluationHelper:
    """
    Quick setup guide for production monitoring.

    This returns a helper with instructions for UI configuration.

    Example:
        >>> from agent_eval.online_evaluation import setup_production_tracing
        >>> helper = setup_production_tracing("opensentinel-prod")
        >>> helper.print_setup_instructions()  # Shows UI setup guide
        >>>
        >>> # Then in your agent code:
        >>> tags = helper.get_trace_tags_for_tool_eval("tavily_search")
        >>> agent.invoke({"messages": [...]}, config={"tags": tags})

    Args:
        project_name: LangSmith project name

    Returns:
        Configured OnlineEvaluationHelper instance
    """
    helper = OnlineEvaluationHelper(project_name=project_name)
    return helper


__all__ = [
    "OnlineEvaluationHelper",
    "setup_production_tracing",
]
