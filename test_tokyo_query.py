"""
Test script for Tokyo travel query - captures full logs and timing
"""
import os
import sys
import time
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load .env file first
load_dotenv()

# Setup logging to capture everything
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('tokyo_query_test.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import after logging setup
from langgraph_sdk import get_client

async def test_tokyo_query():
    """Run the Tokyo travel query and monitor execution"""

    # Verify environment variables
    recursion_limit = os.getenv("OPENSENTINEL_RECURSION_LIMIT", "NOT SET")
    log_level = os.getenv("LOG_LEVEL", "NOT SET")

    logger.info("=" * 80)
    logger.info("TOKYO QUERY TEST - Environment Check")
    logger.info("=" * 80)
    logger.info(f"OPENSENTINEL_RECURSION_LIMIT: {recursion_limit}")
    logger.info(f"LOG_LEVEL: {log_level}")
    logger.info("=" * 80)

    # Connect to LangGraph server
    client = get_client(url="http://localhost:2024")

    # Get assistant ID from environment
    assistant_id = os.getenv("OPENSENTINEL_ASSISTANT_ID", "agent")

    logger.info(f"Connecting to assistant: {assistant_id}")

    # Create a new thread
    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    logger.info(f"Created thread: {thread_id}")

    # The Tokyo travel query
    query = (
        "i'm going to tokyo tomorrow in the morning, i need to know about the weather, "
        "dollar and euro rate and also how is the transport cost form chiba kashiwa "
        "station to tokyo station. yoo! advice me how to dress up too according to the weather."
    )

    logger.info("=" * 80)
    logger.info("SENDING QUERY")
    logger.info("=" * 80)
    logger.info(f"Query: {query}")
    logger.info("=" * 80)

    start_time = time.time()

    try:
        # Send the query (stream and wait for completion)
        result = await client.runs.wait(
            thread_id=thread_id,
            assistant_id=assistant_id,
            input={"messages": [{"role": "user", "content": query}]},
        )

        elapsed = time.time() - start_time

        logger.info("=" * 80)
        logger.info("QUERY COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        logger.info(f"Time elapsed: {elapsed:.2f} seconds")
        logger.info("=" * 80)

        # Extract and display the response
        messages = result.get("messages", [])

        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")

            if role == "assistant" and content:
                logger.info("=" * 80)
                logger.info("AGENT RESPONSE")
                logger.info("=" * 80)
                logger.info(content)
                logger.info("=" * 80)

        # Log full result structure
        logger.debug("Full result structure:")
        logger.debug(result)

        return True, elapsed

    except Exception as e:
        elapsed = time.time() - start_time

        logger.error("=" * 80)
        logger.error("QUERY FAILED")
        logger.error("=" * 80)
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        logger.error(f"Time elapsed: {elapsed:.2f} seconds")
        logger.error("=" * 80)

        # Try to get run details if available
        try:
            runs = await client.runs.list(thread_id=thread_id)
            logger.error(f"Run status: {runs}")
        except:
            pass

        return False, elapsed

if __name__ == "__main__":
    logger.info("Starting Tokyo query test...")
    logger.info(f"Working directory: {Path.cwd()}")

    success, elapsed = asyncio.run(test_tokyo_query())

    if success:
        logger.info(f"\n✓ Test PASSED in {elapsed:.2f} seconds")
        logger.info("Check tokyo_query_test.log for full details")
        sys.exit(0)
    else:
        logger.error(f"\n✗ Test FAILED after {elapsed:.2f} seconds")
        logger.error("Check tokyo_query_test.log for full details")
        sys.exit(1)
