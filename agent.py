import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Literal
from tavily import TavilyClient
from deepagents import create_deep_agent
from deepagents.middleware.skills import SkillsMiddleware
from langchain_nvidia_ai_endpoints import ChatNVIDIA
from langgraph.store.memory import InMemoryStore
from tools.internet_search import TavilySearchTool
from backend.memory import composite_backend

# Load .env automatically
load_dotenv()

# REQUIRED: Verify all keys (remove after testing)
keys = ["NVIDIA_API_KEY", "TAVILY_API_KEY", "LANGSMITH_API_KEY"]
for key in keys:
    assert os.getenv(key), f"Missing {key} in .env"
    print(f"{key} loaded: {os.getenv(key)[:10]}...")  # Print first 10 chars for verification

# Initialize tools
search_tool = TavilySearchTool()
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

# Get absolute path to skills directory
PROJECT_ROOT = Path(__file__).parent
SKILLS_DIR = PROJECT_ROOT / "skills"

# Detect if being loaded by LangGraph API/Cloud
# LangGraph sets these environment variables when loading graphs
IS_LANGGRAPH_API = (
    os.getenv("LANGGRAPH_API_URL") is not None
    or os.getenv("LANGGRAPH_CLOUD") == "true"
    or "langgraph" in os.getenv("LANGSMITH_TRACING", "").lower()
    or __name__ == "__main__"  # Being imported, not run directly
)

# IMPORTANT: Only create InMemoryStore for local development
# LangGraph Cloud will inject its own PostgreSQL-backed store
# We simply don't pass the store parameter, letting the platform provide it
if not IS_LANGGRAPH_API:
    store = InMemoryStore()
    print("💻 Local mode - using InMemoryStore")
else:
    print("🌐 LangGraph API detected - will use platform-provided store")

print(f"Skills directory: {SKILLS_DIR}")
print(f"Skills directory exists: {SKILLS_DIR.exists()}")

# List skills for debugging
if SKILLS_DIR.exists():
    skill_folders = [d.name for d in SKILLS_DIR.iterdir() if d.is_dir()]
    print(f"Found skills: {skill_folders}")
    for skill_folder in skill_folders:
        skill_md = SKILLS_DIR / skill_folder / "SKILL.md"
        if skill_md.exists():
            # Read first 100 chars to verify YAML frontmatter
            content_preview = skill_md.read_text(encoding="utf-8")[:100]
            print(f"  - {skill_folder}/SKILL.md exists, preview: {content_preview[:50]}...")

# System prompt for the main agent
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

# Create backend factory with explicit skills directory
print("\n" + "="*60)
print("🔧 BACKEND CONFIGURATION")
print("="*60)
backend_factory = composite_backend(skills_dir=SKILLS_DIR)
print("✅ Backend factory created")
print("="*60)

# Create the deep agent with skills middleware
# Conditionally include store parameter based on environment
print("\n" + "="*60)
print("🤖 AGENT CONFIGURATION")
print("="*60)
print(f"  Model: qwen/qwen3.5-397b-a17b")
print(f"  Tools: {[search_tool.__class__.__name__]}")
print(f"  Backend: composite_backend")
print(f"  Middleware: SkillsMiddleware")
print(f"    - Backend factory: {backend_factory}")
print(f"    - Skills sources: {[str(SKILLS_DIR)]}")
print(f"    - Skills sources exist: {SKILLS_DIR.exists()}")

agent_config = {
    "model": model,
    "tools": [search_tool],
    "system_prompt": research_prompt,
    "backend": backend_factory,
    "middleware": [
        SkillsMiddleware(
            backend=backend_factory,
            sources=[str(SKILLS_DIR)],  # Absolute path to skills directory
        )
    ],
}

print("✅ Agent config dictionary created")
print("="*60)

# Only add store for local development
# LangGraph Cloud will inject its own store automatically
print("\n" + "="*60)
print("💾 STORE CONFIGURATION")
print("="*60)
if not IS_LANGGRAPH_API:
    agent_config["store"] = store
    print("✅ Using InMemoryStore (local development)")
else:
    print("✅ Using platform-provided store (LangGraph Cloud)")
print("="*60)

print("\n" + "="*60)
print("🚀 CREATING DEEP AGENT")
print("="*60)
print("Calling create_deep_agent with:")
for key, value in agent_config.items():
    if key == "middleware":
        print(f"  {key}: [SkillsMiddleware]")
    elif key == "model":
        print(f"  {key}: ChatNVIDIA")
    elif key == "backend":
        print(f"  {key}: <factory function>")
    else:
        print(f"  {key}: {value}")

deep_agent = create_deep_agent(**agent_config)

print("✅ Deep agent created successfully!")
print("="*60)

graph = deep_agent

print("\n" + "="*60)
print("📊 DEPLOYMENT SUMMARY")
print("="*60)
if IS_LANGGRAPH_API:
    print(f"🌐 LangGraph Cloud deployment")
    print(f"   - Persistence: Platform-provided (PostgreSQL)")
    print(f"   - Skills from: {SKILLS_DIR}")
    print(f"   - Middleware: SkillsMiddleware active")
else:
    print(f"💻 Local development mode")
    print(f"   - Persistence: InMemoryStore")
    print(f"   - Skills from: {SKILLS_DIR}")
    print(f"   - Middleware: SkillsMiddleware active")
print("="*60)
