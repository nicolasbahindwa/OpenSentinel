"""
General Researcher Subagent  EMulti-domain research specialist (finance, politics, IT, news, science).
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.research_analysis import (
    search_news,
    get_financial_data,
    analyze_trend,
    get_market_summary,
    search_research_papers,
    get_political_summary,
)
from ..tools.web_browser import search_internet, browse_webpage, extract_article_text
from ..tools.web_search import search_web
from ..tools.content_generation import generate_summary

SYSTEM_PROMPT = """\
You are an elite multi-domain research analyst covering finance, politics, technology, science, and current events.

Your protocol:
1. Search news and internet for latest information
2. Analyze financial markets and economic trends
3. Monitor political developments and policy changes
4. Track technology and IT sector developments
5. Find and summarize academic research when needed
6. Synthesize findings from multiple sources
7. Provide citations and confidence scores

Research domains:
- **Finance**: Stock data, market trends, economic indicators
- **Politics**: Policy updates, elections, geopolitical events
- **Technology/IT**: Tech news, product launches, industry trends
- **Science**: Research papers, scientific breakthroughs
- **General News**: Current events across all domains

Output format:
- Executive summary with key findings
- Detailed analysis with source citations
- Trend analysis and implications
- Confidence scores for claims
- Related topics for deeper research
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        search_news,
        get_financial_data,
        analyze_trend,
        get_market_summary,
        search_research_papers,
        get_political_summary,
        search_internet,
        browse_webpage,
        extract_article_text,
        search_web,
        generate_summary,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_general_researcher(task: str) -> str:
    """
    Delegate multi-domain research to the general research specialist.

    Use for:
    - Financial market analysis and stock research
    - Political news and policy updates
    - Technology/IT industry research
    - Scientific paper searches
    - Current events and news summaries
    - Cross-domain research topics

    Args:
        task: Research request (e.g., "Latest AI regulations", "Tesla stock analysis", "Climate policy updates")

    Returns:
        Research summary with citations and analysis
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Research complete  Esee findings above."
