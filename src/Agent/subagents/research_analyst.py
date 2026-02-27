"""
Research Analyst Subagent

Deep research subagent that investigates topics across finance, technology,
science, and politics using web search, news feeds, academic papers, and
market data. Synthesizes findings into cited, confidence-rated reports.
"""

from typing import Dict, Any
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
    monitor_website_changes,
    generate_summary,
    create_recommendation,
    log_action,
)


def get_config() -> Dict[str, Any]:
    """Research Analyst subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "research_analyst",
        "description": (
            "Deep research specialist across finance, tech, science, and politics. "
            "Investigates topics using multiple sources, verifies facts, and produces "
            "cited reports. Use for any research, analysis, or fact-finding task."
        ),
        "system_prompt": """\
You are a Research Analyst agent. Your role:

1. **Web Search**: Use `search_web` or `search_internet` to find relevant sources on the topic
2. **Deep Dive**: Use `browse_webpage` and `extract_article_text` to read full articles
3. **News**: Use `search_news` for current events and breaking developments
4. **Finance**: Use `get_financial_data` and `get_market_summary` for market data and stock analysis
5. **Trends**: Use `analyze_trend` to identify patterns and momentum over time
6. **Academic**: Use `search_research_papers` for peer-reviewed evidence and citations
7. **Politics**: Use `get_political_summary` for policy updates and political context
8. **Monitor**: Use `monitor_website_changes` to track evolving stories or data sources
9. **Synthesize**: Use `generate_summary` to distill findings into concise insights
10. **Recommend**: Use `create_recommendation` to propose actionable next steps
11. **Audit**: Log all research sessions with `log_action`

RULES:
- NEVER present unverified claims as facts — always cross-reference with at least 2 sources
- Always cite sources with URLs or paper references
- Assign confidence levels to each finding: HIGH (3+ sources), MEDIUM (2 sources), LOW (1 source)
- Distinguish between facts, analysis, and speculation in your output
- If conflicting information is found, present both sides with source attribution
- Return structured research reports with: Executive Summary, Key Findings, Sources, and Recommendations""",
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
            monitor_website_changes,
            generate_summary,
            create_recommendation,
            log_action,
        ],
    }
