"""
Financial Analyst Subagent  ELLM-driven financial modeling.

Uses reasoning to decide which calculations to run, how to interpret
results, and what recommendations to make. More adaptive than the
deterministic financial skill pipeline.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

from ..tools import (
    calculate_financial_metrics,
    calculate_statistics,
    validate_data_quality,
    create_recommendation,
    generate_report_summary,
)

SYSTEM_PROMPT = """\
You are a senior financial analyst. Your workflow:

1. Validate all input data using validate_data_quality first.
2. Use calculate_financial_metrics for comprehensive analysis.
3. Use calculate_statistics to analyze underlying datasets.
4. Run sensitivity analysis (best / worst / base case scenarios).
5. Generate investment recommendation (Buy / Hold / Avoid).
6. Use create_recommendation for actionable next steps.
7. Format output as a structured financial report using generate_report_summary.

Always check data quality before calculations. Never proceed with incomplete data.
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        calculate_financial_metrics,
        calculate_statistics,
        validate_data_quality,
        create_recommendation,
        generate_report_summary,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_financial_analyst(task: str) -> str:
    """
    Delegate a financial analysis task to the financial specialist.

    The analyst uses LLM reasoning to decide which metrics to compute,
    how to interpret results, and what investment recommendation to make.
    Best for nuanced financial questions requiring judgment.

    Args:
        task: Natural-language description of the financial analysis task

    Returns:
        The analyst's structured assessment as a string
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Financial analysis complete  Eno summary produced."
