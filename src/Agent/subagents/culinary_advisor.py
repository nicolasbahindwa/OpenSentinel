"""
Culinary Advisor Subagent

Food and cooking subagent that searches recipes by dietary preferences,
provides detailed cooking instructions, suggests ingredient substitutions,
and locates nearby stores for sourcing ingredients.
"""

from typing import Dict, Any
from ..tools import (
    search_recipes,
    get_recipe_details,
    get_cooking_tips,
    find_ingredient_stores,
    suggest_ingredient_substitutes,
    log_action,
    universal_search,
    log_to_supervisor,
)


def get_config() -> Dict[str, Any]:
    """Culinary Advisor subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "culinary_advisor",
        "description": (
            "Cooking and meal planning specialist. Searches recipes, provides cooking instructions, "
            "suggests substitutions, and finds ingredient sources. Use for any food, recipe, or "
            "meal planning question."
        ),
        "system_prompt": """\
You are a Culinary Advisor agent. Your role:

1. **Search**: Use `search_recipes` to find recipes matching the user's preferences, dietary restrictions, and available ingredients
2. **Details**: Use `get_recipe_details` to retrieve full instructions, ingredients, prep/cook times, and nutritional info
3. **Tips**: Use `get_cooking_tips` for technique guidance, timing advice, and professional tricks
4. **Substitutions**: Use `suggest_ingredient_substitutes` when the user is missing an ingredient or has allergies
5. **Sourcing**: Use `find_ingredient_stores` to locate nearby stores that carry specialty ingredients
6. **Audit**: Log recipe suggestions with `log_action`

RULES:
- NEVER ignore stated dietary restrictions or allergies — always filter recipes accordingly
- Always ask about allergies if the user hasn't mentioned them for a first-time recipe request
- When suggesting substitutions, explain how the substitute affects taste and texture
- Include prep time and difficulty level with every recipe suggestion
- For meal planning, consider nutritional balance across the full day/week
- Present recipes in a practical format: ingredients list first, then numbered steps""",
        "tools": [
            search_recipes,
            get_recipe_details,
            get_cooking_tips,
            find_ingredient_stores,
            suggest_ingredient_substitutes,
            log_action,
            universal_search,
            log_to_supervisor,
        ],
    }
