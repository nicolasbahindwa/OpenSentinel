"""
Web Browsing Tools — Advanced internet search and content extraction
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def browse_webpage(url: str, extract_type: str = "full") -> str:
    """
    Fetch and extract content from a specific webpage.

    Args:
        url: Full URL to browse (e.g., "https://example.com/article")
        extract_type: What to extract (full, summary, main_content, links, images)

    Returns:
        Webpage content extracted and formatted
    """
    # Simulated — replace with requests + BeautifulSoup or Playwright
    return json.dumps(
        {
            "url": url,
            "extract_type": extract_type,
            "title": "Example Article Title",
            "author": "John Doe",
            "published_date": "2026-02-15",
            "main_content": "This is the main article content extracted from the page...",
            "word_count": 850,
            "reading_time_minutes": 4,
            "images": ["https://example.com/image1.jpg"],
            "links": ["https://example.com/related1", "https://example.com/related2"],
            "fetched_at": datetime.now().isoformat(),
            "note": "Simulated webpage fetch — implement with requests/BeautifulSoup in production",
        },
        indent=2,
    )


@tool
def search_internet(query: str, search_type: str = "general", max_results: int = 10) -> str:
    """
    Advanced internet search with filtering options.

    Uses Tavily API (primary) with DuckDuckGo fallback.

    Setup:
    1. For Tavily (recommended): Set TAVILY_API_KEY env variable
    2. For DuckDuckGo (fallback): pip install duckduckgo-search

    Args:
        query: Search query
        search_type: Type of search (general, news, images, videos, academic, shopping)
        max_results: Number of results to return (1-50)

    Returns:
        Search results with URLs, titles, snippets, dates
    """
    import os
    from typing import Optional

    def _tavily_search(q: str, max_res: int, s_type: str) -> Optional[dict]:
        try:
            from tavily import TavilyClient
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                return None

            client = TavilyClient(api_key=api_key)

            # Map search types to Tavily parameters
            search_params = {
                "query": q,
                "max_results": max_res,
                "search_depth": "advanced" if s_type == "academic" else "basic",
                "include_answer": True,
            }

            # For news, add topic filter
            if s_type == "news":
                search_params["topic"] = "news"

            response = client.search(**search_params)

            results = []
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "domain": item.get("url", "").split("/")[2] if "/" in item.get("url", "") else "",
                    "score": item.get("score", 0),
                })

            return {
                "query": q,
                "search_type": s_type,
                "results": results,
                "answer": response.get("answer", ""),
                "total_found": len(results),
                "source": "tavily",
            }
        except:
            return None

    def _duckduckgo_search(q: str, max_res: int, s_type: str) -> dict:
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                if s_type == "news":
                    results_raw = list(ddgs.news(q, max_results=max_res))
                elif s_type == "images":
                    results_raw = list(ddgs.images(q, max_results=max_res))
                elif s_type == "videos":
                    results_raw = list(ddgs.videos(q, max_results=max_res))
                else:
                    results_raw = list(ddgs.text(q, max_results=max_res))

            results = []
            for item in results_raw:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href") or item.get("url", ""),
                    "snippet": item.get("body") or item.get("description", ""),
                    "domain": (item.get("href") or item.get("url", "")).split("/")[2] if "/" in str(item.get("href") or item.get("url", "")) else "",
                    "published": item.get("date", ""),
                })

            return {
                "query": q,
                "search_type": s_type,
                "results": results,
                "total_found": len(results),
                "source": "duckduckgo",
            }
        except:
            return {
                "query": q,
                "search_type": s_type,
                "results": [{
                    "title": f"Search result for: {q}",
                    "url": "https://example.com",
                    "snippet": f"Information about {q} (install duckduckgo-search or set TAVILY_API_KEY)",
                    "domain": "example.com",
                }],
                "total_found": 1,
                "source": "simulated",
            }

    # Try Tavily first, fallback to DuckDuckGo
    result = _tavily_search(query, max_results, search_type)
    if result is None:
        result = _duckduckgo_search(query, max_results, search_type)

    result["search_time_ms"] = 0
    result["timestamp"] = datetime.now().isoformat()

    return json.dumps(result, indent=2)


@tool
def extract_article_text(url: str) -> str:
    """
    Extract clean article text from news/blog URLs (removes ads, navigation).

    Args:
        url: Article URL

    Returns:
        Clean article text with metadata
    """
    # Simulated — replace with newspaper3k, readability-lxml, or trafilatura
    return json.dumps(
        {
            "url": url,
            "title": "Example Article Title",
            "author": "Jane Smith",
            "published_date": "2026-02-18",
            "text": "Clean article text extracted without ads or navigation...",
            "word_count": 1250,
            "reading_time_minutes": 6,
            "language": "en",
            "top_image": "https://example.com/header.jpg",
            "note": "Simulated extraction — use article extraction library in production",
        },
        indent=2,
    )


@tool
def monitor_website_changes(url: str, check_interval_hours: int = 24) -> str:
    """
    Monitor a webpage for content changes.

    Args:
        url: URL to monitor
        check_interval_hours: How often to check (default 24 hours)

    Returns:
        Change detection results
    """
    # Simulated — implement with web scraping + diff algorithm
    return json.dumps(
        {
            "url": url,
            "check_interval_hours": check_interval_hours,
            "last_checked": datetime.now().isoformat(),
            "changes_detected": False,
            "change_summary": "No changes since last check",
            "next_check": (datetime.now()).isoformat(),
            "note": "Simulated monitoring — implement with scheduled scraping in production",
        },
        indent=2,
    )
