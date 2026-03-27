"""
Utility to clear agent cache during development.

The agent creation function uses @lru_cache for performance.
When you modify middleware, tools, or agent configuration, you need to clear
the cache to see your changes take effect.

Best Practices for Cache Management:
====================================

Option 1: Clear cache programmatically (RECOMMENDED for development)
---------------------------------------------------------------------
from agent.agent_professional import create_professional_agent
create_professional_agent.cache_clear()

Option 2: Restart LangGraph server (SIMPLE but slower)
-------------------------------------------------------
- Press Ctrl+C in langgraph dev terminal
- Run: langgraph dev
- Server loads fresh code

Option 3: Remove cache decorator temporarily (FAST iteration)
--------------------------------------------------------------
# In agent_professional.py, comment out @lru_cache:
# @lru_cache(maxsize=1)  # TEMPORARILY DISABLED
def create_professional_agent(...):
    ...

**When to use each approach:**
- Development/testing: Option 3 (no cache) for fastest iteration
- Production: Option 1 + proper cache key design
- Quick fixes: Option 2 (restart server)

**Cache Key Design (Advanced):**
For production, consider adding a version parameter to the cache key:
@lru_cache(maxsize=1)
def create_professional_agent(
    tool_names: Optional[tuple[str, ...]] = None,
    subagent_names: Optional[tuple[str, ...]] = None,
    version: str = "v1"  # Change this to force cache invalidation
) -> CompiledStateGraph:
    ...

"""

if __name__ == "__main__":
    print("Clearing agent cache...")

    try:
        from agent.agent_professional import create_professional_agent

        # Check if function has cache
        if hasattr(create_professional_agent, 'cache_clear'):
            create_professional_agent.cache_clear()
            print("✓ Agent cache cleared successfully!")
            print("  Next agent creation will use fresh code.")
        else:
            print("ℹ Cache decorator not found - agent is not cached.")
            print("  This is normal if @lru_cache was removed for development.")

    except ImportError as e:
        print(f"✗ Error importing agent: {e}")
        print("  Make sure you're in the project root directory.")
    except Exception as e:
        print(f"✗ Unexpected error: {e}")

    print("\nNote: After clearing cache, restart langgraph dev to see changes.")
