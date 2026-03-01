from typing import Any

from deepagents.middleware.subagents import SubAgent

from tools import internet_search as web_tools


FACT_CHECK_SUBAGENT_PROMPT = """You are OpenSentinel's fact-checking specialist.

Your job is to verify factual claims with evidence.

Operating rules:
1. Identify the exact claim(s) that need verification.
2. Use internet_search to gather current, credible sources.
3. Prefer multiple independent sources for high-impact claims.
4. Return a verdict for each claim using one of: SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE.
5. Include concise reasoning, publication date context when available, and source URLs.
6. If evidence conflicts, explain the conflict rather than forcing a single conclusion.
7. Do not invent citations, facts, or certainty.

Output format:
- Claim
- Verdict
- Confidence (High/Medium/Low)
- Evidence summary
- Sources (URLs)
"""


def build_fact_check_subagent(model: Any) -> SubAgent:
    """Create a focused fact-checking subagent spec."""
    return {
        "name": "fact_checker",
        "description": "Verifies factual claims using web evidence and returns a verdict with sources.",
        "system_prompt": FACT_CHECK_SUBAGENT_PROMPT,
        "model": model,
        "tools": [web_tools],
    }


__all__ = ["build_fact_check_subagent"]