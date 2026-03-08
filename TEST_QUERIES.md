# Test Queries for Agent Tool Calling

Use these queries to verify that the agent is calling the internet_search tool correctly.

## ✅ Queries That SHOULD Trigger internet_search

### Weather Queries
```
1. "What's the weather tomorrow in Tokyo?"
   Expected: Calls internet_search with "Tokyo weather forecast March 8 2026"

2. "How should I dress for the weather today in New York?"
   Expected: Calls internet_search for current NYC weather

3. "Will it rain this weekend in London?"
   Expected: Calls internet_search for London weekend forecast
```

### Event Queries
```
4. "What events are happening tomorrow in Tokyo?"
   Expected: Calls internet_search with "Tokyo events March 8 2026"

5. "What should I do this weekend in Paris?"
   Expected: Calls internet_search for Paris weekend activities

6. "Are there any concerts tonight in LA?"
   Expected: Calls internet_search for LA concerts today
```

### Current Information
```
7. "What's the current dollar to yen exchange rate?"
   Expected: Calls internet_search for "USD JPY exchange rate today"

8. "What's happening in the news today?"
   Expected: Calls internet_search for "news today March 7 2026"

9. "What's the latest in AI development?"
   Expected: Calls internet_search for "AI news March 2026"
```

### Combined Queries (Your Original Query)
```
10. "YO! what going on tomorrow around tokyo i want to go out, and have some fun during day how should i dress up, what are the events tomorrow. hit me up with some updates"

   Expected behavior:
   - Recognizes: tomorrow, Tokyo, events, weather (dress up)
   - Calls internet_search 2-3 times:
     1. "Tokyo weather forecast March 8 2026"
     2. "Tokyo events March 8 2026"
     3. "Tokyo activities March 8 2026"
   - Returns: Current weather forecast + real events happening tomorrow
```

## ❌ What NOT To Accept

### Bad Response Pattern (Hallucination):
```
"Based on my knowledge..."
"Typically in Tokyo..."
"Usually events include..."
"The weather is generally..."
```

### Good Response Pattern (Tool Use):
```
"Let me search for current information..."
[Calls internet_search]
"Here's what I found about Tokyo tomorrow:

• **Weather Forecast** - [Real data from search]
  Source: [URL]

• **Events Tomorrow** - [Real events from search]
  Source: [URL]
"
```

## 🔍 How to Verify in LangSmith Studio

1. Open LangSmith Studio trace
2. Look for the tool call nodes in the graph
3. Verify:
   - ✅ Tool name: "internet_search"
   - ✅ Query includes current/specific date
   - ✅ Results include sources/URLs
   - ❌ No tool call = PROBLEM (hallucination)

## 🐛 If Agent Still Doesn't Call Tools

### Check 1: Model Temperature
In `.env`:
```bash
OPENSENTINEL_MODEL_TEMPERATURE=0.7  # Higher encourages tool use
```

### Check 2: Model Supports Tool Calling
Some models don't support tool calling well. Try:
```bash
# Good for tool calling
OPENSENTINEL_MODEL_NAME=meta/llama-3.3-70b-instruct
OPENSENTINEL_MODEL_NAME=nvidia/llama-3.1-nemotron-70b-instruct

# May not call tools reliably
# OPENSENTINEL_MODEL_NAME=qwen/qwen3.5-397b-a17b (sometimes ignores tools)
```

### Check 3: Prompt is Loaded
Restart dev server to reload updated prompts:
```bash
dev.bat
```

### Check 4: Tools Are Registered
Check LangSmith trace shows tools in the agent's tool list.
