"""
Inspect the failed run to understand what happened
"""
import os
import asyncio
import json
from dotenv import load_dotenv
load_dotenv()

from langgraph_sdk import get_client

async def inspect_failed_run(thread_id: str):
    """Inspect a failed run's history"""

    client = get_client(url="http://localhost:2024")

    print("="*80)
    print(f"INSPECTING THREAD: {thread_id}")
    print("="*80)

    # Get all runs for this thread
    runs = await client.runs.list(thread_id=thread_id, limit=1)

    if not runs:
        print("No runs found for this thread")
        return

    run = runs[0]
    run_id = run["run_id"]

    print(f"\nRun ID: {run_id}")
    print(f"Status: {run['status']}")
    print(f"Created: {run['created_at']}")
    print(f"Updated: {run['updated_at']}")

    # Get the thread state history to see all steps
    try:
        history = await client.threads.get_history(
            thread_id=thread_id,
            limit=100,  # Get last 100 states
        )

        print(f"\n{'='*80}")
        print(f"STATE HISTORY ({len(history)} states)")
        print(f"{'='*80}\n")

        # Analyze the states
        tool_calls = []
        ai_messages = []

        for i, state in enumerate(history):
            messages = state.get("values", {}).get("messages", [])

            for msg in messages:
                if isinstance(msg, dict):
                    role = msg.get("type") or msg.get("role")
                    content = msg.get("content", "")

                    if role == "tool":
                        tool_name = msg.get("name", "unknown")
                        tool_calls.append({
                            "step": i,
                            "tool": tool_name,
                            "content_preview": str(content)[:100]
                        })

                    elif role == "ai" or role == "assistant":
                        tool_calls_in_msg = msg.get("tool_calls", [])
                        if tool_calls_in_msg:
                            for tc in tool_calls_in_msg:
                                if isinstance(tc, dict):
                                    ai_messages.append({
                                        "step": i,
                                        "type": "tool_request",
                                        "tool": tc.get("name", "unknown"),
                                        "args_preview": str(tc.get("args", {}))[:100]
                                    })
                        elif content:
                            ai_messages.append({
                                "step": i,
                                "type": "message",
                                "content_preview": str(content)[:100]
                            })

        # Print summary
        print(f"Tool Calls Made: {len(tool_calls)}")
        print(f"AI Messages: {len(ai_messages)}")

        print(f"\n{'='*80}")
        print("TOOL CALL SEQUENCE")
        print(f"{'='*80}\n")

        for tc in tool_calls[-20:]:  # Last 20 tool calls
            print(f"Step {tc['step']:3d}: {tc['tool']:20s} -> {tc['content_preview']}")

        print(f"\n{'='*80}")
        print("AI MESSAGE SEQUENCE")
        print(f"{'='*80}\n")

        for msg in ai_messages[-20:]:  # Last 20 AI messages
            if msg['type'] == 'tool_request':
                print(f"Step {msg['step']:3d}: REQUEST {msg['tool']} with {msg['args_preview']}")
            else:
                print(f"Step {msg['step']:3d}: RESPONSE {msg['content_preview']}")

        # Check for patterns
        print(f"\n{'='*80}")
        print("PATTERN ANALYSIS")
        print(f"{'='*80}\n")

        # Count tool frequency
        tool_freq = {}
        for tc in tool_calls:
            tool = tc['tool']
            tool_freq[tool] = tool_freq.get(tool, 0) + 1

        print("Tool Usage Frequency:")
        for tool, count in sorted(tool_freq.items(), key=lambda x: -x[1]):
            print(f"  {tool:20s}: {count:3d} times")

        # Check for repetitive patterns
        if len(tool_calls) > 5:
            last_5_tools = [tc['tool'] for tc in tool_calls[-5:]]
            if len(set(last_5_tools)) == 1:
                print(f"\n⚠️  WARNING: Last 5 tool calls are ALL '{last_5_tools[0]}'")
            elif len(set(last_5_tools)) <= 2:
                print(f"\n⚠️  WARNING: Last 5 tool calls only use {len(set(last_5_tools))} different tools")

    except Exception as e:
        print(f"\nError getting history: {e}")
        print("\nTrying alternative approach - get state snapshots...")

        try:
            state = await client.threads.get_state(thread_id=thread_id)
            print(json.dumps(state, indent=2, default=str))
        except Exception as e2:
            print(f"Also failed: {e2}")

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        thread_id = sys.argv[1]
    else:
        # Use the thread from the most recent test
        thread_id = "bfe44a8d-821f-42f7-b124-d5185e35122c"
        print(f"Using thread from most recent test: {thread_id}")

    asyncio.run(inspect_failed_run(thread_id))
