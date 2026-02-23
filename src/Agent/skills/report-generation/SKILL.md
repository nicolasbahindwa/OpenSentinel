---
name: report-generation
description: "Compile raw analysis findings into a polished executive report. Generates executive and detailed summaries, creates strategic recommendations, and formats the output as a professional C-suite-ready deliverable."
---

# Report Generation Skill

Compile multiple data sources into a polished, executive-ready report.

## Steps

1. **Parse Input** — Parse the provided findings. If the input is a JSON
   string, parse it into structured data. If it is plain text, treat it as
   raw content.

2. **Executive Summary** — Use `generate_summary` with
   `summary_type: "executive"` and `max_sentences: 3` to create a concise
   top-line summary.

3. **Detailed Summary** — Use `generate_summary` with
   `summary_type: "detailed"` and `max_sentences: 8` to create the body
   analysis section.

4. **Recommendations** — Use `create_recommendation` with:
   - topic: the report type, title-cased
   - context: map the report type to a context:
     - `business_analysis` → `"business"`
     - `market_research` → `"general"`
     - `financial_audit` → `"business"`
     - `technical_review` → `"technical"`
   - confidence_level: `0.85`

5. **Compile** — Use `generate_report_summary` with
   `format_style: "executive_summary"` to produce the final formatted report
   combining executive summary, detailed analysis, and recommendations.

## Output Format

Deliver a professional markdown report with:

- Title and generation date
- Executive Summary (3 sentences max)
- Key Findings (with quantified data points)
- Detailed Analysis
- Recommendations (prioritised with impact ratings and timelines)
- Risk Assessment

## Quality Rules

- Keep the executive summary under 3 sentences.
- Ensure every recommendation is actionable with a specific timeline.
- Include confidence scores where available.
- Format for C-suite readability — no jargon, clear structure, tables where
  appropriate.
