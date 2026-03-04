"""
Tools package for OpenSentinel Agent
"""
import os
from dotenv import load_dotenv
from .internet_search import TavilySearchTool
from .weather import WeatherLookupTool

# Load environment variables
load_dotenv()

# Initialize tool instances with API keys from environment
tavily_api_key = os.getenv("TAVILY_API_KEY")
internet_search = TavilySearchTool(api_key=tavily_api_key)

openweathermap_api_key = os.getenv("OPENWEATHERMAP_API_KEY")
weather_lookup = WeatherLookupTool(api_key=openweathermap_api_key) if openweathermap_api_key else None

# Export for the agent
__all__ = [
    "internet_search",
    "weather_lookup",
    "TavilySearchTool",
    "WeatherLookupTool",
]
