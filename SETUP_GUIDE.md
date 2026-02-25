# OpenSentinel Setup & Testing Guide

## Prerequisites

- Python 3.11 or higher
- (Optional) Ollama installed if using local models

## Quick Start

### 1. Install Dependencies

```bash
# Install the project with all dependencies
pip install -e .

# Or if you prefer uv (faster)
uv pip install -e .
```

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and set your model configuration:

#### Option A: Using Ollama (Local, Free)

```bash
# In your .env file:
OPENSENTINEL_MODEL_NAME=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
OPENSENTINEL_MODEL_TEMPERATURE=0.3
OPENSENTINEL_MODEL_MAX_TOKENS=8192
```

**Before running, make sure Ollama is installed and running:**

```bash
# Install Ollama from: https://ollama.com/download

# Pull a model (if not already available)
ollama pull llama3.2

# Verify Ollama is running
ollama list

# If not running, start it:
ollama serve
```

#### Option B: Using Claude (Anthropic)

```bash
# In your .env file:
OPENSENTINEL_MODEL_NAME=claude-3-5-sonnet-20241022
ANTHROPIC_API_KEY=sk-ant-your-key-here
OPENSENTINEL_MODEL_TEMPERATURE=0.3
OPENSENTINEL_MODEL_MAX_TOKENS=8192
```

Get your API key from: https://console.anthropic.com/settings/keys

#### Option C: Using OpenAI GPT

```bash
# In your .env file:
OPENSENTINEL_MODEL_NAME=openai/gpt-4
OPENAI_API_KEY=sk-your-key-here
```

Get your API key from: https://platform.openai.com/api-keys

### 3. Run the Test

```bash
python test_agent.py
```

You should see output like:

```
============================================================
OpenSentinel Agent Test
============================================================

✓ Model configured: llama3.2
  Temperature: 0.3
  Max tokens: 8192
  Ollama URL: http://localhost:11434

============================================================
Creating agent...
============================================================
✓ Agent created successfully!

============================================================
Testing agent with a simple query...
============================================================

Query: What can you help me with today?

Response:
[Agent response here...]

============================================================
✓ Test completed successfully!
============================================================
```

## Architecture Overview

OpenSentinel uses a **supervisor + subagent** architecture:

- **Main Agent (Supervisor)**: Orchestrates tasks and delegates to specialists
- **11 Specialized Subagents**:
  - `scheduling_coordinator` - Calendar management
  - `email_triage_specialist` - Email processing
  - `task_strategist` - Task prioritization
  - `daily_briefing_compiler` - Morning briefings
  - `research_analyst` - Deep research
  - `report_generator` - Report writing
  - `weather_advisor` - Weather analysis
  - `culinary_advisor` - Recipe suggestions
  - `travel_coordinator` - Travel planning
  - `system_monitor` - System health
  - `approval_gatekeeper` - Safety & permissions

## Testing Individual Subagents

Edit `test_agent.py` and uncomment the test you want to run:

```python
if __name__ == "__main__":
    # Run basic test
    main()

    # Test a specific subagent
    test_subagent()  # Uncomment this line
```

## Advanced Configuration

### Using Different Models for Subagents

You can use a powerful model for the main agent and faster models for subagents:

```bash
# Main agent uses a large model
OPENSENTINEL_MODEL_NAME=llama3.2

# Subagents use a smaller, faster model
OPENSENTINEL_SUBAGENT_MODEL_NAME=llama3.2:8b
```

### Adjusting Model Parameters

```bash
# Lower temperature = more focused/deterministic
OPENSENTINEL_MODEL_TEMPERATURE=0.1

# Higher temperature = more creative/varied
OPENSENTINEL_MODEL_TEMPERATURE=0.9

# Adjust max tokens based on your needs
OPENSENTINEL_MODEL_MAX_TOKENS=4096
```

## Troubleshooting

### Error: "Failed to initialize model"

**Solution**: Check that:
1. Ollama is running (`ollama serve`)
2. The model is installed (`ollama list`)
3. The URL is correct in `.env`

### Error: "No default model configured"

**Solution**: Make sure your `.env` file has `OPENSENTINEL_MODEL_NAME` set:

```bash
OPENSENTINEL_MODEL_NAME=llama3.2
```

### Error: "Connection refused" or "Connection error"

**Solution for Ollama**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model is too slow

**Solution**: Try a smaller model:
```bash
# Switch to a smaller model
OPENSENTINEL_MODEL_NAME=llama3.2:8b

# Or even smaller
OPENSENTINEL_MODEL_NAME=qwen2.5:3b
```

### Out of memory errors

**Solution**:
1. Use a smaller model
2. Reduce max tokens:
   ```bash
   OPENSENTINEL_MODEL_MAX_TOKENS=2048
   ```
3. If using Ollama, try loading the model with reduced context:
   ```bash
   ollama run llama3.2 --context-length 4096
   ```

## Project Structure

```
OpenSentinel/
├── src/
│   ├── Agent/
│   │   ├── agent.py              # Main orchestrator
│   │   ├── llm_factory.py        # Model initialization
│   │   ├── subagents/            # Specialist agents
│   │   │   ├── __init__.py
│   │   │   ├── scheduling_coordinator.py
│   │   │   ├── email_triage_specialist.py
│   │   │   ├── ... (9 more)
│   │   └── tools/                # Atomic tools
│   │       ├── __init__.py
│   │       ├── calendar.py
│   │       ├── email_tools.py
│   │       └── ... (more tools)
├── test_agent.py                 # Test script
├── .env                          # Your configuration (not in git)
├── .env.example                  # Template
├── pyproject.toml                # Dependencies
└── AGENT_CLEANUP.md              # Architecture docs
```

## Next Steps

1. ✅ Install dependencies
2. ✅ Configure `.env`
3. ✅ Run `test_agent.py`
4. Try asking the agent to delegate to a subagent:
   - "What's the weather like?" → delegates to `weather_advisor`
   - "Find me a recipe for pasta" → delegates to `culinary_advisor`
   - "Help me plan my day" → delegates to `daily_briefing_compiler`
5. Build your own integrations using the tools in `src/Agent/tools/`

## Resources

- [DeepAgents Documentation](https://github.com/deepagents/deepagents)
- [Ollama Models](https://ollama.com/library)
- [LangChain Documentation](https://python.langchain.com/)
- [Architecture Guide](AGENT_CLEANUP.md)

## Getting Help

If you run into issues:
1. Check this guide's troubleshooting section
2. Review the error messages carefully
3. Verify your `.env` configuration
4. Check that all services (Ollama, etc.) are running
