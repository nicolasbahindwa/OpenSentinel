"""
Data Analysis Tools — Statistical analysis and dataset inspection.
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def analyze_dataset(data_type: str, dataset_size: int) -> str:
    """
    Perform comprehensive analysis on a dataset.

    Args:
        data_type: Type of data (sales, customer, product, performance)
        dataset_size: Number of records in dataset

    Returns:
        JSON string containing analysis results and insights
    """
    analysis_results = {
        "sales": {
            "total_revenue": 2_500_000,
            "average_transaction": 1_250,
            "top_products": ["Product A", "Product B", "Product C"],
            "growth_rate": "23.5%",
        },
        "customer": {
            "total_customers": 5_000,
            "retention_rate": "78.5%",
            "churn_rate": "21.5%",
            "avg_lifetime_value": 3_500,
        },
        "product": {
            "total_products": 250,
            "active_products": 180,
            "discontinued": 70,
            "success_rate": "72%",
        },
        "performance": {
            "uptime": "99.95%",
            "avg_response_time_ms": 145,
            "error_rate": "0.05%",
            "user_satisfaction": "94.5%",
        },
    }

    results = analysis_results.get(data_type, {})

    return json.dumps(
        {
            "data_type": data_type,
            "dataset_size": dataset_size,
            "analysis": results,
            "quality_score": 0.945,
            "confidence_level": "95.2%",
            "analysis_timestamp": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def calculate_statistics(values: str, stat_type: str = "comprehensive") -> str:
    """
    Calculate statistical measures for a dataset.

    Args:
        values: Comma-separated numerical values
        stat_type: Type of statistics (descriptive, correlation, trend, comprehensive)

    Returns:
        JSON string containing calculated statistics
    """
    try:
        nums = [float(x.strip()) for x in values.split(",")]

        mean = sum(nums) / len(nums)
        sorted_nums = sorted(nums)
        median = (
            sorted_nums[len(nums) // 2]
            if len(nums) % 2 == 1
            else (sorted_nums[len(nums) // 2 - 1] + sorted_nums[len(nums) // 2]) / 2
        )
        variance = sum((x - mean) ** 2 for x in nums) / len(nums)
        std_dev = variance**0.5

        stats = {
            "count": len(nums),
            "mean": round(mean, 2),
            "median": round(median, 2),
            "std_deviation": round(std_dev, 2),
            "variance": round(variance, 2),
            "min": min(nums),
            "max": max(nums),
            "range": max(nums) - min(nums),
            "sum": sum(nums),
        }

        if stat_type == "comprehensive":
            stats["percentile_25"] = sorted_nums[len(nums) // 4]
            stats["percentile_75"] = sorted_nums[3 * len(nums) // 4]
            stats["skewness"] = "positive" if mean > median else "negative"
            stats["data_quality"] = "Good"

        return json.dumps(stats, indent=2)

    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "message": "Failed to calculate statistics",
                "suggestion": "Ensure values are comma-separated numbers",
            },
            indent=2,
        )
