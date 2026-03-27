"""
Test with minimal agent configuration to isolate recursion issue
"""
import os
from dotenv import load_dotenv
load_dotenv()

from functools import lru_cache
from langchain.agents.deepagents import create_deep_agent
from langgraph.graph.state import CompiledStateGraph
from agent.config.config import Config
from agent.logger import configure_logging, get_logger
from agent.prompt.get_prompt import get_full_prompt
from agent.tools import get_selected_tools

logger = get_logger("test_minimal", component="test")

@lru_cache(maxsize=1)
def create_minimal_agent() -> CompiledStateGraph:
    """Create agent with minimal middleware"""
    configure_logging(json_output=False, log_level="DEBUG")
    logger.info("Creating MINIMAL agent for testing...")

    configurable = Config.from_runnable_config()

    # Only essential tools
    tools = get_selected_tools(("web_browser", "currency"))

    # NO MIDDLEWARE - completely vanilla agent
    agent = create_deep_agent(
        model=configurable.base_model,
        name="MINIMAL_TEST_AGENT",
        system_prompt=get_full_prompt(),
        tools=tools,
        subagents=[],  # No subagents
        skills=[],  # No skills
        middleware=[],  # NO MIDDLEWARE AT ALL
        debug=True,
    )

    return agent.with_config({"recursion_limit": 60})

if __name__ == "__main__":
    import asyncio
    from langgraph_sdk import get_client

    async def test():
        logger.info("="*80)
        logger.info("MINIMAL AGENT TEST")
        logger.info("="*80)

        # Test simple query
        query = "What is 2+2?"

        logger.info(f"Query: {query}")

        client = get_client(url="http://localhost:2024")

        # This won't work directly - we need to register the minimal agent first
        # For now, just create it to verify it compiles
        agent = create_minimal_agent()
        logger.info("✓ Minimal agent created successfully")
        logger.info(f"✓ Agent type: {type(agent)}")
        logger.info(f"✓ Recursion limit: 60")

        logger.info("\nTo test this agent, you need to:")
        logger.info("1. Export it in langgraph.json")
        logger.info("2. Restart langgraph dev")
        logger.info("3. Query via CLI or SDK")

    asyncio.run(test())
