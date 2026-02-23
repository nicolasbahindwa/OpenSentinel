---
name: document-research
description: "Information gathering and synthesis from local documents and web sources. Provides annotated citations and provenance for all claims."
---

# Document Research Skill

Gather, synthesize, and cite information from multiple sources.

## Steps

### Path A: Local Document Research

1. **Search Local Documents** — Use `search_documents` with:
   - `query`: User's research query
   - `max_results`: 10

   Retrieve relevant files with semantic search

2. **Read Top Documents** — For top 3-5 results:
   - Use `read_document` with:
     - `file_path`: from search results
     - `summary_type`: "key_points"

   Extract relevant information

3. **Cite Sources** — For each piece of information:
   - Use `cite_document` with:
     - `file_path`: source document
     - `excerpt`: quoted text

   Build annotated bibliography

### Path B: Web Research

1. **Search Web** — Use `search_web` with:
   - `query`: User's research query
   - `num_results`: 5-10

   Retrieve relevant web sources

2. **Fetch Web Pages** — For top results:
   - Use `fetch_webpage` with:
     - `url`: from search results

   Retrieve full page content

3. **Summarize Articles** — For each fetched page:
   - Use `summarize_article` with:
     - `url`: source URL

   Extract key points and quotes

4. **Create Bibliography** — Use `create_annotated_bibliography` with:
   - `sources`: all URLs and summaries

   Generate formatted citations

### Path C: Hybrid (Local + Web)

Execute both Path A and Path B, then synthesize findings

## Steps (All Paths)

5. **Cross-Reference Sources** — Compare findings:
   - Flag agreements across sources
   - Note conflicts or contradictions
   - Assess source credibility and recency

6. **Generate Research Summary** — Compile:
   - Executive summary (3-5 key findings)
   - Detailed findings with citations
   - Source quality assessment
   - Confidence scores
   - Gaps in information

## Output Format

Return annotated research summary:

```markdown
## Research Summary: [Query]

### Executive Summary
[3-5 key findings with inline citations]

### Detailed Findings

#### Finding 1: [Topic]
[Detailed explanation]

**Sources:**
- [Document Name](file://path/to/doc.pdf) — "Quoted excerpt" (accessed 2026-02-21)
- [Article Title](https://example.com/article) — Summary of relevant info

**Confidence:** 0.92 (high agreement across sources)

#### Finding 2: [Topic]
...

### Source Quality Assessment
- **Local Documents**: 3 files, last modified 2026-02-20
- **Web Sources**: 4 articles, published 2025-2026
- **Confidence**: Overall 0.85 (good source diversity)

### Information Gaps
- No data found on [specific aspect]
- Conflicting information on [topic] — needs clarification
- Recommend additional search for [specific query]

### Annotated Bibliography
1. **Project Plan** (local file)
   - Path: /docs/project_plan.md
   - Modified: 2026-02-20
   - Relevance: High
   - Key contribution: Project timeline and objectives

2. **Industry Report** (web)
   - URL: https://example.com/report
   - Published: 2025-11-15
   - Relevance: Medium
   - Key contribution: Market size data
```

## Quality Rules

- **Always cite sources**: Every claim traces to a specific document or URL
- **Note publication dates**: Assess recency and relevance
- **Flag conflicts**: When sources disagree, present both views
- **Assess credibility**: Consider source authority and bias
- **Provide provenance**: Full paths, URLs, and access dates
- **Include confidence scores**: Based on source agreement and quality
- **Distinguish facts from inferences**: Clear about what's data vs. interpretation

## Error Handling

- If local search returns no results → Try web search
- If web search fails → Continue with local documents only
- If no sources found → Return "No information found", suggest query refinement
- If source fetch fails → Note in bibliography, continue with available sources
