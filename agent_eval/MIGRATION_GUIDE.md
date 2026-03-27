# Migration Guide: v1 → v2 (2026 LangSmith)

## What Changed?

Your `agent_eval` module has been completely rewritten to align with **LangSmith 2026 best practices**.

### Old Approach (v1)
- Custom `ToolCallEvaluator` with inline + async pipeline
- Custom `AsyncEvalPipeline` for background evaluation
- Manual JSONL logging
- Custom LLM judge implementation
- No native LangSmith integration

### New Approach (v2 - 2026)
- **Native LangSmith integration** (automatic tracing)
- **Online evaluators** configured in UI (not code!)
- **Offline evaluation** using `client.run_on_dataset()`
- **Multi-turn conversation evaluation** (NEW!)
- **Trajectory evaluation** for complex workflows
- **Insights Agent** for automatic failure clustering

## Breaking Changes

### 1. Removed Files
- ❌ `evaluator.py` → ✅ `evaluators.py` (LangSmith-compatible)
- ❌ `async_pipeline.py` → ✅ `online_evaluation.py` (UI helper)

### 2. API Changes

#### Before (v1):
```python
from agent_eval import ToolCallEvaluator, AsyncEvalPipeline

evaluator = ToolCallEvaluator()
pipeline = AsyncEvalPipeline()

# Evaluate single tool call
result = evaluator.evaluate_tool_call(
    tool_name="search",
    tool_args={"query": "test"},
    tool_output={"results": [...]}
)
```

#### After (v2):
```python
from agent_eval import OfflineEvaluator, setup_production_tracing

# Offline: Evaluate full agent against dataset
evaluator = OfflineEvaluator()
results = evaluator.evaluate_agent(
    agent_or_factory=create_agent(),
    dataset_name="my-tests"
)

# Online: Configure in UI
helper = setup_production_tracing()
helper.print_setup_instructions()
```

### 3. Configuration Changes

#### Before (v1):
```python
from agent_eval import EvalConfig, DEFAULT_CONFIG

config = EvalConfig(
    enable_async_pipeline=True,
    llm_judge_sample_rate=0.05,
    log_path="./eval_logs.jsonl"
)
```

#### After (v2):
```python
from agent_eval import EvalConfig

config = EvalConfig()
config.online.trajectory_eval_sampling = 0.05
config.offline.min_tool_correctness = 0.95
config.langsmith.project_name = "opensentinel-prod"
```

## Migration Steps

### Step 1: Enable LangSmith Tracing

Add to `.env`:
```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=your_key_here
LANGSMITH_PROJECT=opensentinel-dev
```

### Step 2: Update Dependencies

Already done in `pyproject.toml`:
```toml
"langsmith>=0.5.0",  # Updated for 2026
```

Run:
```bash
uv sync
```

### Step 3: Replace Custom Evaluator Code

**If you had:**
```python
# Old code in your agent
from agent_eval import ToolCallEvaluator

evaluator = ToolCallEvaluator()
result = evaluator.evaluate_tool_call(...)
```

**Replace with:**

For **production monitoring** (online):
1. Remove inline evaluation code from agent
2. Configure online evaluators in LangSmith UI
3. Tag traces for filtering:
```python
from agent_eval import setup_production_tracing

helper = setup_production_tracing()
tags = helper.get_trace_tags_for_tool_eval("tavily_search")

agent.invoke(
    {"messages": [...]},
    config={"tags": tags}  # Enables filtering
)
```

For **development/testing** (offline):
```python
from agent_eval import OfflineEvaluator

evaluator = OfflineEvaluator()
results = evaluator.evaluate_agent(
    agent_or_factory=create_agent(),
    dataset_name="regression-tests"
)
```

### Step 4: Create Test Datasets

**Old approach:** Manual JSONL logs

**New approach:** LangSmith datasets
```python
from agent_eval import DatasetManager, create_test_dataset_for_routing

# Create pre-built datasets
create_test_dataset_for_routing("routing-tests")

# Or create custom
manager = DatasetManager()
manager.create_dataset("my-tests")
manager.add_example("my-tests", inputs={...}, outputs={...})

# Export production failures
manager.export_runs_to_dataset(
    dataset_name="prod-failures",
    project_name="opensentinel-prod"
)
```

### Step 5: Setup Online Evaluators (Production)

**Old approach:** Custom `AsyncEvalPipeline` in code

**New approach:** Configure in LangSmith UI

```python
from agent_eval import setup_production_tracing

helper = setup_production_tracing("opensentinel-prod")
helper.print_setup_instructions()  # Shows step-by-step UI guide
```

Then follow instructions to configure evaluators in LangSmith UI.

### Step 6: Update CI/CD

**Old approach:** Run custom evaluation scripts

**New approach:** Use offline evaluation

```python
# tests/test_agent_quality.py
from agent import create_agent
from agent_eval import OfflineEvaluator

def test_regression():
    evaluator = OfflineEvaluator()
    passed = evaluator.run_regression_tests(
        agent_or_factory=create_agent(),
        dataset_name='regression-tests'
    )
    assert passed
```

GitHub Actions:
```yaml
- name: Run quality gates
  env:
    LANGSMITH_API_KEY: ${{ secrets.LANGSMITH_API_KEY }}
  run: pytest tests/test_agent_quality.py
```

## Feature Mapping

| v1 Feature | v2 Equivalent | Notes |
|------------|---------------|-------|
| `ToolCallEvaluator` | `ToolCallCorrectnessEvaluator` | Now LangSmith-compatible |
| `AsyncEvalPipeline` | Online evaluators (UI) | Configure in LangSmith UI |
| JSONL logging | LangSmith trace storage | Automatic |
| Custom LLM judge | `openevals` + LLM-as-judge | Pre-built evaluators |
| Manual batching | Automatic | Built into LangSmith |
| - | `MultiTurnConversationEvaluator` | NEW! Thread-level eval |
| - | `TrajectoryEvaluator` | NEW! Path analysis |
| - | Insights Agent | NEW! Auto clustering |

## Benefits of v2

### 1. Zero-Code Tracing
Just set env vars - LangGraph automatically traces everything.

### 2. UI-Configured Online Evaluators
- No SDK code required
- Easy to modify without redeployment
- Built-in batching, alerts, webhooks

### 3. Multi-Turn Evaluation (NEW 2026!)
Evaluate complete conversations, not just single turns.

### 4. Insights Agent (NEW 2026!)
Automatically clusters production traces to find failure patterns.

### 5. Dataset-Driven Development
- Export failures as test cases
- Run offline regression tests
- Compare experiments easily

### 6. CI/CD Quality Gates
Block deployments if scores drop below thresholds.

## Backward Compatibility

### What Still Works

The old API is **removed**, but the concepts transfer:

| Old Concept | New Concept |
|-------------|-------------|
| Inline checks | Online evaluators (UI) |
| Async pipeline | Online evaluators (UI) |
| High-risk tools | Safety evaluator |
| Sampling | Configure in UI |

### What Doesn't Work Anymore

- ❌ `ToolCallEvaluator.evaluate_tool_call()` → Use offline evaluation
- ❌ `AsyncEvalPipeline.submit()` → Use online evaluators (UI)
- ❌ Custom JSONL logs → Use LangSmith trace storage

## Troubleshooting

### "My evaluations aren't running!"

**For online (production):**
1. Check `LANGSMITH_TRACING=true` in `.env`
2. Verify traces appear in LangSmith UI
3. Configure evaluators in UI (Project → Evaluators)
4. Ensure trace tags match evaluator filters

**For offline (testing):**
1. Ensure dataset exists
2. Check `LANGSMITH_API_KEY` is set
3. Verify agent factory returns valid agent

### "I want the old inline checks back!"

The `ToolCallCorrectnessEvaluator` provides similar fast checks, but is now:
- LangSmith-compatible
- Works in offline evaluation
- Can be used in online evaluators (UI)

For production, configure as a **Code Evaluator** in LangSmith UI.

### "Where are my JSONL logs?"

Replace with LangSmith trace storage:
- View in UI: https://smith.langchain.com
- Query programmatically: `client.list_runs(project_name="...")`
- Export to CSV/JSON from UI

## Next Steps

1. ✅ Enable tracing (`.env`)
2. ✅ Create test datasets
3. ✅ Run offline evaluation
4. ✅ Configure online evaluators (UI)
5. ✅ Setup CI/CD quality gates
6. ✅ Export production failures as tests

See `agent_eval/README.md` for detailed examples!

## Questions?

- Check `agent_eval/examples.py` for working code
- Read `agent_eval/README.md` for full documentation
- LangSmith Docs: https://docs.langchain.com/langsmith
