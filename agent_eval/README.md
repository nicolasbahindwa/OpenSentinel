# OpenSentinel Agent Evaluation (2026)

Modern evaluation and observability for OpenSentinel, built on **LangSmith 2026** best practices.

## Overview

This evaluation framework provides:
- **Automatic tracing** for LangGraph agents (zero-code integration)
- **Online evaluators** for production monitoring (UI-configured)
- **Offline evaluation** against curated datasets
- **Multi-turn conversation** evaluation (NEW in 2026!)
- **Trajectory analysis** for complex agent workflows
- **CI/CD quality gates** for deployment blocking

## Quick Start

### 1. Enable LangSmith Tracing

Add to your `.env`:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=opensentinel-dev
```

That's it! Your agent is now automatically traced. View traces at https://smith.langchain.com

### 2. Production Monitoring (Online Evaluation)

Online evaluators are **configured in the LangSmith UI**, not code.

```python
from agent_eval import setup_production_tracing

# Get setup instructions
helper = setup_production_tracing("opensentinel-prod")
helper.print_setup_instructions()

# Tag your traces for filtering
tags = helper.get_trace_tags_for_tool_eval("tavily_search")

# Use tags when invoking agent
from agent import create_agent
agent = create_agent()
agent.invoke(
    {"messages": [HumanMessage(content="Search for AI news")]},
    config={"tags": tags}  # Enables filtering in online evaluators
)
```

Then configure evaluators in LangSmith UI:
1. Go to Project → **Evaluators** tab → **+ New**
2. Select type: **LLM-as-judge** or **Code**
3. Set filter: `tag:tool:tavily_search`
4. Set sampling rate: `10%`
5. Save

Evaluations run automatically on production traffic!

### 3. Offline Evaluation (Development/CI)

Test against curated datasets before deployment:

```python
from agent import create_agent
from agent_eval import OfflineEvaluator

# Create evaluator
evaluator = OfflineEvaluator()

# Run evaluation
results = evaluator.evaluate_agent(
    agent_or_factory=create_agent(),
    dataset_name="regression-tests",
    experiment_name="fix-routing-v2"
)

# Check quality gates (CI/CD)
passed, failures = evaluator.check_quality_gates(results)
if not passed:
    print(f"Quality gates failed: {failures}")
    sys.exit(1)  # Block deployment
```

### 4. Create Test Datasets

```python
from agent_eval import DatasetManager

manager = DatasetManager()

# Create dataset
manager.create_dataset("my-tests", description="Routing tests")

# Add examples
manager.add_example(
    dataset_name="my-tests",
    inputs={"query": "What's the weather in SF?"},
    outputs={"expected_route": "weather_agent"},
    metadata={"category": "weather"}
)

# Export production failures as test cases
manager.export_runs_to_dataset(
    dataset_name="production-failures",
    project_name="opensentinel-prod",
    limit=50
)
```

### 5. Pre-built Test Datasets

```python
from agent_eval import (
    create_test_dataset_for_routing,
    create_test_dataset_for_tools
)

# Create routing test suite
create_test_dataset_for_routing("routing-tests")

# Create tool test suite
create_test_dataset_for_tools("tool-tests")
```

## Evaluator Types

### Tool Correctness
Fast technical validation:
- Checks for errors in output
- Validates schema (JSON, dict, list)
- <50ms latency

```python
from agent_eval import tool_correctness

# Used automatically in offline evaluation
# Or create custom instance:
evaluator = ToolCallCorrectnessEvaluator(enable_schema_validation=True)
```

### Routing Correctness
Validates routing decisions:
- Did agent route to correct subagent?
- Was user intent classified correctly?

```python
from agent_eval import routing_correctness

# Tag traces for routing evaluation
metadata = helper.get_trace_metadata_for_routing(
    route_decision="weather_agent",
    intent="weather_query"
)
agent.invoke({...}, config={"metadata": metadata, "tags": ["routing"]})
```

### Trajectory Evaluation
Analyzes full decision paths:
- Gives partial credit for correct intermediate steps
- Evaluates tool call sequences
- Essential for multi-step agents

```python
from agent_eval import trajectory

# Configure expected tools
evaluator = TrajectoryEvaluator(expected_tools=["search", "summarize"])
```

### Multi-Turn Conversations (NEW 2026!)
Evaluates complete conversation threads:
- Did agent accomplish user's goal?
- Was conversation helpful throughout?

**Configure in LangSmith UI:**
1. Evaluators → + New → LLM-as-Judge
2. **Target: Threads** (not single runs!)
3. Filter: `tag:conversation`
4. Prompt: "Did the agent accomplish the user's goal?"

### Safety Evaluation
Monitors guardrails:
- High-risk tool usage
- Guardrail triggers
- Inappropriate requests

```python
from agent_eval import safety

# Automatically flags high-risk operations
```

## Configuration

### Environment-Specific Configs

```python
from agent_eval import get_dev_config, get_staging_config, get_prod_config

# Development: Higher sampling, verbose
config = get_dev_config()

# Staging: Medium sampling, thorough testing
config = get_staging_config()

# Production: Lower sampling, auto-export failures
config = get_prod_config()
```

### Custom Configuration

```python
from agent_eval import EvalConfig

config = EvalConfig()
config.online.trajectory_eval_sampling = 0.1  # 10% of traces
config.online.alert_webhook = "https://your-alerts.com/webhook"
config.offline.min_tool_correctness = 0.95  # Quality gate threshold
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Agent Tests

on: [pull_request]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2

      - name: Install dependencies
        run: uv sync

      - name: Run regression tests
        env:
          LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
          LANGSMITH_TRACING: true
        run: |
          python -c "
          from agent import create_agent
          from agent_eval import OfflineEvaluator

          evaluator = OfflineEvaluator()
          passed = evaluator.run_regression_tests(
              agent_or_factory=create_agent(),
              dataset_name='regression-tests'
          )

          exit(0 if passed else 1)
          "
```

## Advanced: Comparing Experiments

```python
from agent import create_agent
from agent_eval import evaluate_routing_changes

# Test routing changes
comparison = evaluate_routing_changes(
    agent_or_factory=create_agent(),
    baseline_experiment="routing-v1",
    new_experiment_name="routing-v2",
    dataset_name="routing-test-suite"
)

if comparison["winner"] == "routing-v2":
    print("New routing is better!")
    print(f"Improvements: {comparison['improvements']}")
```

## Insights Agent (NEW 2026!)

LangSmith's Insights Agent automatically clusters production traces to find patterns:

1. Go to LangSmith UI → Your Project → **Insights**
2. Click **Run Analysis**
3. Wait ~15 minutes
4. View clustered failure modes and usage patterns

No code required!

## Best Practices

### 1. The Agent Reliability Loop
```
Trace → Find Failures → Create Dataset → Run Offline Eval → Deploy → Repeat
```

### 2. Tagging Strategy
- Use `tag:production` for all prod traffic
- Use `tag:tool:{tool_name}` for tool-specific evaluation
- Use `tag:high-risk` for dangerous operations
- Use `tag:routing` for routing decisions

### 3. Sampling Rates
- **Tool correctness**: 100% (fast, always run)
- **Routing**: 10% (medium cost)
- **Trajectory**: 5% (expensive LLM-as-judge)
- **Safety**: 100% (critical)

### 4. Quality Gates
Set thresholds in config:
```python
config.offline.min_tool_correctness = 0.95
config.offline.min_routing_correctness = 0.90
config.offline.min_trajectory_score = 0.80
config.offline.min_safety_score = 0.95
```

## Troubleshooting

### Traces not appearing?
1. Check `LANGSMITH_TRACING=true` in `.env`
2. Verify `LANGSMITH_API_KEY` is set
3. Confirm project name matches in UI

### Online evaluators not running?
- Online evaluators are **UI-configured**, not SDK
- Check Project → Evaluators tab
- Verify trace tags match evaluator filters

### Offline evaluation errors?
- Ensure dataset exists: `manager.list_datasets()`
- Check agent factory returns valid agent
- Verify evaluators are compatible with your agent

## Migration from v1 (Old Custom Code)

If you had custom evaluation code:

### Before (v1):
```python
from agent_eval import ToolCallEvaluator, AsyncEvalPipeline

evaluator = ToolCallEvaluator()
pipeline = AsyncEvalPipeline()
result = evaluator.evaluate_tool_call(tool_name, args, output)
```

### After (v2 - 2026):
```python
from agent_eval import OfflineEvaluator, setup_production_tracing

# Offline
evaluator = OfflineEvaluator()
results = evaluator.evaluate_agent(agent, "my-dataset")

# Online (UI-configured)
helper = setup_production_tracing()
helper.print_setup_instructions()
```

## Resources

- [LangSmith Docs](https://docs.langchain.com/langsmith)
- [Online Evaluators Guide](https://docs.langchain.com/langsmith/online-evaluations-llm-as-judge)
- [Offline Evaluation Guide](https://docs.langchain.com/langsmith/evaluate-llm-application)
- [Multi-turn Evals Blog](https://blog.langchain.com/insights-agent-multiturn-evals-langsmith/)

## Support

Questions? Issues?
- GitHub: [OpenSentinel Issues](https://github.com/yourorg/opensentinel/issues)
- LangSmith Support: https://support.langchain.com
