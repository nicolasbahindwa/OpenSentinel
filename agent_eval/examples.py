"""
Example usage of agent_eval module (2026 LangSmith).

Run these examples to learn how to use the evaluation framework.
"""

import sys
import os

# Ensure agent package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


def example_1_enable_tracing():
    """
    Example 1: Enable automatic tracing for your agent.

    This is step #1 - without this, nothing else works!
    """
    print("\n" + "="*70)
    print("EXAMPLE 1: Enable Automatic Tracing")
    print("="*70 + "\n")

    print("1. Add to your .env file:")
    print("   LANGSMITH_TRACING=true")
    print("   LANGSMITH_API_KEY=your_key_here")
    print("   LANGSMITH_PROJECT=opensentinel-dev\n")

    print("2. Run your agent normally:")
    print("   >>> from agent import create_agent")
    print("   >>> agent = create_agent()")
    print("   >>> agent.invoke({'messages': [...]})\n")

    print("3. View traces at: https://smith.langchain.com\n")

    print("That's it! LangGraph agents are automatically traced.")


def example_2_setup_online_evaluation():
    """
    Example 2: Setup production monitoring with online evaluators.
    """
    print("\n" + "="*70)
    print("EXAMPLE 2: Setup Online Evaluation (Production)")
    print("="*70 + "\n")

    from agent_eval import setup_production_tracing

    # Get helper with instructions
    helper = setup_production_tracing("opensentinel-prod")

    print("Online evaluators are configured in the LangSmith UI.\n")
    print("Step-by-step instructions:\n")

    helper.print_setup_instructions()

    print("\n💡 TIP: Tag your traces to enable filtering:")
    print("   >>> tags = helper.get_trace_tags_for_tool_eval('tavily_search')")
    print("   >>> agent.invoke({...}, config={'tags': tags})")


def example_3_create_test_dataset():
    """
    Example 3: Create a test dataset for offline evaluation.
    """
    print("\n" + "="*70)
    print("EXAMPLE 3: Create Test Dataset")
    print("="*70 + "\n")

    from agent_eval import DatasetManager

    manager = DatasetManager()

    # Create dataset
    print("Creating dataset...")
    try:
        manager.create_dataset(
            name="example-tests",
            description="Example test dataset"
        )
        print("✓ Dataset created: example-tests\n")
    except Exception as e:
        print(f"Dataset may already exist: {e}\n")

    # Add example
    print("Adding test example...")
    try:
        manager.add_example(
            dataset_name="example-tests",
            inputs={
                "messages": [
                    {"role": "user", "content": "What's the weather in San Francisco?"}
                ]
            },
            outputs={
                "expected_route": "weather_agent",
                "expected_tools": ["weather_lookup"]
            },
            metadata={
                "category": "weather",
                "difficulty": "easy"
            }
        )
        print("✓ Example added\n")
    except Exception as e:
        print(f"Failed to add example: {e}\n")

    # List datasets
    print("Available datasets:")
    datasets = manager.list_datasets()
    for ds in datasets[:5]:  # Show first 5
        print(f"  - {ds['name']}: {ds.get('example_count', 0)} examples")


def example_4_offline_evaluation():
    """
    Example 4: Run offline evaluation against a dataset.
    """
    print("\n" + "="*70)
    print("EXAMPLE 4: Offline Evaluation")
    print("="*70 + "\n")

    from agent import create_agent
    from agent_eval import OfflineEvaluator

    evaluator = OfflineEvaluator()

    print("Running evaluation...")
    print("Note: This requires a dataset named 'regression-tests' to exist.\n")

    try:
        results = evaluator.evaluate_agent(
            agent_or_factory=create_agent(),
            dataset_name="regression-tests",
            experiment_name="example-run"
        )

        print("✓ Evaluation complete!")
        print(f"Experiment: {results['experiment_name']}")
        print(f"Dataset: {results['dataset_name']}")
        print(f"Metrics: {results['aggregate_metrics']}")

        # Check quality gates
        passed, failures = evaluator.check_quality_gates(results)

        if passed:
            print("\n✓ All quality gates passed!")
        else:
            print(f"\n✗ Quality gates failed:")
            for failure in failures:
                print(f"  - {failure}")

    except Exception as e:
        print(f"✗ Evaluation failed: {e}")
        print("\nTo fix:")
        print("1. Create a dataset first (see example_3)")
        print("2. Ensure LANGSMITH_API_KEY is set")


def example_5_export_failures_to_dataset():
    """
    Example 5: Export production failures as test cases.
    """
    print("\n" + "="*70)
    print("EXAMPLE 5: Export Production Failures")
    print("="*70 + "\n")

    from agent_eval import OnlineEvaluationHelper

    helper = OnlineEvaluationHelper("opensentinel-prod")

    print("Exporting failing traces to dataset...")
    print("This creates a regression test suite from real failures.\n")

    try:
        count = helper.export_failing_traces_to_dataset(
            dataset_name="production-failures",
            score_threshold=0.5,
            limit=10
        )

        print(f"✓ Exported {count} failing traces to 'production-failures' dataset")
        print("\nNow you can run offline evaluation against these failures:")
        print("   >>> evaluator.evaluate_agent(agent, 'production-failures')")

    except Exception as e:
        print(f"✗ Export failed: {e}")
        print("\nRequires production traces with evaluation scores.")


def example_6_pre_built_datasets():
    """
    Example 6: Use pre-built test datasets.
    """
    print("\n" + "="*70)
    print("EXAMPLE 6: Pre-built Test Datasets")
    print("="*70 + "\n")

    from agent_eval import (
        create_test_dataset_for_routing,
        create_test_dataset_for_tools
    )

    print("Creating routing test suite...")
    try:
        count = create_test_dataset_for_routing("routing-tests")
        print(f"✓ Created routing-tests with {count} examples\n")
    except Exception as e:
        print(f"Dataset may exist: {e}\n")

    print("Creating tool test suite...")
    try:
        count = create_test_dataset_for_tools("tool-tests")
        print(f"✓ Created tool-tests with {count} examples\n")
    except Exception as e:
        print(f"Dataset may exist: {e}\n")

    print("These datasets are ready for evaluation:")
    print("   >>> evaluator.evaluate_agent(agent, 'routing-tests')")
    print("   >>> evaluator.evaluate_agent(agent, 'tool-tests')")


def example_7_ci_cd_integration():
    """
    Example 7: CI/CD quality gate script.
    """
    print("\n" + "="*70)
    print("EXAMPLE 7: CI/CD Integration")
    print("="*70 + "\n")

    print("Use this pattern in your CI pipeline:\n")

    print("""```python
# tests/test_agent_quality.py
import sys
from agent import create_agent
from agent_eval import OfflineEvaluator

def test_regression():
    evaluator = OfflineEvaluator()
    passed = evaluator.run_regression_tests(
        agent_or_factory=create_agent(),
        dataset_name='regression-tests'
    )

    assert passed, "Regression tests failed - quality gates not met"

if __name__ == '__main__':
    test_regression()
```\n""")

    print("GitHub Actions workflow:\n")

    print("""```yaml
name: Agent Quality Gates

on: [pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        env:
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
        run: pytest tests/test_agent_quality.py
```\n""")


def example_8_custom_evaluators():
    """
    Example 8: Use custom evaluators.
    """
    print("\n" + "="*70)
    print("EXAMPLE 8: Custom Evaluators")
    print("="*70 + "\n")

    from agent_eval import (
        ToolCallCorrectnessEvaluator,
        RoutingDecisionEvaluator,
        TrajectoryEvaluator,
        SafetyEvaluator
    )

    print("Pre-built evaluators:\n")

    print("1. Tool Correctness (fast, <50ms):")
    print("   >>> tool_eval = ToolCallCorrectnessEvaluator()")
    print("   >>> result = tool_eval.evaluate_run(run)\n")

    print("2. Routing Correctness:")
    print("   >>> routing_eval = RoutingDecisionEvaluator()")
    print("   >>> result = routing_eval.evaluate_run(run, example)\n")

    print("3. Trajectory (analyzes full path):")
    print("   >>> trajectory_eval = TrajectoryEvaluator(")
    print("   ...     expected_tools=['search', 'summarize']")
    print("   ... )")
    print("   >>> result = trajectory_eval.evaluate_run(run)\n")

    print("4. Safety:")
    print("   >>> safety_eval = SafetyEvaluator()")
    print("   >>> result = safety_eval.evaluate_run(run)\n")

    print("Use in offline evaluation:")
    print("   >>> evaluator.evaluate_agent(")
    print("   ...     agent, 'my-dataset',")
    print("   ...     evaluators=[tool_eval, routing_eval, trajectory_eval]")
    print("   ... )")


def main():
    """Run all examples."""
    examples = [
        ("Enable Tracing", example_1_enable_tracing),
        ("Setup Online Evaluation", example_2_setup_online_evaluation),
        ("Create Test Dataset", example_3_create_test_dataset),
        ("Offline Evaluation", example_4_offline_evaluation),
        ("Export Failures", example_5_export_failures_to_dataset),
        ("Pre-built Datasets", example_6_pre_built_datasets),
        ("CI/CD Integration", example_7_ci_cd_integration),
        ("Custom Evaluators", example_8_custom_evaluators),
    ]

    print("\n" + "="*70)
    print("AGENT_EVAL EXAMPLES (2026 LangSmith)")
    print("="*70)

    print("\nAvailable examples:")
    for i, (name, _) in enumerate(examples, 1):
        print(f"  {i}. {name}")

    print("\nRun all examples? (y/n): ", end="")

    try:
        choice = input().strip().lower()
    except:
        choice = "y"  # Default to yes if no input

    if choice == "y":
        for name, func in examples:
            func()
    else:
        print("\nTo run individual examples:")
        print("   >>> from agent_eval.examples import example_1_enable_tracing")
        print("   >>> example_1_enable_tracing()")

    print("\n" + "="*70)
    print("Done! Check the agent_eval/README.md for more details.")
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
