"""
Travel Coordinator Subagent Configuration

Coordinates flights, trains, buses, and transit planning.
"""

from ..tools import (
    search_flights,
    search_trains,
    search_buses,
    get_live_transit_status,
    check_flight_status,
    compare_transport_options,
)


def get_config():
    """Returns the travel coordinator subagent configuration."""
    return {
        "name": "travel_coordinator",
        "description": "Coordinates flights, trains, buses, and transit. Use for travel planning.",
        "system_prompt": (
            "You are a travel planning specialist. Search and compare transport options, "
            "check live status, and coordinate multi-leg journeys. Optimize for cost, time, and convenience. "
            "Alert about delays or disruptions."
        ),
        "tools": [
            search_flights,
            search_trains,
            search_buses,
            get_live_transit_status,
            check_flight_status,
            compare_transport_options,
        ],
    }
