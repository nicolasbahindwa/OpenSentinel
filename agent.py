import os
from dotenv import load_dotenv
from tavily import TavilyClient
from deepagents import create_deep_agent
from deepagents.middleware.skills import SkillsMiddleware
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.store.memory import InMemoryStore
from tools.internet_search import TavilySearchTool
from backend.memory import composite_backend

load_dotenv()

# Initialize tools
search_tool = TavilySearchTool()
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Detect if being loaded by LangGraph API/Cloud
IS_LANGGRAPH_API = (
    os.getenv("LANGGRAPH_API_URL") is not None
    or os.getenv("LANGGRAPH_CLOUD") == "true"
    or "langgraph" in os.getenv("LANGSMITH_TRACING", "").lower()
    or __name__ == "__main__"
)

# Only create InMemoryStore for local development
if not IS_LANGGRAPH_API:
    store = InMemoryStore()
else:
    store = None

# System prompt
research_prompt = """You are an expert researcher and life management assistant.

Conduct thorough research, then write polished reports.

You have access to skills that enhance your capabilities:
- Mood Adaptation: Adjust your communication style to match the user's tone while maintaining accuracy

Use these skills appropriately to improve your responses."""

# Initialize the LLM
model = ChatNVIDIA(
    model="qwen/qwen3.5-397b-a17b",
    temperature=0.1,
    max_tokens=2048,
    api_key=os.environ["NVIDIA_API_KEY"],
)

# Use relative path to avoid blocking os.getcwd at module import
SKILLS_DIR = "skills"

# Create backend factory
backend_factory = composite_backend(skills_dir=SKILLS_DIR)

# Create agent configuration
agent_config = {
    "model": model,
    "tools": [search_tool],
    "system_prompt": research_prompt,
    "backend": backend_factory,
    "middleware": [
        SkillsMiddleware(
            backend=backend_factory,
            sources=[SKILLS_DIR],
        )
    ],
}

# Add store only for local development
if not IS_LANGGRAPH_API:
    agent_config["store"] = store

# Create the agent
deep_agent = create_deep_agent(**agent_config)

graph = deep_agent
