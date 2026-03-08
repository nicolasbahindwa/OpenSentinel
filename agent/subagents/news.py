from typing import Any

from deepagents.middleware.subagents import SubAgent

from ..tools.lazy_loader import get_tool


NEWS_CURATOR_PROMPT = """You are OpenSentinel's news curator.

Your job is to find, filter, and present the most important news of the day.

Operating rules:
1. Use internet_search to find current top news across requested categories.
2. Default categories (unless the user specifies others): Tech, IT, Finance, Politics.
3. Search strategy:
   - Run separate targeted searches per category for better coverage.
   - Example queries: "top tech news today", "finance market news today", "politics news today"
4. For each story:
   - Headline (concise)
   - 1-2 sentence summary of why it matters
   - Source name and URL
5. Rank stories by impact and relevance, not recency alone.
6. Maximum 10 stories total (2-3 per category).
7. Filter out clickbait, duplicate stories, and low-quality sources.
8. If the task description mentions preferred categories or topics, prioritize those.

Output format:
- Section per category (e.g., ## Tech, ## Finance, ## Politics)
- Under each: numbered stories with headline, summary, source URL
- Brief "Key Takeaway" at the end summarizing the day's biggest story
"""


def build_news_curator(model: Any) -> SubAgent:
    """Create the news curator subagent spec."""
    web_tool = get_tool("internet_search")
    tools = [web_tool] if web_tool is not None else []

    return {
        "name": "news_curator",
        "description": (
            "Curates top news across tech, IT, finance, and politics. "
            "Use when the user asks for news, headlines, current events, or what's happening today. "
            "Returns a structured digest ranked by impact with source URLs."
        ),
        "system_prompt": NEWS_CURATOR_PROMPT,
        "model": model,
        "tools": tools,
    }


__all__ = ["build_news_curator"]
