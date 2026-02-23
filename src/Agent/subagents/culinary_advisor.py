"""
Culinary Advisor Subagent  ERecipe search, cooking guidance, and meal planning specialist.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.food_recipe import (
    search_recipes,
    get_recipe_details,
    get_cooking_tips,
    find_ingredient_stores,
    suggest_ingredient_substitutes,
)

SYSTEM_PROMPT = """\
You are a professional culinary advisor and cooking instructor.

Your protocol:
1. Help users find recipes based on ingredients, cuisine, or dietary needs
2. Provide detailed cooking instructions with pro tips
3. Suggest where to buy hard-to-find ingredients locally
4. Offer ingredient substitutions for dietary restrictions or availability
5. Give expert cooking techniques and food preparation advice
6. Recommend complementary dishes and meal pairings

Specialties:
- Recipe search and meal planning
- Cooking technique guidance
- Dietary accommodations (vegan, gluten-free, keto, etc.)
- Ingredient sourcing and shopping assistance
- Food substitutions and modifications
- Kitchen tips and professional techniques

Output format:
- Clear recipe recommendations with difficulty ratings
- Step-by-step cooking guidance
- Pro tips for better results
- Shopping lists with store recommendations
- Substitution options when needed
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        search_recipes,
        get_recipe_details,
        get_cooking_tips,
        find_ingredient_stores,
        suggest_ingredient_substitutes,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_culinary_advisor(task: str) -> str:
    """
    Delegate cooking and recipe tasks to the culinary specialist.

    Use for:
    - Finding recipes by ingredient or cuisine
    - Getting detailed cooking instructions
    - Learning cooking techniques and tips
    - Finding where to buy ingredients
    - Getting ingredient substitution advice
    - Meal planning and menu suggestions

    Args:
        task: Culinary request (e.g., "Find pasta recipes", "How to cook chicken perfectly", "Where to buy saffron")

    Returns:
        Recipe recommendations, cooking guidance, or ingredient sourcing info
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Culinary guidance provided  Esee above."
