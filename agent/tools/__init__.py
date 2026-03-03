"""
Tools package for OpenSentinel Agent
"""
import os
from dotenv import load_dotenv
from .internet_search import TavilySearchTool

# Load environment variables
load_dotenv()

# Initialize tool instances with API key from environment
tavily_api_key = os.getenv("TAVILY_API_KEY")
internet_search = TavilySearchTool(api_key=tavily_api_key)

# Export as a list for the agent
__all__ = ["internet_search", "TavilySearchTool"]
