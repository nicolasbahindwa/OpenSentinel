"""
Tools module — Atomic, stateless functions.

Each tool performs a single operation and returns structured JSON.
Tools are the lowest-level building blocks; they are composed by
skills (deterministic pipelines) and subagents (LLM-driven specialists).
"""

from .web_search import search_web, get_trending_topics
from .data_analysis import analyze_dataset, calculate_statistics
from .content_generation import generate_summary, create_recommendation
from .email import compose_email, classify_email
from .core import (
    search_market_data,
    calculate_financial_metrics,
    analyze_weather_impact,
    generate_report_summary,
    validate_data_quality,
)

__all__ = [
    # Web & market
    "search_web",
    "get_trending_topics",
    "search_market_data",
    # Analysis
    "analyze_dataset",
    "calculate_statistics",
    "calculate_financial_metrics",
    "analyze_weather_impact",
    # Content & reporting
    "generate_summary",
    "create_recommendation",
    "generate_report_summary",
    # Email
    "compose_email",
    "classify_email",
    # Validation
    "validate_data_quality",
]
