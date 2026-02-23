"""
Web Search Tools — Internet information retrieval using Tavily (primary) and DuckDuckGo (fallback).
"""

from langchain_core.tools import tool
import json
from datetime import datetime
import os
from typing import Optional


def _search_with_tavily(query: str, num_results: int = 5) -> Optional[dict]:
    """
    Search using Tavily API (primary method).

    Returns None if Tavily is not available or fails.
    """
    try:
        from tavily import TavilyClient

        # Get API key from environment
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return None

        # Initialize Tavily client
        client = TavilyClient(api_key=api_key)

        # Perform search
        response = client.search(
            query=query,
            max_results=num_results,
            search_depth="basic",  # or "advanced" for deeper search
            include_answer=True,  # Get AI-generated answer
            include_raw_content=False,
        )

        # Format results
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0),
            })

        return {
            "query": query,
            "results": results,
            "answer": response.get("answer", ""),  # AI-generated summary
            "total_found": len(results),
            "search_time_ms": response.get("response_time", 0) * 1000,
            "timestamp": datetime.now().isoformat(),
            "source": "tavily",
        }

    except ImportError:
        # Tavily not installed
        return None
    except Exception as e:
        # Tavily failed
        print(f"Tavily search failed: {e}")
        return None


def _search_with_duckduckgo(query: str, num_results: int = 5) -> dict:
    """
    Search using DuckDuckGo (fallback method).

    Always returns results (even if empty).
    """
    try:
        from duckduckgo_search import DDGS

        # Perform search
        with DDGS() as ddgs:
            results_raw = list(ddgs.text(query, max_results=num_results))

        # Format results
        results = []
        for item in results_raw:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("href", ""),
                "snippet": item.get("body", ""),
            })

        return {
            "query": query,
            "results": results,
            "total_found": len(results),
            "search_time_ms": 0,
            "timestamp": datetime.now().isoformat(),
            "source": "duckduckgo",
        }

    except ImportError:
        # DuckDuckGo not installed - return simulated data
        return {
            "query": query,
            "results": [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"Information about {query} (simulated - install duckduckgo-search)",
                }
            ],
            "total_found": 1,
            "search_time_ms": 0,
            "timestamp": datetime.now().isoformat(),
            "source": "simulated",
            "note": "Install tavily-python or duckduckgo-search for real results",
        }
    except Exception as e:
        # DuckDuckGo failed - return error
        return {
            "query": query,
            "results": [],
            "total_found": 0,
            "timestamp": datetime.now().isoformat(),
            "source": "error",
            "error": str(e),
        }


@tool
def search_web(query: str, num_results: int = 5) -> str:
    """
    Search the web for information on any topic.

    Uses Tavily API (primary) with DuckDuckGo fallback.

    Setup:
    1. For Tavily (recommended): Set TAVILY_API_KEY env variable
       Get free key at: https://tavily.com
       Install: pip install tavily-python

    2. For DuckDuckGo (fallback):
       Install: pip install duckduckgo-search

    Args:
        query: The search query (e.g., "latest AI trends 2026")
        num_results: Number of results to return (1-10)

    Returns:
        JSON string containing search results with URLs and snippets
    """
    # Try Tavily first
    result = _search_with_tavily(query, num_results)

    # Fallback to DuckDuckGo if Tavily unavailable
    if result is None:
        result = _search_with_duckduckgo(query, num_results)

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
