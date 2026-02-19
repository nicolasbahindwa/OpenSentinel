"""
Web Search Tools — Internet information retrieval.
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search the web for information on any topic.

    Args:
        query: The search query (e.g., "latest AI trends 2026")
        num_results: Number of results to return (1-10)

    Returns:
        JSON string containing search results with URLs and snippets
    """
    # Simulated — replace with Tavily / Serper in production
    sample_results = [
        {
            "title": f"Top Article: {query}",
            "url": "https://example.com/article1",
            "snippet": f"Comprehensive information about {query}. Leading source for current information on this topic.",
            "date": "2026-02-15",
        },
        {
            "title": f"In-depth Guide: Understanding {query}",
            "url": "https://example.com/guide",
            "snippet": f"A detailed guide explaining {query} with practical examples and expert insights.",
            "date": "2026-02-10",
        },
        {
            "title": f"Latest News: {query} Updates",
            "url": "https://example.com/news",
            "snippet": f"Breaking news and recent developments in {query} industry.",
            "date": "2026-02-18",
        },
    ]

    return json.dumps(
        {
            "query": query,
            "results": sample_results[:num_results],
            "total_found": 1_250_000,
            "search_time_ms": 342,
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


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
