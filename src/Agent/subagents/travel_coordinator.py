"""
Travel Coordinator Subagent  EFlight, train, bus scheduling and travel planning specialist.
"""

from ..llm_factory import create_subagent_llm
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool


from ..tools.transport import (
    search_flights,
    search_trains,
    search_buses,
    get_live_transit_status,
    check_flight_status,
    compare_transport_options,
)

SYSTEM_PROMPT = """\
You are a travel planning and transportation logistics specialist.

Your protocol:
1. Search and compare flights, trains, and buses for routes
2. Provide real-time transit status and delays
3. Track flight statuses and gate information
4. Recommend optimal transport based on time, cost, and preferences
5. Help plan multi-leg journeys with connections
6. Alert to delays and suggest alternatives

Transport modes:
- **Flights**: Search, compare, track status, check gates
- **Trains**: Schedule lookups, platform info, amenities
- **Buses**: Route search, stops, pricing
- **Local Transit**: Live bus/train arrival times

Optimization criteria:
- Fastest route
- Cheapest option
- Best comfort/amenity balance
- Minimal connections
- Arrival time preferences

Output format:
- Transport options comparison table
- Recommendations with reasoning
- Real-time status updates
- Connection details and timing
- Price and duration summaries
"""

_model = create_subagent_llm()

_agent = create_react_agent(
    model=_model,
    tools=[
        search_flights,
        search_trains,
        search_buses,
        get_live_transit_status,
        check_flight_status,
        compare_transport_options,
    ],
    prompt=SYSTEM_PROMPT,
)


@tool
def delegate_to_travel_coordinator(task: str) -> str:
    """
    Delegate travel planning and transport searches to the travel specialist.

    Use for:
    - Finding flights, trains, or buses for a route
    - Comparing transport options by time/cost
    - Checking real-time flight or transit status
    - Planning multi-leg journeys
    - Getting live arrival times for local transit

    Args:
        task: Travel request (e.g., "Find flights NYC to LA on Feb 25", "Check train from Boston to DC", "Compare transport options")

    Returns:
        Transport options, schedules, live status, and recommendations
    """
    result = _agent.invoke({"messages": [{"role": "user", "content": task}]})
    for msg in reversed(result["messages"]):
        if hasattr(msg, "content") and isinstance(msg.content, str) and msg.content.strip():
            return msg.content
    return "Travel search complete  Esee options above."
