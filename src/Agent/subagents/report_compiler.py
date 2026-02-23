"""
Report Compiler Subagent  ELLM-driven report writing.

Uses reasoning to structure, narrate, and polish findings into
executive-ready deliverables.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..tools import (
    generate_report_summary,
    generate_summary,
    create_recommendation,
)

SYSTEM_PROMPT = """\
You are a senior business consultant specialising in report writing.

1. Use generate_summary to create concise summaries of findings.
2. Use generate_report_summary to create structured outputs.
3. Synthesize multiple data sources into a coherent narrative.
4. Include: executive summary, key findings, risk assessment, and recommendations.
5. Use create_recommendation for final action items.
6. Format as professional markdown with tables and headers.
7. Ensure all financial data is properly contextualised.

Create reports suitable for C-suite presentation.
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[generate_report_summary, generate_summary, create_recommendation],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_report_compiler(task: str) -> str:
    """
    Delegate a report-writing task to the report compiler.

    The compiler uses LLM reasoning to structure raw findings into
    polished executive reports. Best when you have data from other
    agents/skills and need a well-written final deliverable.

    Args:
        task: Natural-language description of what to compile, including
              the raw findings data

    Returns:
        The compiled report as a markdown string
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Report compilation complete  Eno output produced."
