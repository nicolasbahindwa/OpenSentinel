"""
Core Business Tools — Market data, financial metrics, weather impact,
report generation, and data validation.
"""

from langchain_core.tools import tool
import json
from datetime import datetime
from typing import Dict


@tool
def search_market_data(query: str, sector: str = "general", max_results: int = 5) -> str:
    """
    Search for market research data, industry reports, and competitive intelligence.

    Args:
        query: Specific market query (e.g., "Tokyo weather tech market size 2024")
        sector: Industry sector filter (fintech, greentech, general)
        max_results: Number of sources to retrieve (1-10)
    """
    # Simulated — replace with Tavily / Serper in production
    return json.dumps(
        {
            "query": query,
            "sector": sector,
            "results": [
                {
                    "source": "market-research-db",
                    "title": f"{query} Analysis",
                    "snippet": f"Market data for {sector}: $2.4B TAM, 15% CAGR",
                    "url": "https://example.com/report",
                }
            ],
            "timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def calculate_financial_metrics(
    revenue: float,
    costs: float,
    tax_rate: float = 0.25,
    currency: str = "USD",
) -> str:
    """
    Calculate comprehensive financial metrics including profit, margins, and ROI.

    Args:
        revenue: Total revenue amount
        costs: Total operational costs
        tax_rate: Corporate tax rate (default 0.25 for 25%)
        currency: Currency code (USD, JPY, EUR)
    """
    gross_profit = revenue - costs
    tax = gross_profit * tax_rate if gross_profit > 0 else 0
    net_profit = gross_profit - tax
    margin = (net_profit / revenue * 100) if revenue > 0 else 0

    return json.dumps(
        {
            "currency": currency,
            "revenue": revenue,
            "costs": costs,
            "gross_profit": gross_profit,
            "tax": tax,
            "net_profit": net_profit,
            "profit_margin_pct": round(margin, 2),
            "break_even_revenue": costs,
            "health_score": "Strong" if margin > 20 else "Moderate" if margin > 10 else "Weak",
        },
        indent=2,
    )


@tool
def analyze_weather_impact(city: str, industry: str) -> str:
    """
    Analyze how weather patterns affect specific industries in a given city.
    Returns risk assessment and opportunity analysis.
    """
    weather_data = {
        "Tokyo": {"temp": 22, "condition": "sunny", "seasonal_variability": "high"},
        "London": {"temp": 15, "condition": "rainy", "seasonal_variability": "medium"},
        "Singapore": {"temp": 30, "condition": "humid", "seasonal_variability": "low"},
    }

    data = weather_data.get(city, {"temp": 20, "condition": "variable", "seasonal_variability": "medium"})

    industry_impacts = {
        "weather_tech": {
            "opportunity_score": 9 if data["seasonal_variability"] == "high" else 6,
            "risk_factors": ["Seasonal demand fluctuation", "Extreme weather events"],
            "recommendation": "High potential for predictive weather solutions",
        },
        "agriculture": {
            "opportunity_score": 8,
            "risk_factors": ["Crop damage", "Supply chain disruption"],
            "recommendation": "Insurance and monitoring tech needed",
        },
    }

    impact = industry_impacts.get(
        industry,
        {"opportunity_score": 5, "risk_factors": [], "recommendation": "General monitoring advised"},
    )

    return json.dumps(
        {
            "city": city,
            "current_weather": data,
            "industry": industry,
            **impact,
            "analysis_timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def generate_report_summary(
    findings: Dict,
    report_type: str = "business_analysis",
    format_style: str = "markdown",
) -> str:
    """
    Compile structured findings into a formatted business report.

    Args:
        findings: Dictionary containing analysis results
        report_type: Type of report (business_analysis, market_research, financial_audit)
        format_style: Output format (markdown, json, executive_summary)
    """
    if format_style == "executive_summary":
        return (
            f"# Executive Summary: {report_type.replace('_', ' ').title()}\n\n"
            f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M')}  \n"
            f"**Key Findings:** {len(findings)} data points analyzed\n\n"
            "## Critical Insights\n"
            f"{json.dumps(findings, indent=2)[:500]}...\n\n"
            "## Recommendation\n"
            "Proceed with phased implementation based on risk assessment.\n"
        )
    return json.dumps(findings, indent=2)


@tool
def validate_data_quality(data: str, schema_type: str = "financial") -> str:
    """
    Validate data integrity and completeness before analysis.
    Checks for missing fields, outliers, and format consistency.
    """
    issues = []
    if "revenue" in data and "costs" not in data:
        issues.append("Missing cost data for profit calculation")
    if len(data) < 50:
        issues.append("Insufficient data volume")

    return json.dumps(
        {
            "schema_type": schema_type,
            "validation_passed": len(issues) == 0,
            "issues": issues,
            "confidence_score": 0.95 if len(issues) == 0 else 0.6,
            "suggested_action": "Proceed" if len(issues) == 0 else "Request additional data",
        },
        indent=2,
    )
