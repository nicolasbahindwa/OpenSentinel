"""
Research Assistant Subagent  EInformation gathering and synthesis specialist.

Refocused for personal productivity: web research, document summarization,
literature review with proper citations and provenance.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.web_search import search_web
from ..tools.documents import (
    list_documents,
    read_document,
    search_documents,
    cite_document,
)
from ..tools.content_generation import generate_summary

SYSTEM_PROMPT = """\
You are a research librarian and information specialist.

Your protocol:
1. Gather information from web and local documents
2. Evaluate source credibility and recency
3. Summarize findings with clear citations
4. Create annotated bibliographies for research tasks
5. Provide provenance for all claims
6. Flag conflicting information across sources

Quality standards:
- Cite all sources with URLs or file paths
- Note publication dates and assess recency
- Cross-reference claims across sources
- Distinguish facts from opinions
- Provide confidence scores for findings
- Structure output for user's domain (education/business/research)

Output format:
- Executive summary with key findings
- Detailed findings with inline citations
- Annotated bibliography with source quality assessment
- Information gaps and recommendations for further research
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        search_web,
        list_documents,
        read_document,
        search_documents,
        cite_document,
        generate_summary,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_research_assistant(task: str) -> str:
    """
    Delegate research tasks to the information gathering specialist.

    Use for:
    - Web research on specific topics
    - Document summarization and synthesis
    - Literature review with citations
    - Finding and organizing information across sources

    Args:
        task: Natural-language description of the research task

    Returns:
        Research summary with annotated sources and citations
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})

    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content

    return "Research complete  Esee findings above."
