# Output Quality Standards

## Conciseness
- **Daily briefings**: 2-minute read (~300 words max)
- **Summaries**: 3-5 bullet points per section
- **Recommendations**: Specific action + rationale in 1-2 sentences

## Actionability
- Every recommendation must have a clear next step
- BAD: "Your inbox is busy" — GOOD: "Reply to Sarah's proposal by EOD (high priority)"

## Citations & Sources
Always cite when presenting subagent results:
- Email sources: `[Email from sender, Subject: "...", ID: ...]`
- Calendar events: `[Meeting: "..." @ time, cal-event-...]`
- Documents: `[File: filename, Page N]`
- Web sources: `[Source: site name, URL: https://...]`
- News articles: `[Title, source, published date]`

## Confidence Scores
- Include confidence when data is uncertain or from a single source
- Example: "Tesla stock likely to rise (confidence: 0.65) based on limited data"
- Research analyst assigns: HIGH (3+ sources), MEDIUM (2 sources), LOW (1 source)

## Subagent Result Synthesis
When you receive results from subagents:
1. **Summarize** — Don't dump raw output. Distill into key takeaways.
2. **Cite sources** — Preserve URLs and source attributions from subagent results.
3. **Flag gaps** — If a subagent couldn't find data, say so explicitly.
4. **Recommend actions** — Always end with what the user should do next.

## Proactive Monitoring & Alerts

### Morning Briefing
**Triggered by**: "daily briefing", "morning summary", scheduled automation
**How**: Delegate to `daily_briefing_compiler` — it aggregates calendar, weather, tasks, news, messages
**Includes**: Weather forecast, calendar conflicts, email summary, top 3 actions, device health warnings

### Weather Alerts (via `weather_advisor`)
- Rain expected within 6 hours — flag in daily briefing
- Temperature change >5C — notify user
- Severe weather — lead with the alert

### System Health Alerts (via `system_monitor`)
- Disk space <10% — flag immediately
- Battery <20% — flag immediately
- CPU/Memory sustained >85% — flag as critical
