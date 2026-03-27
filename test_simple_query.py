"""
Simple test with single-part query to diagnose recursion issue
"""
import os
import sys
import time
import logging
import asyncio
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

logger = logging.getLogger(__name__)

from langgraph_sdk import get_client

async def test_simple_query(query: str):
    """Run a simple query and monitor execution"""

    logger.info("=" * 80)
    logger.info(f"TESTING: {query}")
    logger.info("=" * 80)

    client = get_client(url="http://localhost:2024")
    assistant_id = os.getenv("OPENSENTINEL_ASSISTANT_ID", "agent")

    thread = await client.threads.create()
    thread_id = thread["thread_id"]

    start_time = time.time()

    try:
        result = await client.runs.wait(
            thread_id=thread_id,
            assistant_id=assistant_id,
            input={"messages": [{"role": "user", "content": query}]},
        )

        elapsed = time.time() - start_time

        # Extract response
        messages = result.get("messages", [])
        for msg in messages:
            if msg.get("role") == "assistant":
                content = msg.get("content", "")
                if content:
                    logger.info("=" * 80)
                    logger.info(f"✓ SUCCESS ({elapsed:.1f}s)")
                    logger.info("=" * 80)
                    logger.info(f"Response: {content[:200]}...")
                    return True, elapsed

        logger.error(f"✗ No response found ({elapsed:.1f}s)")
        return False, elapsed

    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"✗ FAILED ({elapsed:.1f}s): {e}")
        return False, elapsed

async def run_all_tests():
    """Run progressively complex tests"""

    tests = [
        ("Simple fact", "What is 2+2?"),
        ("Weather only", "What's the weather in Tokyo?"),
        ("Currency only", "What's the USD to JPY exchange rate?"),
        ("Two parts", "What's the weather in Tokyo and USD to JPY rate?"),
    ]

    results = []

    for name, query in tests:
        logger.info(f"\n{'='*80}")
        logger.info(f"TEST: {name}")
        logger.info(f"{'='*80}")

        success, elapsed = await test_simple_query(query)
        results.append((name, success, elapsed))

        if not success:
            logger.warning(f"Test '{name}' failed - stopping here")
            break

        # Small delay between tests
        await asyncio.sleep(2)

    # Summary
    logger.info(f"\n{'='*80}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*80}")
    for name, success, elapsed in results:
        status = "✓ PASS" if success else "✗ FAIL"
        logger.info(f"{status} {name:20s} ({elapsed:.1f}s)")

if __name__ == "__main__":
    asyncio.run(run_all_tests())
