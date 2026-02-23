"""
Food & Recipe Tools — Recipe search, cooking tips, ingredient sourcing
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def search_recipes(query: str, dietary_restrictions: str = "", max_results: int = 10) -> str:
    """
    Search for recipes by ingredient, dish name, or cuisine type.

    Args:
        query: Search query (e.g., "chicken pasta", "chocolate cake", "vegan soup")
        dietary_restrictions: Dietary filters (vegetarian, vegan, gluten-free, keto, etc.)
        max_results: Number of recipes to return (1-50)

    Returns:
        Recipes with ingredients, instructions, cook time, difficulty
    """
    # Simulated — replace with Spoonacular API, Edamam API, or Recipe Puppy
    sample_recipes = [
        {
            "id": "recipe_001",
            "title": "Classic Chicken Pasta",
            "cuisine": "Italian",
            "difficulty": "Medium",
            "cook_time_minutes": 30,
            "servings": 4,
            "ingredients": [
                "400g pasta",
                "300g chicken breast",
                "2 cloves garlic",
                "200ml cream",
                "Parmesan cheese",
                "Salt, pepper, olive oil",
            ],
            "instructions_summary": "Cook pasta. Sauté chicken and garlic. Mix with cream and cheese.",
            "calories_per_serving": 520,
            "image_url": "https://example.com/recipe1.jpg",
            "source": "RecipeDB",
        },
        {
            "id": "recipe_002",
            "title": "Creamy Mushroom Pasta",
            "cuisine": "Italian",
            "difficulty": "Easy",
            "cook_time_minutes": 20,
            "servings": 4,
            "ingredients": [
                "400g pasta",
                "300g mushrooms",
                "2 cloves garlic",
                "200ml cream",
                "Parmesan cheese",
            ],
            "instructions_summary": "Cook pasta. Sauté mushrooms. Mix with cream.",
            "calories_per_serving": 420,
            "image_url": "https://example.com/recipe2.jpg",
            "source": "RecipeDB",
        },
    ]

    # Filter by dietary restrictions if provided
    filtered_recipes = sample_recipes[:max_results]

    return json.dumps(
        {
            "query": query,
            "dietary_restrictions": dietary_restrictions or "none",
            "recipes": filtered_recipes,
            "total_found": len(filtered_recipes),
            "note": "Simulated recipes — connect to Spoonacular API in production",
        },
        indent=2,
    )


@tool
def get_recipe_details(recipe_id: str) -> str:
    """
    Get detailed cooking instructions for a specific recipe.

    Args:
        recipe_id: Recipe identifier from search results

    Returns:
        Full recipe with step-by-step instructions, tips, nutritional info
    """
    # Simulated detailed recipe
    return json.dumps(
        {
            "recipe_id": recipe_id,
            "title": "Classic Chicken Pasta",
            "prep_time": 10,
            "cook_time": 30,
            "total_time": 40,
            "servings": 4,
            "difficulty": "Medium",
            "ingredients": [
                {"item": "Pasta", "amount": "400g"},
                {"item": "Chicken breast", "amount": "300g"},
                {"item": "Garlic", "amount": "2 cloves"},
                {"item": "Heavy cream", "amount": "200ml"},
                {"item": "Parmesan cheese", "amount": "50g, grated"},
                {"item": "Olive oil", "amount": "2 tbsp"},
                {"item": "Salt and pepper", "amount": "to taste"},
            ],
            "instructions": [
                {"step": 1, "text": "Bring large pot of salted water to boil. Cook pasta according to package directions."},
                {"step": 2, "text": "Cut chicken into bite-sized pieces. Season with salt and pepper."},
                {"step": 3, "text": "Heat olive oil in large pan. Cook chicken until golden, about 6-8 minutes."},
                {"step": 4, "text": "Add minced garlic, cook for 1 minute until fragrant."},
                {"step": 5, "text": "Pour in cream, bring to simmer. Add parmesan, stir until melted."},
                {"step": 6, "text": "Drain pasta, add to sauce. Toss to coat. Serve immediately."},
            ],
            "cooking_tips": [
                "Don't overcook the pasta — al dente is best",
                "Reserve 1 cup pasta water to adjust sauce consistency",
                "Use freshly grated Parmesan for best flavor",
            ],
            "nutrition": {
                "calories": 520,
                "protein_g": 28,
                "carbs_g": 55,
                "fat_g": 18,
            },
            "note": "Simulated recipe details — connect to recipe API in production",
        },
        indent=2,
    )


@tool
def get_cooking_tips(ingredient_or_technique: str) -> str:
    """
    Get professional cooking tips for ingredients or techniques.

    Args:
        ingredient_or_technique: Ingredient name or cooking technique (e.g., "chicken", "pasta", "sautéing")

    Returns:
        Expert cooking tips and techniques
    """
    # Simulated cooking tips
    tips_db = {
        "chicken": [
            "Pat chicken dry before cooking for better browning",
            "Use meat thermometer: 165°F/74°C for safe internal temp",
            "Let rest 5 minutes after cooking to retain juices",
            "Brine for extra moisture (1 hour in saltwater)",
        ],
        "pasta": [
            "Use 4-6 quarts water per pound of pasta",
            "Salt the water generously (should taste like seawater)",
            "Stir within first 2 minutes to prevent sticking",
            "Reserve pasta water before draining — great for adjusting sauce",
            "Cook to al dente (slightly firm to bite)",
        ],
    }

    tips = tips_db.get(ingredient_or_technique.lower(), [
        f"General tip: Research {ingredient_or_technique} for best practices"
    ])

    return json.dumps(
        {
            "topic": ingredient_or_technique,
            "tips": tips,
            "tip_count": len(tips),
            "source": "Culinary knowledge base",
        },
        indent=2,
    )


@tool
def find_ingredient_stores(ingredient: str, location: str) -> str:
    """
    Find where to buy specific ingredients near you.

    Args:
        ingredient: Ingredient name (e.g., "saffron", "fresh basil", "wagyu beef")
        location: Your location (city or address)

    Returns:
        Stores that carry the ingredient with addresses, prices, availability
    """
    # Simulated — replace with Google Places API, grocery store APIs
    sample_stores = [
        {
            "name": "Whole Foods Market",
            "address": "123 Main St, " + location,
            "distance_km": 2.3,
            "has_ingredient": True,
            "estimated_price": "$4.99",
            "hours": "8:00 AM - 10:00 PM",
            "phone": "+1-555-0123",
        },
        {
            "name": "Local Farmers Market",
            "address": "456 Market Plaza, " + location,
            "distance_km": 1.8,
            "has_ingredient": True,
            "estimated_price": "$3.50",
            "hours": "Sat-Sun 9:00 AM - 2:00 PM",
            "phone": "+1-555-0456",
        },
    ]

    return json.dumps(
        {
            "ingredient": ingredient,
            "location": location,
            "stores": sample_stores,
            "total_found": len(sample_stores),
            "note": "Simulated store data — connect to Places API in production",
        },
        indent=2,
    )


@tool
def suggest_ingredient_substitutes(ingredient: str) -> str:
    """
    Get ingredient substitution recommendations.

    Args:
        ingredient: Ingredient to substitute (e.g., "butter", "eggs", "soy sauce")

    Returns:
        Substitute options with ratios and usage notes
    """
    # Simulated substitution database
    substitutes_db = {
        "butter": [
            {"substitute": "Olive oil", "ratio": "3/4 cup oil = 1 cup butter", "notes": "Best for savory dishes"},
            {"substitute": "Coconut oil", "ratio": "1:1", "notes": "Works well in baking"},
            {"substitute": "Greek yogurt", "ratio": "1/2 cup yogurt = 1 cup butter", "notes": "Reduces calories"},
        ],
        "eggs": [
            {"substitute": "Flax eggs", "ratio": "1 tbsp ground flax + 3 tbsp water = 1 egg", "notes": "Let sit 5 min"},
            {"substitute": "Applesauce", "ratio": "1/4 cup = 1 egg", "notes": "Best for sweet baking"},
            {"substitute": "Mashed banana", "ratio": "1/4 cup = 1 egg", "notes": "Adds banana flavor"},
        ],
    }

    substitutes = substitutes_db.get(ingredient.lower(), [
        {"substitute": "Consult recipe", "ratio": "varies", "notes": f"No common substitute for {ingredient} found"}
    ])

    return json.dumps(
        {
            "original_ingredient": ingredient,
            "substitutes": substitutes,
            "note": "Test substitutes in small batches first",
        },
        indent=2,
    )
