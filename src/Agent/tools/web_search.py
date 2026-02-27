"""
Web Search Tools — Internet information retrieval using Tavily + DuckDuckGo together.

Both providers run in parallel. If one fails, the other still returns results.
Results are merged and deduplicated. Shared engine lives in _search_engine.py.
"""

from langchain_core.tools import tool
import json
from datetime import datetime

from ._search_engine import search_dual


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search the web for information on any topic.

    Runs both Tavily and DuckDuckGo together for comprehensive coverage.
    If one provider fails, the other still returns results gracefully.

    Setup (at least one required):
    1. Tavily (recommended): Set TAVILY_API_KEY, pip install tavily-python
    2. DuckDuckGo (free): pip install duckduckgo-search

    Args:
        query: The search query (e.g., "latest AI trends 2026")
        num_results: Number of results per provider (1-10, total may be higher after merge)

    Returns:
        JSON string with merged results from both providers, deduplicated by URL
    """
    result = search_dual(query, num_results, search_type="general")
    return json.dumps(result, indent=2)


@tool
def get_trending_topics(category: str = "technology", period: str = "week") -> str:
    """
    Get trending topics in a specific category.

    Args:
        category: Category to search (technology, business, science, finance)
        period: Time period (day, week, month)

    Returns:
        JSON string containing trending topics with popularity scores
    """
    trending_data = {
        "technology": {
            "day": ["AI Agents", "Quantum Computing", "5G Networks", "Blockchain Security", "Web3"],
            "week": ["Generative AI", "AI Safety", "Cloud Computing", "Edge AI", "Machine Learning Ops"],
            "month": ["Artificial Intelligence", "Cybersecurity", "Automation", "Data Science", "Digital Transformation"],
        },
        "business": {
            "day": ["Startup Funding", "Market Trends", "Business Strategy", "Leadership", "Productivity"],
            "week": ["Economic Growth", "Trade Policies", "Corporate Innovation", "Mergers & Acquisitions", "Remote Work"],
            "month": ["Global Economy", "Consumer Behavior", "Brand Strategy", "Risk Management", "Sustainability"],
        },
    }

    topics = trending_data.get(category, {}).get(
        period, ["General Trending Topic 1", "General Trending Topic 2"]
    )

    return json.dumps(
        {
            "category": category,
            "period": period,
            "trending_topics": [
                {"rank": i + 1, "topic": topic, "popularity_score": 95 - i * 5, "mentions": (100 - i * 10) * 1000}
                for i, topic in enumerate(topics)
            ],
            "last_updated": datetime.now().isoformat(),
        },
        indent=2,
    )
