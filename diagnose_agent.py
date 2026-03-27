"""
Emergency diagnostic script for OpenSentinel agent issues.

Run this when agent times out or gets stuck to see what's happening.
"""

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_environment():
    """Check critical environment variables."""
    print("\n=== ENVIRONMENT CHECK ===")

    critical_vars = {
        "LANGSMITH_TRACING": os.getenv("LANGSMITH_TRACING"),
        "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
        "OPENSENTINEL_RECURSION_LIMIT": os.getenv("OPENSENTINEL_RECURSION_LIMIT", "40"),
        "OPENSENTINEL_MODEL_NAME": os.getenv("OPENSENTINEL_MODEL_NAME"),
        "NVIDIA_API_KEY": "***" if os.getenv("NVIDIA_API_KEY") else None,
        "TAVILY_API_KEY": "***" if os.getenv("TAVILY_API_KEY") else None,
    }

    for key, value in critical_vars.items():
        status = "✓" if value else "✗"
        print(f"  {status} {key:30} = {value}")

    # Check recursion limit
    limit = int(os.getenv("OPENSENTINEL_RECURSION_LIMIT", "40"))
    if limit < 60:
        print(f"\n  ⚠️  WARNING: Recursion limit is {limit}, recommended is 60+")

    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level != "DEBUG":
        print(f"\n  ⚠️  WARNING: LOG_LEVEL is {log_level}, set to DEBUG for diagnostics")


def test_agent_creation():
    """Try to create the agent and report any errors."""
    print("\n=== AGENT CREATION TEST ===")

    try:
        from agent import create_agent
        print("  ✓ Importing agent module...")

        agent = create_agent()
        print("  ✓ Agent created successfully")
        print(f"  ✓ Agent type: {type(agent).__name__}")

        # Check config
        from agent.config import Config
        config = Config.from_runnable_config()
        print(f"  ✓ Recursion limit: {config.recursion_limit}")
        print(f"  ✓ Model: {config.base_model}")

        return True

    except Exception as e:
        print(f"  ✗ Failed to create agent: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_langgraph_server():
    """Check if LangGraph dev server is running."""
    print("\n=== LANGGRAPH SERVER CHECK ===")

    try:
        from langgraph_sdk import get_sync_client
        from gateway.config import GatewayConfig

        config = GatewayConfig()
        client = get_sync_client(url=config.url)

        print(f"  ✓ Connecting to {config.url}...")
        assistants = client.assistants.search(limit=1)
        print(f"  ✓ Server is running")
        print(f"  ✓ Found {len(assistants)} assistant(s)")

        return True

    except Exception as e:
        print(f"  ✗ Cannot connect to LangGraph server: {e}")
        print(f"  ℹ️  Start server with: langgraph dev")
        return False


def check_tools():
    """Check if tools can be loaded."""
    print("\n=== TOOLS CHECK ===")

    try:
        from agent.tools.lazy_loader import get_all_tools

        tools = get_all_tools()
        print(f"  ✓ Loaded {len(tools)} tools")

        # Show first few tools
        for i, tool in enumerate(tools[:5]):
            name = getattr(tool, 'name', 'unknown')
            print(f"    - {name}")

        if len(tools) > 5:
            print(f"    ... and {len(tools) - 5} more")

        return True

    except Exception as e:
        print(f"  ✗ Failed to load tools: {e}")
        return False


def suggest_fixes():
    """Suggest fixes based on diagnostics."""
    print("\n=== SUGGESTED FIXES ===")

    limit = int(os.getenv("OPENSENTINEL_RECURSION_LIMIT", "40"))
    if limit < 60:
        print("\n1. INCREASE RECURSION LIMIT")
        print("   Edit .env:")
        print("   OPENSENTINEL_RECURSION_LIMIT=60")

    log_level = os.getenv("LOG_LEVEL", "INFO")
    if log_level != "DEBUG":
        print("\n2. ENABLE DEBUG LOGGING")
        print("   Edit .env:")
        print("   LOG_LEVEL=DEBUG")

    print("\n3. RESTART LANGGRAPH SERVER")
    print("   Ctrl+C to stop current server")
    print("   Then run: langgraph dev")

    print("\n4. TEST WITH SIMPLE QUERY")
    print("   python -m gateway.cli")
    print("   You > What is 2+2?")
    print("   (Should complete instantly without tools)")

    print("\n5. CHECK LOGS")
    print("   Look for:")
    print("   - === ROUTING MIDDLEWARE ===")
    print("   - FORCING_ANSWER messages")
    print("   - tool_outputs count")
    print("   - recursion limit exceeded")


def main():
    """Run all diagnostics."""
    print("=" * 70)
    print("OPENSENTINEL AGENT DIAGNOSTICS")
    print("=" * 70)

    # Load .env if present
    try:
        from dotenv import load_dotenv
        load_dotenv()
        print("✓ Loaded .env file")
    except ImportError:
        print("⚠️  python-dotenv not installed, using system environment")
    except Exception as e:
        print(f"⚠️  Could not load .env: {e}")

    # Run checks
    check_environment()
    agent_ok = test_agent_creation()
    server_ok = check_langgraph_server()
    tools_ok = check_tools()

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    status = []
    if agent_ok:
        status.append("✓ Agent creation")
    else:
        status.append("✗ Agent creation FAILED")

    if server_ok:
        status.append("✓ LangGraph server")
    else:
        status.append("✗ LangGraph server NOT RUNNING")

    if tools_ok:
        status.append("✓ Tools loading")
    else:
        status.append("✗ Tools loading FAILED")

    for s in status:
        print(f"  {s}")

    if not (agent_ok and server_ok and tools_ok):
        suggest_fixes()
    else:
        print("\n✓ All systems operational!")
        print("\nIf agent still times out:")
        print("  1. Check logs with LOG_LEVEL=DEBUG")
        print("  2. Test with simple queries first")
        print("  3. Monitor 'tool_outputs count' in logs")
        print("  4. Look for 'FORCING_ANSWER' warnings")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    main()
