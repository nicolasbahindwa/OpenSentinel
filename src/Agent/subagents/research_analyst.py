"""
Research Analyst Subagent Configuration

Deep research on finance, tech, science, or politics using multiple sources.
"""

from ..tools import (
    search_news,
    get_financial_data,
    analyze_trend,
    get_market_summary,
    search_research_papers,
    get_political_summary,
    search_web,
    search_internet,
    browse_webpage,
    extract_article_text,
    generate_summary,
    create_recommendation,
)


def get_config():
    """Returns the research analyst subagent configuration."""
    return {
        "name": "research_analyst",
        "description": "Deep research on finance, tech, science, or politics. Use for comprehensive research tasks.",
        "system_prompt": (
            "You are a research analyst. Conduct thorough research using multiple sources, "
            "verify facts, analyze trends, and synthesize findings into structured reports. "
            "Always cite sources and indicate confidence levels."
        ),
        "tools": [
            search_news,
            get_financial_data,
            analyze_trend,
            get_market_summary,
            search_research_papers,
            get_political_summary,
            search_web,
            search_internet,
            browse_webpage,
            extract_article_text,
            generate_summary,
            create_recommendation,
        ],
    }
