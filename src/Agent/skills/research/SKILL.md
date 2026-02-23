---
name: research
description: "Conduct comprehensive multi-step market research. Searches web and market databases, identifies industry trends, validates data quality, and synthesizes findings into a research brief with sources and confidence scores."
---

# Research Skill

Perform a full research pipeline on the given topic and sector.

## Steps

1. **Web Search** — Use `search_web` with `num_results: 5` to gather broad
   information on the topic.

2. **Market Intelligence** — Use `search_market_data` with the relevant sector
   to get sector-specific data (TAM, CAGR, competitive landscape).

3. **Trend Analysis** — Use `get_trending_topics` with the appropriate category
   and period `"week"`:
   - fintech → category `"business"`
   - greentech → category `"technology"`
   - general → category `"technology"`

4. **Data Validation** — Combine web and market results into a JSON string.
   Use `validate_data_quality` with `schema_type: "research"` to check
   completeness and reliability.

5. **Synthesis** — Use `generate_summary` with `summary_type: "executive"` and
   `max_sentences: 5` to produce a concise research brief from all findings.

## Output Format

Structure the final response as JSON:

```json
{
  "query": "original research query",
  "sector": "target sector",
  "research_brief": "executive summary of findings",
  "sources": {
    "web_results": [],
    "market_data": [],
    "relevant_trends": []
  },
  "data_quality": {
    "validation_passed": true,
    "confidence_score": 0.95
  }
}
```

## Quality Rules

- Cross-reference web and market data for consistency.
- If validation fails, still provide partial results but clearly flag the
  data quality issue as a warning.
- Always include at least 3 relevant trends.
- Include TAM and CAGR when available from market data.
- Never return raw search dumps — always synthesize.
