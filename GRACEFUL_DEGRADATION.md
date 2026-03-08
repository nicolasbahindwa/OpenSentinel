# Graceful Degradation - Handling Missing API Keys

## Problem (RESOLVED)

The agent was crashing when `OPENWEATHERMAP_API_KEY` wasn't configured:

```
ValueError: OPENWEATHERMAP_API_KEY environment variable required
```

This happened even though the agent wasn't trying to use the weather tool - it failed during initialization!

## Solution (NOW OBSOLETE - See Update Below)

Initially, we implemented **graceful degradation** - tools without API keys return `None` and are filtered out:

**UPDATE:** The weather tool now uses the free Open-Meteo API and no longer requires an API key!

### Before (Crash) ❌

```python
@cached_property
def weather_lookup(self) -> BaseTool:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    return WeatherLookupTool(api_key=api_key)  # ← Crashes if no API key
```

### After (Graceful) ✅

**OLD APPROACH (No longer needed):**
```python
@cached_property
def weather_lookup(self) -> Optional[BaseTool]:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if api_key:
        return WeatherLookupTool(api_key=api_key)  # ← Only if key available
    else:
        return None  # ← Gracefully return None
```

**NEW APPROACH (Current - No API key required):**
```python
@cached_property
def weather_lookup(self) -> BaseTool:
    # No API key needed - Open-Meteo is free!
    return WeatherLookupTool()
```

## How It Works

### 1. Lazy Loader Returns None

```python
class LazyToolLoader:
    @cached_property
    def weather_lookup(self) -> Optional[BaseTool]:
        api_key = os.getenv("OPENWEATHERMAP_API_KEY")
        if api_key:
            return WeatherLookupTool(api_key=api_key)
        return None  # No key? No tool
```

### 2. Wrapper Filters Out None

```python
class LazyToolWrapper:
    def __iter__(self):
        tools = [
            self._loader.internet_search,  # Always available
            self._loader.weather_lookup,   # May be None
        ]
        # Filter out None values
        self._loaded_tools = [t for t in tools if t is not None]
        return iter(self._loaded_tools)
```

### 3. Agent Gets Only Available Tools

```python
# With TAVILY_API_KEY only:
tools = [internet_search]  # 1 tool

# With both API keys:
tools = [internet_search, weather_lookup]  # 2 tools
```

## Required vs Optional API Keys

### Required (Agent Won't Start Without)
- ✅ `NVIDIA_API_KEY` - Required for the model
- ✅ `TAVILY_API_KEY` - Required for internet_search (core functionality)

### Optional (Agent Works Without)
- ⚠️ `ANTHROPIC_API_KEY` - If using Anthropic models
- ⚠️ `OPENAI_API_KEY` - If using OpenAI models
- ⚠️ `GOOGLE_API_KEY` - If using Google models

### No Longer Required
- ~~❌ `OPENWEATHERMAP_API_KEY`~~ - **Not needed anymore!** Weather tool now uses free Open-Meteo API

## Configuration

In `.env`:

```bash
# Required
NVIDIA_API_KEY=your_nvidia_key
TAVILY_API_KEY=your_tavily_key

# Optional - agent works without these
# ANTHROPIC_API_KEY=your_anthropic_key
# OPENAI_API_KEY=your_openai_key
# GOOGLE_API_KEY=your_google_key

# No longer needed - weather tool uses free Open-Meteo API
# OPENWEATHERMAP_API_KEY=your_openweather_key  # ← NOT REQUIRED!
```

## Benefits

✅ **No crashes** - Missing API keys don't break the agent
✅ **Flexible deployment** - Configure only what you need
✅ **Development friendly** - Work with minimal keys during dev
✅ **Production ready** - Add keys as needed

## Example Scenarios

### Scenario 1: Development (Minimal Keys - CURRENT)

```bash
# .env
NVIDIA_API_KEY=xxx
TAVILY_API_KEY=xxx
```

**Result:**
- Agent starts successfully ✅
- Has internet_search tool ✅
- Has weather_lookup tool ✅ (uses free Open-Meteo API!)
- Weather queries → Uses dedicated weather_lookup tool ✅
- No crashes ✅
- **No additional API keys needed!** ✅

### Scenario 2: Production (Same Keys - No Change Needed)

```bash
# .env
NVIDIA_API_KEY=xxx
TAVILY_API_KEY=xxx
# No OPENWEATHERMAP_API_KEY needed!
```

**Result:**
- Agent starts successfully ✅
- Has both tools ✅
- Weather queries → Uses dedicated weather_lookup tool ✅
- Optimal performance ✅
- **One less API key to manage!** ✅

## Monitoring

Check which tools are available:

```python
from agent.tools.lazy_loader import _tool_loader

# Check loaded tools
tools = _tool_loader.get_all_tools()
print(f"Available tools: {[t.name for t in tools]}")

# Output (always has both tools now):
# Available tools: ['internet_search', 'weather_lookup']
```

## Future Enhancements

This pattern can be extended to:
- More API-dependent tools
- Database connections
- External service integrations
- Feature flags

**Principle:** Always degrade gracefully - missing features shouldn't crash the entire system!
