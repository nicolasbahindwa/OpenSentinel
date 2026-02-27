"""
Test script for OpenSentinel agent.

This script demonstrates basic agent functionality and tests subagent delegation.

Run with:
    uv run python test_agent.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Support running directly from source
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Load environment variables from .env file in the project root
env_path = project_root / ".env"

print(f"Looking for .env at: {env_path}")
print(f".env exists: {env_path.exists()}")

# Load with override to ensure variables are set
load_dotenv(dotenv_path=env_path, override=True)

from src.Agent.agent import create_agent
from src.Agent.llm_factory import DEFAULT_MODEL_NAME


def main():
    """Run basic agent tests."""

    print("=" * 60)
    print("OpenSentinel Agent Test")
    print("=" * 60)

    # Debug: Show all environment variables related to models
    print("\n[DEBUG] Environment variables:")
    for key in os.environ:
        if "MODEL" in key or "OLLAMA" in key or "OPENSENTINEL" in key:
            print(f"  {key} = {os.environ[key]}")

    # Check model configuration
    model_name = os.getenv("OPENSENTINEL_MODEL_NAME")
    if not model_name:
        print("\n[WARN] OPENSENTINEL_MODEL_NAME not set!")
        print("   Please set it in your .env file or environment.")
        print("\nExample .env file:")
        print("   OPENSENTINEL_MODEL_NAME=llama3.2")
        print("   OLLAMA_BASE_URL=http://localhost:11434")
        return

    print(f"\n[OK] Model configured: {model_name}")
    if DEFAULT_MODEL_NAME != model_name:
        print(f"  Effective model after normalization/fallback: {DEFAULT_MODEL_NAME}")
    if "gemini-1.5-flash" in model_name:
        fallback_model = os.getenv("OPENSENTINEL_FALLBACK_MODEL", "google_genai:gemini-2.0-flash")
        print(f"  Fallback model: {fallback_model}")
    print(f"  Temperature: {os.getenv('OPENSENTINEL_MODEL_TEMPERATURE', '0.3')}")
    print(f"  Max tokens: {os.getenv('OPENSENTINEL_MODEL_MAX_TOKENS', '8192')}")

    if "ollama" in model_name.lower() or "/" not in model_name:
        ollama_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        print(f"  Ollama URL: {ollama_url}")

    print("\n" + "=" * 60)
    print("Creating agent...")
    print("=" * 60)

    try:
        # Create the agent
        agent = create_agent(
            prompt_mode="standard",
            enable_human_in_the_loop=False  # Disable for testing
        )

        print("[OK] Agent created successfully!")
        print("\n" + "=" * 60)
        print("Testing agent with a simple query...")
        print("=" * 60)

        # Test query
        test_query = "what is the news in the DRCONGO today. try to analyse what going on there"

        print(f"\nQuery: {test_query}\n")

        # Run the agent with required thread_id configuration
        config = {"configurable": {"thread_id": "test-thread-1"}}
        result = agent.invoke(
            {"messages": [{"role": "user", "content": test_query}]},
            config=config
        )

        # Extract and display the response
        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "content") and msg.content:
                    print(f"Response:\n{msg.content}\n")

        print("=" * 60)
        print("[OK] Test completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        err = str(e)
        if "NOT_FOUND" in err and "gemini" in err.lower():
            print("\nDetected Google model ID mismatch.")
            print("Set OPENSENTINEL_MODEL_NAME to a model available to your API key,")
            print("or unset it and rely on GOOGLE_DEFAULT_MODEL.")
        if "RESOURCE_EXHAUSTED" in err and "gemini" in err.lower():
            print("\nDetected Google quota exhaustion.")
            print("Enable billing/increase quota for Gemini,")
            print("or switch OPENSENTINEL_MODEL_NAME to another provider model.")
        print("\nTroubleshooting:")
        print("1. Make sure Ollama is running (if using Ollama)")
        print("2. Check your .env file has correct settings")
        print("3. Verify the model is available:")
        print("   - For Ollama: ollama list")
        print("4. Check the error message above for details")
        return


def test_subagent():
    """Test a specific subagent (weather advisor example)."""
    print("\n" + "=" * 60)
    print("Testing Subagent Delegation (Weather Advisor)")
    print("=" * 60)

    try:
        agent = create_agent(enable_human_in_the_loop=False)

        test_query = "what do you think will happen in congo this coming week regarding the political situation and the security of the population. try to give me a detailed analysis based on the current news and trends. also, try to give me some recommendations for the population and the government to improve the situation and avoid further deterioration. also, try to give me some insights about the possible future scenarios and their implications for the region and the world. also, try to give me some insights about the possible future scenarios and their implications for the region and the world. also, try to give me some insights about the possible future scenarios and their implications for the region and the world."
        print(f"\nQuery: {test_query}\n")

        # Use thread_id configuration
        config = {"configurable": {"thread_id": "test-thread-weather"}}
        result = agent.invoke(
            {"messages": [{"role": "user", "content": test_query}]},
            config=config
        )

        if "messages" in result:
            for msg in result["messages"]:
                if hasattr(msg, "content") and msg.content:
                    print(f"Response:\n{msg.content}\n")

        print("[OK] Subagent test completed!")

    except Exception as e:
        print(f"[ERROR] Subagent test error: {e}")


if __name__ == "__main__":
    # Run basic test
    main()

    # Uncomment to test subagents
    # test_subagent()
