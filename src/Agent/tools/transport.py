"""
Transport Schedule Tools — Flights, trains, buses, real-time transit
"""

from langchain_core.tools import tool
import json
from datetime import datetime, timedelta


@tool
def search_flights(origin: str, destination: str, date: str, return_date: str = "") -> str:
    """
    Search for flight options between two locations.

    Args:
        origin: Departure airport code or city (e.g., "JFK", "New York")
        destination: Arrival airport code or city (e.g., "LAX", "Los Angeles")
        date: Departure date (YYYY-MM-DD)
        return_date: Return date for round trip (optional, YYYY-MM-DD)

    Returns:
        Flight options with airlines, times, prices, durations
    """
    # Simulated — replace with Skyscanner API, Amadeus API, or Google Flights
    sample_flights = [
        {
            "flight_id": "FL001",
            "airline": "United Airlines",
            "flight_number": "UA1234",
            "departure": {
                "airport": origin,
                "time": f"{date}T08:00:00",
                "terminal": "4",
            },
            "arrival": {
                "airport": destination,
                "time": f"{date}T11:30:00",
                "terminal": "5",
            },
            "duration_minutes": 330,
            "stops": 0,
            "price_usd": 285,
            "class": "Economy",
            "availability": "Available",
        },
        {
            "flight_id": "FL002",
            "airline": "Delta",
            "flight_number": "DL5678",
            "departure": {
                "airport": origin,
                "time": f"{date}T14:00:00",
                "terminal": "2",
            },
            "arrival": {
                "airport": destination,
                "time": f"{date}T17:45:00",
                "terminal": "1",
            },
            "duration_minutes": 345,
            "stops": 0,
            "price_usd": 310,
            "class": "Economy",
            "availability": "Available",
        },
    ]

    trip_type = "round_trip" if return_date else "one_way"

    return json.dumps(
        {
            "origin": origin,
            "destination": destination,
            "departure_date": date,
            "return_date": return_date or None,
            "trip_type": trip_type,
            "flights": sample_flights,
            "total_found": len(sample_flights),
            "note": "Simulated flights — connect to flight API in production",
        },
        indent=2,
    )


@tool
def search_trains(origin: str, destination: str, date: str, time: str = "08:00") -> str:
    """
    Search for train schedules between stations.

    Args:
        origin: Departure station name or code
        destination: Arrival station name or code
        date: Travel date (YYYY-MM-DD)
        time: Preferred departure time (HH:MM)

    Returns:
        Train options with operators, times, prices, platforms
    """
    # Simulated — replace with Trainline API, Rail Europe API, or local transit APIs
    sample_trains = [
        {
            "train_id": "TR001",
            "operator": "Amtrak",
            "train_number": "Acela 2150",
            "departure": {
                "station": origin,
                "time": f"{date}T08:15:00",
                "platform": "7",
            },
            "arrival": {
                "station": destination,
                "time": f"{date}T11:45:00",
                "platform": "3",
            },
            "duration_minutes": 210,
            "stops": 2,
            "price_usd": 125,
            "class": "Business",
            "amenities": ["WiFi", "Power outlets", "Cafe car"],
        },
        {
            "train_id": "TR002",
            "operator": "Regional Rail",
            "train_number": "NE 412",
            "departure": {
                "station": origin,
                "time": f"{date}T09:30:00",
                "platform": "5",
            },
            "arrival": {
                "station": destination,
                "time": f"{date}T14:00:00",
                "platform": "2",
            },
            "duration_minutes": 270,
            "stops": 8,
            "price_usd": 68,
            "class": "Standard",
            "amenities": ["WiFi"],
        },
    ]

    return json.dumps(
        {
            "origin": origin,
            "destination": destination,
            "travel_date": date,
            "preferred_time": time,
            "trains": sample_trains,
            "total_found": len(sample_trains),
            "note": "Simulated trains — connect to rail API in production",
        },
        indent=2,
    )


@tool
def search_buses(origin: str, destination: str, date: str, time: str = "08:00") -> str:
    """
    Search for bus schedules between locations.

    Args:
        origin: Departure city or station
        destination: Arrival city or station
        date: Travel date (YYYY-MM-DD)
        time: Preferred departure time (HH:MM)

    Returns:
        Bus options with operators, times, prices, amenities
    """
    # Simulated — replace with FlixBus API, Greyhound API, or local transit APIs
    sample_buses = [
        {
            "bus_id": "BUS001",
            "operator": "Greyhound",
            "bus_number": "GH1234",
            "departure": {
                "station": origin + " Bus Terminal",
                "time": f"{date}T08:00:00",
                "gate": "12",
            },
            "arrival": {
                "station": destination + " Bus Station",
                "time": f"{date}T13:30:00",
                "gate": "5",
            },
            "duration_minutes": 330,
            "stops": 3,
            "price_usd": 45,
            "amenities": ["WiFi", "Power outlets", "Restroom"],
            "availability": "Available",
        },
        {
            "bus_id": "BUS002",
            "operator": "FlixBus",
            "bus_number": "FB789",
            "departure": {
                "station": origin + " Central",
                "time": f"{date}T10:30:00",
                "gate": "8",
            },
            "arrival": {
                "station": destination + " Downtown",
                "time": f"{date}T15:45:00",
                "gate": "3",
            },
            "duration_minutes": 315,
            "stops": 2,
            "price_usd": 38,
            "amenities": ["WiFi", "Power outlets", "Snacks"],
            "availability": "Available",
        },
    ]

    return json.dumps(
        {
            "origin": origin,
            "destination": destination,
            "travel_date": date,
            "preferred_time": time,
            "buses": sample_buses,
            "total_found": len(sample_buses),
            "note": "Simulated buses — connect to bus API in production",
        },
        indent=2,
    )


@tool
def get_live_transit_status(route_id: str, transit_type: str = "bus") -> str:
    """
    Get real-time status for a specific transit route.

    Args:
        route_id: Route or line identifier (e.g., "M15", "Red Line", "Route 501")
        transit_type: Type of transit (bus, train, subway, tram)

    Returns:
        Real-time arrival times, delays, service alerts
    """
    # Simulated — replace with local transit APIs (GTFS, MTA, TfL, etc.)
    return json.dumps(
        {
            "route_id": route_id,
            "transit_type": transit_type,
            "status": "Operating",
            "next_arrivals": [
                {"stop": "Main Street", "arrival_time": (datetime.now() + timedelta(minutes=3)).isoformat(), "delay_minutes": 2},
                {"stop": "Central Station", "arrival_time": (datetime.now() + timedelta(minutes=8)).isoformat(), "delay_minutes": 0},
                {"stop": "West End", "arrival_time": (datetime.now() + timedelta(minutes=15)).isoformat(), "delay_minutes": 1},
            ],
            "service_alerts": [],
            "last_updated": datetime.now().isoformat(),
            "note": "Simulated live data — connect to transit API in production",
        },
        indent=2,
    )


@tool
def check_flight_status(flight_number: str, date: str) -> str:
    """
    Check real-time status of a specific flight.

    Args:
        flight_number: Flight number (e.g., "UA1234", "DL5678")
        date: Flight date (YYYY-MM-DD)

    Returns:
        Flight status, gate, baggage claim, delays
    """
    # Simulated — replace with FlightAware API, AviationStack, or airline APIs
    return json.dumps(
        {
            "flight_number": flight_number,
            "date": date,
            "status": "On Time",
            "departure": {
                "airport": "JFK",
                "scheduled": f"{date}T08:00:00",
                "actual": f"{date}T08:05:00",
                "terminal": "4",
                "gate": "B12",
            },
            "arrival": {
                "airport": "LAX",
                "scheduled": f"{date}T11:30:00",
                "estimated": f"{date}T11:35:00",
                "terminal": "5",
                "gate": "52A",
                "baggage_claim": "3",
            },
            "delay_minutes": 5,
            "last_updated": datetime.now().isoformat(),
            "note": "Simulated flight status — connect to flight tracking API in production",
        },
        indent=2,
    )


@tool
def compare_transport_options(origin: str, destination: str, date: str) -> str:
    """
    Compare all transport options (flight, train, bus) for a route.

    Args:
        origin: Starting location
        destination: Ending location
        date: Travel date (YYYY-MM-DD)

    Returns:
        Comparison of all transport modes with fastest, cheapest options
    """
    # Simulated comparison
    options = [
        {
            "mode": "Flight",
            "duration_minutes": 330,
            "price_usd": 285,
            "departure": f"{date}T08:00:00",
            "arrival": f"{date}T13:30:00",
            "provider": "United Airlines",
        },
        {
            "mode": "Train",
            "duration_minutes": 420,
            "price_usd": 125,
            "departure": f"{date}T08:15:00",
            "arrival": f"{date}T15:15:00",
            "provider": "Amtrak",
        },
        {
            "mode": "Bus",
            "duration_minutes": 510,
            "price_usd": 45,
            "departure": f"{date}T08:00:00",
            "arrival": f"{date}T16:30:00",
            "provider": "Greyhound",
        },
    ]

    fastest = min(options, key=lambda x: x["duration_minutes"])
    cheapest = min(options, key=lambda x: x["price_usd"])

    return json.dumps(
        {
            "origin": origin,
            "destination": destination,
            "date": date,
            "options": options,
            "recommendations": {
                "fastest": fastest,
                "cheapest": cheapest,
            },
            "note": "Simulated comparison — connect to transport APIs in production",
        },
        indent=2,
    )
