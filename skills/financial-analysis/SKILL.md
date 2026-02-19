---
name: financial-analysis
description: "Run a complete financial assessment pipeline. Validates input data, calculates profit metrics, performs statistical analysis on historical data, models optimistic/base/pessimistic scenarios, and generates prioritised recommendations with an executive report."
---

# Financial Analysis Skill

Perform a complete financial assessment on the provided data.

## Steps

1. **Validate Input** — Use `validate_data_quality` with
   `schema_type: "financial"` to verify data completeness.
   **If validation fails, stop and report what data is missing.**

2. **Calculate Metrics** — Use `calculate_financial_metrics` with the provided
   revenue, costs, tax_rate, and currency to get gross profit, net profit,
   margins, break-even point, and health score.

3. **Statistical Analysis** (conditional) — If historical data values are
   provided, use `calculate_statistics` with `stat_type: "comprehensive"` to
   analyse trends, variance, and percentiles. Skip this step if no historical
   data is available.

4. **Scenario Modeling** — Run `calculate_financial_metrics` three times with
   the same costs and tax_rate but adjusted revenue:
   - **Optimistic**: revenue × 1.20 (20% growth)
   - **Base**: revenue × 1.00 (current)
   - **Pessimistic**: revenue × 0.80 (20% decline)

5. **Recommendations** — Use `create_recommendation` with:
   - topic: `"Financial strategy ({currency})"`
   - context: `"business"` if health_score is Strong, otherwise `"technical"`
   - confidence_level: `0.85`

6. **Compile Report** — Use `generate_report_summary` with
   `report_type: "financial_audit"` and `format_style: "executive_summary"`
   to produce the final deliverable.

## Output Format

Present the assessment as a structured report including:

- Base metrics (revenue, costs, margins, health score)
- Statistical analysis (if historical data provided)
- Three-scenario comparison (optimistic / base / pessimistic)
- Prioritised recommendations with timelines
- Overall data quality confidence score

## Quality Rules

- **Never proceed with calculations if validation fails.** Return an error
  report with the specific issues and a suggestion to provide complete data.
- Always model all three scenarios, even when the base case looks healthy.
- Flag any metrics that indicate financial distress (profit margin < 5%).
- Present currency-appropriate formatting.
