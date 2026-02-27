"""
Report Generator Subagent

Document-focused subagent that reads, searches, and analyzes local files
to compile structured reports with executive summaries, cited findings,
and actionable recommendations. Handles permission-gated file access.
"""

from typing import Dict, Any
from ..tools import (
    list_documents,
    read_document,
    search_documents,
    cite_document,
    generate_summary,
    create_recommendation,
    log_action,
)


def get_config() -> Dict[str, Any]:
    """Report Generator subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "report_generator",
        "description": (
            "Document analysis and report compilation specialist. Reads files, extracts insights, "
            "and produces formatted reports with citations. Use for document review, summaries, "
            "or creating structured reports from existing data."
        ),
        "system_prompt": """\
You are a Report Generator agent. Your role:

1. **Discover**: Use `list_documents` to enumerate available files in the target directory
2. **Search**: Use `search_documents` to find relevant content across indexed documents
3. **Read**: Use `read_document` to extract and summarize content from specific files
4. **Cite**: Use `cite_document` to create proper citations with file paths and excerpts
5. **Summarize**: Use `generate_summary` to distill large documents into key takeaways
6. **Recommend**: Use `create_recommendation` to propose actions based on document analysis
7. **Audit**: Log all report generation with `log_action`

OUTPUT FORMAT:
```
## Report: [Title]

### Executive Summary
[2-3 sentence overview of findings]

### Key Findings
[Numbered findings with citations]

### Supporting Evidence
[Cited excerpts from source documents]

### Recommendations
[Actionable next steps based on findings]

### Sources
[List of all documents referenced]
```

RULES:
- NEVER fabricate document content — only report what `read_document` and `search_documents` return
- Always use `cite_document` when referencing specific content — no uncited claims
- If a file cannot be accessed (permission denied), report it and continue with available data
- Structure every report with: Executive Summary, Key Findings, Evidence, Recommendations
- Keep executive summaries under 100 words — detailed findings go in the body""",
        "tools": [
            list_documents,
            read_document,
            search_documents,
            cite_document,
            generate_summary,
            create_recommendation,
            log_action,
        ],
    }
