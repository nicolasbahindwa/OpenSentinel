# Modular System Prompt Architecture

## Overview

To minimize token usage, OpenSentinel's system prompt is split into modular components that can be loaded on-demand based on context needs.

## Prompt Modules

### 1. `core.md` (Always Loaded)
**~150 tokens**
- Essential identity (OpenSentinel, OpenClaw principles)
- Adaptive use cases (Personal/Family/Enterprise)
- Core mission and values
- **When to use**: Every agent invocation

### 2. `capabilities.md` (Standard Mode)
**~250 tokens**
- Three-tier architecture (Skills/Subagents/Tools)
- Decision logic for choosing the right capability level
- List of available skills, subagents, and tool domains
- **When to use**: When user needs to understand what the agent can do

### 3. `safety.md` (Standard Mode)
**~200 tokens**
- Critical action detection rules
- Approval workflow implementation
- Audit trail requirements
- **When to use**: Always for production use (safety-critical)

### 4. `quality_standards.md` (Full Mode)
**~300 tokens**
- Output formatting guidelines
- Citation requirements
- Proactive monitoring rules
- Weather/system health alert thresholds
- **When to use**: When generating daily briefings, reports, or user-facing content

## Loading Modes

Configure in `agent.py`:

```python
# Minimal mode (~150 tokens) - Core identity only
SYSTEM_PROMPT = load_system_prompt(mode="minimal")

# Standard mode (~600 tokens) - Core + Capabilities + Safety
SYSTEM_PROMPT = load_system_prompt(mode="standard")  # DEFAULT

# Full mode (~900 tokens) - All modules
SYSTEM_PROMPT = load_system_prompt(mode="full")
```

## Token Savings

| Mode | Tokens | Use Case |
|------|--------|----------|
| **Minimal** | ~150 | Quick tool calls, simple queries |
| **Standard** | ~600 | Normal operations, multi-step tasks |
| **Full** | ~900 | Daily briefings, reports, complex workflows |

**Comparison**: Original monolithic prompt was ~1500 tokens. Standard mode saves **60%** of tokens.

## Dynamic Context Loading

For even more efficiency, you can load specific modules per task:

```python
# For safety-critical actions only
prompt = load_system_prompt(mode="minimal")
with open(PROMPTS_DIR / "safety.md") as f:
    prompt += "\n\n" + f.read()

# For report generation only
prompt = load_system_prompt(mode="minimal")
with open(PROMPTS_DIR / "quality_standards.md") as f:
    prompt += "\n\n" + f.read()
```

## Adding New Modules

To add a new prompt module:

1. Create `src/prompts/your_module.md`
2. Update `load_system_prompt()` in `agent.py` to include it
3. Document token count and use case here

## Best Practices

- **Always include `core.md`**: Contains essential identity
- **Always include `safety.md` in production**: Critical for OpenClaw compliance
- **Load `quality_standards.md` for user-facing outputs**: Ensures consistent, high-quality responses
- **Use minimal mode for background tasks**: Token efficiency for scheduled automation
