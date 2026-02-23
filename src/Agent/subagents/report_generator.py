"""
Report Generator Subagent  EProfessional report compilation and formatting specialist.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.content_generation import generate_summary, create_recommendation

SYSTEM_PROMPT = """\
You are a professional report writer and document compiler.

Your protocol:
1. Accept raw data, findings, or research outputs
2. Structure information into clear, professional reports
3. Format with executive summaries, findings, analysis, recommendations
4. Tailor tone and depth to audience (executive, technical, general)
5. Include proper sections: summary, methodology, findings, conclusions
6. Add visualizations recommendations where appropriate

Report types you create:
- **Daily Summaries**: Brief updates on tasks, events, decisions
- **Research Reports**: In-depth analysis with citations
- **Financial Reports**: Market analysis, portfolio summaries
- **Project Status**: Progress updates, milestones, blockers
- **Executive Briefings**: High-level strategic overviews

Output format:
- Clear section headers with markdown formatting
- Executive summary (2-3 paragraphs max)
- Bulleted key findings
- Detailed analysis sections
- Actionable recommendations with priorities
- Appendices for supporting data
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[generate_summary, create_recommendation],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_report_generator(task: str) -> str:
    """
    Delegate report compilation and formatting to the report specialist.

    Use for:
    - Creating formatted reports from raw data
    - Compiling research findings into professional documents
    - Generating executive summaries
    - Writing status updates and briefings
    - Formatting technical documentation

    Args:
        task: Report request with raw content (e.g., "Compile research findings into executive report")

    Returns:
        Professionally formatted report
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Report generated  Esee above."
