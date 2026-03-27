# Subagents

Specialized subagents are available for delegation when deeper domain reasoning is needed.

## Available

- `fact_checker`: claim verification with evidence.
- `weather_advisor`: weather interpretation and practical recommendations.
- `finance_expert`: market context and finance-oriented analysis.
- `news_curator`: structured current-events digest.
- `morning_briefing`: combined weather, markets, and news summary.

## How to Use Subagents

**Use the `task` tool with these parameters:**
- `subagent_type` (required): The subagent name (e.g., "news_curator", "morning_briefing")
- `description` (required): Detailed task description for the subagent

**Example:**
```python
task(subagent_type="news_curator", description="Get top tech and AI news from today")
task(subagent_type="morning_briefing", description="Provide daily briefing for Tokyo, include weather, market indices, and tech news")
```

## Delegation Policy (Following LangChain Best Practices)

**Use direct tools for straightforward operations:**
- Weather lookups → `weather_lookup` tool
- Currency rates → `currency` tool
- Web searches → `internet_search` tool
- Simple fact lookups → Direct tools

**Use subagent delegation ONLY for context isolation:**
- Deep research requiring isolation → Delegate to specialized subagent
- Complex analysis (market trends, detailed planning) → Delegate
- Explicit research requests ("investigate", "analyze", "research") → Delegate

**For multi-part queries** (e.g., "weather + currency + transport + advice"):
- Use direct tools sequentially
- Make organized tool calls: weather_lookup → currency → internet_search
- Synthesize all results into a comprehensive answer
- Do NOT delegate unless tools are unavailable

## Example: Multi-Part Query

**User:** "I'm going to Tokyo tomorrow. Tell me weather, USD/EUR rates, transport costs from Chiba to Tokyo, and how to dress."

**Correct Approach (Direct Tools):**
1. Call `weather_lookup(location="Tokyo")`
2. Call `currency(from_currency="USD", to_currency="JPY")`
3. Call `currency(from_currency="EUR", to_currency="JPY")`
4. Call `internet_search(query="Chiba Kashiwa to Tokyo station transport cost")`
5. Synthesize: "Based on the weather (14°C, light rain), dress in layers with a light jacket. USD rate is X, EUR rate is Y. Transport costs ¥550-800 and takes 37 minutes."

**When NOT to use subagents:**
- You have the tools you need → Use them directly
- Simple information gathering → Direct tools are faster
