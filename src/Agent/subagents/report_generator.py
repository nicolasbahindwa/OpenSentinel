"""
Report Generator Subagent Configuration

Compiles data into formatted reports with summaries and recommendations.
"""

from ..tools import (
    list_documents,
    read_document,
    search_documents,
    cite_document,
    generate_summary,
    create_recommendation,
)


def get_config():
    """Returns the report generator subagent configuration."""
    return {
        "name": "report_generator",
        "description": "Compiles data into formatted reports. Use for creating summaries and briefings.",
        "system_prompt": (
            "You are a report writing specialist. Compile information into well-structured, "
            "readable reports with executive summaries, key findings, and actionable recommendations. "
            "Use markdown formatting for clarity."
        ),
        "tools": [
            list_documents,
            read_document,
            search_documents,
            cite_document,
            generate_summary,
            create_recommendation,
        ],
    }
