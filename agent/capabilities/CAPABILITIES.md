# OpenSentinel Capability Index

This file is the detailed runtime index for capabilities.
Keep startup prompts concise and read this file only when deeper guidance is needed.

## Tools

- `internet_search`
  - Purpose: real-time web retrieval and source-backed facts.
  - Use for: post-cutoff data, news, prices, and date-sensitive questions.

- `weather_lookup`
  - Purpose: current weather and 3-day forecast.
  - Use for: weather planning, travel conditions, and briefing summaries.

## Subagents

- `fact_checker`: verifies claims and returns evidence-backed verdicts.
- `weather_advisor`: interprets weather data into practical recommendations.
- `finance_expert`: market context and risk-aware financial analysis.
- `news_curator`: structured, high-signal news digest.
- `morning_briefing`: consolidated weather + markets + news summary.

## Skills

Skill metadata is discovered from `/skills/`.
Read a specific `SKILL.md` only when the task requires that workflow.

## Middleware

- Guardrails middleware: detects and refuses clearly harmful intent.
- Rate-limit middleware: throttles request volume per identity/time window.
- Routing middleware: applies intent-aware tool ordering and delegation hints.
- Observability middleware: logs route decisions and latency metrics.
- Memory middleware: loads configured memory files once per session.
- Skills middleware: injects skill catalog and enables progressive disclosure.
- Filesystem middleware: provides file operations for `/memories/`, `/workspace/`, and mapped routes.

## Memory

- `/memories/`: persistent memory and preferences.
- `/workspace/`: task workspace.
