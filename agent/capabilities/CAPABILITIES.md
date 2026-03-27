# OpenSentinel Capability Index

This file is the detailed runtime index for capabilities.
Keep startup prompts concise and read this file only when deeper guidance is needed.

## Tools

- `tool_search`
  - Purpose: discover available tools and subagents from the registry.
  - Use for: mapping user requests to capabilities when unsure.

- `internet_search`
  - Purpose: real-time web retrieval and source-backed facts.
  - Use for: post-cutoff data, news, prices, and date-sensitive questions.

- `weather_lookup`
  - Purpose: current weather and 3-day forecast.
  - Use for: weather planning, travel conditions, and briefing summaries.

- `file_browser`
  - Purpose: browse and manage local files.
  - Use for: listing, reading, searching, creating, editing, and moving files.
  - Limits: restricted to Desktop, Documents, and Downloads.

- `system_status`
  - Purpose: read-only system health checks.
  - Use for: CPU, memory, disk, network, process, and OS info.

- `web_browser`
  - Purpose: web browsing, DOM snapshots with element refs, and browser automation.
  - Use for: JS-heavy pages, multi-step interactions, and screenshots.

## Subagents

- `fact_checker`: verifies claims and returns evidence-backed verdicts.
- `weather_advisor`: interprets weather data into practical recommendations.
- `finance_expert`: market context and risk-aware financial analysis.
- `news_curator`: structured, high-signal news digest.
- `morning_briefing`: consolidated weather + markets + news summary.

## Skills

Skill metadata is discovered from `/skills/`.
Read a specific `SKILL.md` only when the task requires that workflow.
`mood-skill` is also used as the policy reference for always-on response-style middleware.

## Middleware

- Guardrails middleware: detects and refuses clearly harmful intent.
- Rate-limit middleware: throttles request volume per identity/time window.
- Routing middleware: applies intent-aware tool ordering and delegation hints.
- Observability middleware: logs route decisions and latency metrics.
- Response-style middleware: injects a concise per-turn tone and language hint based on the latest user message.
- Memory middleware: loads configured memory files once per session.
- Skills middleware: injects skill catalog and enables progressive disclosure.
- Filesystem middleware: provides file operations within tool-enforced allowlists.
- Follow-up middleware: extracts or synthesizes concise next-question suggestions for the UI.

## Memory

- `/memories/`: persistent memory and preferences.
