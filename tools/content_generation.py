"""
Content Generation Tools — Summary and recommendation generation.
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def generate_summary(content: str, summary_type: str = "brief", max_sentences: int = 3) -> str:
    """
    Generate a concise summary of provided content.

    Args:
        content: The text content to summarize
        summary_type: Type of summary (brief, detailed, executive)
        max_sentences: Maximum sentences in summary (1-10)

    Returns:
        JSON string containing the generated summary
    """
    summary_lengths = {
        "brief": "Key point 1 extracted from content. Key point 2 from the material.",
        "detailed": (
            f"Comprehensive overview: The content primarily discusses {content[:50]}... "
            "Key insights include technical details, market implications, and strategic recommendations."
        ),
        "executive": (
            f"Executive Summary: This comprehensive analysis of {content[:40]}... "
            "provides critical insights for decision-makers. Recommendations included."
        ),
    }

    summary_text = summary_lengths.get(summary_type, summary_lengths["brief"])

    return json.dumps(
        {
            "original_length": len(content),
            "summary": summary_text,
            "summary_type": summary_type,
            "words_in_summary": len(summary_text.split()),
            "compression_ratio": f"{(1 - len(summary_text) / max(len(content), 1)) * 100:.1f}%",
            "generation_timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def create_recommendation(topic: str, context: str = "general", confidence_level: float = 0.85) -> str:
    """
    Generate actionable recommendations on a topic.

    Args:
        topic: The topic to generate recommendations for
        context: Context or use case (general, business, technical, strategic)
        confidence_level: Confidence in recommendations (0.0-1.0)

    Returns:
        JSON string containing recommendations with priorities and actions
    """
    recommendations = {
        "business": [
            {"priority": "high", "action": "Implement market analysis framework", "timeline": "2-4 weeks", "impact": "High"},
            {"priority": "high", "action": "Establish KPI tracking system", "timeline": "1-2 weeks", "impact": "High"},
            {"priority": "medium", "action": "Develop customer engagement strategy", "timeline": "4-6 weeks", "impact": "Medium"},
            {"priority": "low", "action": "Optimize operational efficiency", "timeline": "2-3 months", "impact": "Medium"},
        ],
        "technical": [
            {"priority": "high", "action": "Deploy security patches", "timeline": "Immediate", "impact": "Critical"},
            {"priority": "high", "action": "Implement auto-scaling", "timeline": "1 week", "impact": "High"},
            {"priority": "medium", "action": "Optimize database performance", "timeline": "2-3 weeks", "impact": "Medium"},
            {"priority": "low", "action": "Refactor legacy code", "timeline": "Ongoing", "impact": "Low"},
        ],
        "general": [
            {"priority": "high", "action": f"Prioritize key initiatives for {topic}", "timeline": "1-2 weeks", "impact": "High"},
            {"priority": "medium", "action": f"Document {topic} processes", "timeline": "2-4 weeks", "impact": "Medium"},
            {"priority": "low", "action": f"Review and optimize {topic} workflow", "timeline": "1-2 months", "impact": "Low"},
        ],
    }

    recs = recommendations.get(context, recommendations["general"])

    return json.dumps(
        {
            "topic": topic,
            "context": context,
            "recommendations": recs,
            "overall_confidence": confidence_level,
            "next_review_date": datetime.now().isoformat(),
            "risk_assessment": "Low to Medium",
        },
        indent=2,
    )
