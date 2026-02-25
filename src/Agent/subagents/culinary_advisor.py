"""
Culinary Advisor Subagent Configuration

Recipe suggestions, cooking tips, and ingredient sourcing.
"""

from ..tools import (
    search_recipes,
    get_recipe_details,
    get_cooking_tips,
    find_ingredient_stores,
    suggest_ingredient_substitutes,
)


def get_config():
    """Returns the culinary advisor subagent configuration."""
    return {
        "name": "culinary_advisor",
        "description": "Recipe suggestions, cooking tips, and ingredient sourcing. Use for meal planning.",
        "system_prompt": (
            "You are a culinary assistant. Suggest recipes based on preferences/dietary restrictions, "
            "provide cooking tips, find ingredient sources, and suggest substitutions. "
            "Consider nutrition, prep time, and skill level."
        ),
        "tools": [
            search_recipes,
            get_recipe_details,
            get_cooking_tips,
            find_ingredient_stores,
            suggest_ingredient_substitutes,
        ],
    }
