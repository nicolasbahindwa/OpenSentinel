"""
Research & Analysis Tools — Finance, politics, IT, news, and multi-domain analysis
"""

from langchain_core.tools import tool
import json
from datetime import datetime

from ._search_engine import search_dual


@tool
def search_news(query: str, category: str = "general", max_results: int = 10) -> str:
    """
    Search latest news articles on any topic.

    Runs both Tavily and DuckDuckGo together with search_type="news"
    for comprehensive news coverage. If one provider fails, the other
    still returns results gracefully.

    Args:
        query: Search query (e.g., "AI developments", "DR Congo news")
        category: News category hint — appended to query for better results
                  (general, business, technology, politics, science, health)
        max_results: Number of results per provider (1-50)

    Returns:
        News articles with titles, URLs, snippets, and provider status
    """
    search_query = f"{query} {category} news" if category != "general" else query
    result = search_dual(search_query, max_results, search_type="news")
    return json.dumps(result, indent=2)


@tool
def get_financial_data(symbol: str, data_type: str = "quote") -> str:
    """
    Get financial market data for stocks, crypto, forex, commodities.

    Args:
        symbol: Ticker symbol (e.g., "AAPL", "BTC-USD", "EUR/USD", "GOLD")
        data_type: Data type (quote, historical, fundamentals, news)

    Returns:
        Financial data with price, change, volume, market cap
    """
    # Simulated — replace with Alpha Vantage, Yahoo Finance API, or CoinGecko
    return json.dumps(
        {
            "symbol": symbol,
            "data_type": data_type,
            "quote": {
                "price": 175.23,
                "change": 2.45,
                "change_percent": 1.42,
                "volume": 52_000_000,
                "market_cap": 2_800_000_000_000,
                "currency": "USD",
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Simulated data — connect to financial API in production",
        },
        indent=2,
    )


@tool
def analyze_trend(topic: str, time_period: str = "7d") -> str:
    """
    Analyze trending interest in a topic over time.

    Args:
        topic: Topic to analyze (e.g., "AI regulation", "climate change")
        time_period: Time period (1d, 7d, 30d, 90d, 1y)

    Returns:
        Trend analysis with interest over time, related topics, sentiment
    """
    # Simulated — replace with Google Trends API or social media analytics
    return json.dumps(
        {
            "topic": topic,
            "time_period": time_period,
            "trend_direction": "increasing",
            "interest_score": 78,
            "change_from_previous_period": "+15%",
            "related_topics": ["AI regulation EU", "AI safety", "tech policy"],
            "sentiment": "mixed",
            "peak_date": "2026-02-18",
            "note": "Simulated trend data — connect to analytics API in production",
        },
        indent=2,
    )


@tool
def get_market_summary(market: str = "global") -> str:
    """
    Get overall market summary and indices.

    Args:
        market: Market region (global, us, europe, asia, crypto)

    Returns:
        Market indices, top movers, sector performance
    """
    # Simulated market data
    return json.dumps(
        {
            "market": market,
            "indices": [
                {"name": "S&P 500", "value": 5234.56, "change": "+0.8%"},
                {"name": "NASDAQ", "value": 16789.23, "change": "+1.2%"},
                {"name": "DOW", "value": 38456.78, "change": "+0.5%"},
            ],
            "top_gainers": [
                {"symbol": "NVDA", "change": "+5.2%"},
                {"symbol": "TSLA", "change": "+3.8%"},
            ],
            "top_losers": [
                {"symbol": "META", "change": "-2.1%"},
                {"symbol": "AMZN", "change": "-1.5%"},
            ],
            "timestamp": datetime.now().isoformat(),
            "note": "Simulated market data — connect to financial API in production",
        },
        indent=2,
    )


@tool
def search_research_papers(query: str, field: str = "all", max_results: int = 10) -> str:
    """
    Search academic and research papers.

    Args:
        query: Search query
        field: Research field (all, cs, biology, physics, economics, etc.)
        max_results: Number of papers to return

    Returns:
        Research papers with titles, authors, abstracts, citations
    """
    # Simulated — replace with arXiv API, Google Scholar, Semantic Scholar
    sample_papers = [
        {
            "title": f"Recent Advances in {query}",
            "authors": ["Smith, J.", "Johnson, A."],
            "published": "2026-01-15",
            "abstract": f"This paper presents {query}...",
            "url": "https://arxiv.org/abs/2601.12345",
            "citations": 12,
            "field": field,
        }
    ]

    return json.dumps(
        {
            "query": query,
            "field": field,
            "papers": sample_papers[:max_results],
            "total_found": len(sample_papers),
            "note": "Simulated papers — connect to arXiv/Scholar API in production",
        },
        indent=2,
    )


@tool
def get_political_summary(country: str = "global") -> str:
    """
    Get political news and updates for a country or globally.

    Args:
        country: Country code or "global" (us, uk, eu, jp, global)

    Returns:
        Political news summary, key developments, upcoming events
    """
    # Simulated political summary
    return json.dumps(
        {
            "country": country,
            "key_developments": [
                "Legislative session on climate policy scheduled for next week",
                "Trade negotiations with partners ongoing",
            ],
            "upcoming_events": [
                {"event": "Policy debate", "date": "2026-02-25"},
            ],
            "sentiment": "stable",
            "sources": ["Reuters", "AP News"],
            "last_updated": datetime.now().isoformat(),
            "note": "Simulated political data — connect to news APIs in production",
        },
        indent=2,
    )
