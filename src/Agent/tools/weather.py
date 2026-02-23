"""
Weather Monitoring Tools — Real-time weather, forecasts, and intelligent alerts
"""

from langchain_core.tools import tool
import json
from datetime import datetime, timedelta


@tool
def get_current_weather(location: str) -> str:
    """
    Get current weather conditions for a location.

    Args:
        location: City name or coordinates (e.g., "Tokyo", "New York", "35.6762,139.6503")

    Returns:
        Current weather with temperature, conditions, humidity, wind
    """
    # Simulated — replace with OpenWeatherMap, WeatherAPI, or NOAA API
    return json.dumps(
        {
            "location": location,
            "current": {
                "temperature_c": 18,
                "temperature_f": 64,
                "condition": "Partly Cloudy",
                "feels_like_c": 16,
                "humidity_percent": 65,
                "wind_kph": 12,
                "wind_direction": "NW",
                "uv_index": 4,
                "visibility_km": 10,
            },
            "timestamp": datetime.now().isoformat(),
            "note": "Simulated data — connect to OpenWeatherMap API in production",
        },
        indent=2,
    )


@tool
def get_weather_forecast(location: str, days: int = 3) -> str:
    """
    Get weather forecast for upcoming days.

    Args:
        location: City name or coordinates
        days: Number of days to forecast (1-14)

    Returns:
        Daily forecast with high/low temps, conditions, precipitation chance
    """
    forecast_days = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")
        forecast_days.append({
            "date": date,
            "high_c": 22 - i,
            "low_c": 12 - i,
            "condition": "Sunny" if i == 0 else "Partly Cloudy",
            "precipitation_chance": 10 + (i * 15),
            "wind_kph": 10 + i * 2,
        })

    return json.dumps(
        {
            "location": location,
            "forecast": forecast_days,
            "note": "Simulated forecast — connect to weather API in production",
        },
        indent=2,
    )


@tool
def get_hourly_forecast(location: str, hours: int = 12) -> str:
    """
    Get hourly weather forecast.

    Args:
        location: City name or coordinates
        hours: Number of hours to forecast (1-48)

    Returns:
        Hourly forecast with temp, conditions, precipitation probability
    """
    hourly_data = []
    for i in range(hours):
        hour_time = (datetime.now() + timedelta(hours=i)).strftime("%Y-%m-%d %H:00")
        hourly_data.append({
            "time": hour_time,
            "temperature_c": 18 + (i % 6) - 3,
            "condition": "Clear" if i < 6 else "Cloudy",
            "precipitation_chance": 5 + (i * 3),
            "humidity": 60 + i,
        })

    return json.dumps(
        {
            "location": location,
            "hourly_forecast": hourly_data[:hours],
            "note": "Simulated hourly data — connect to weather API in production",
        },
        indent=2,
    )


@tool
def detect_weather_alerts(location: str) -> str:
    """
    Check for severe weather alerts and warnings.

    Args:
        location: City name or coordinates

    Returns:
        Active weather alerts (storms, extreme temps, etc.)
    """
    # Simulated alerts
    alerts = []
    # Example: Rain alert
    # alerts.append({
    #     "type": "rain_warning",
    #     "severity": "moderate",
    #     "message": "Rain expected in 2 hours (80% chance)",
    #     "valid_until": (datetime.now() + timedelta(hours=6)).isoformat(),
    # })

    return json.dumps(
        {
            "location": location,
            "alerts": alerts,
            "alert_count": len(alerts),
            "status": "no_alerts" if not alerts else "active_alerts",
            "checked_at": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def check_precipitation_forecast(location: str, time_window_hours: int = 6) -> str:
    """
    Check if rain/snow is expected in the next N hours.

    Args:
        location: City name or coordinates
        time_window_hours: How far ahead to check (default 6 hours)

    Returns:
        Precipitation forecast and timing
    """
    # Simulated precipitation check
    rain_expected = False
    rain_start_time = None
    rain_probability = 15

    # Example: Rain in 2 hours
    # rain_expected = True
    # rain_start_time = (datetime.now() + timedelta(hours=2)).isoformat()
    # rain_probability = 80

    return json.dumps(
        {
            "location": location,
            "time_window_hours": time_window_hours,
            "rain_expected": rain_expected,
            "rain_start_time": rain_start_time,
            "precipitation_probability": rain_probability,
            "recommendation": "Bring umbrella" if rain_expected else "No rain expected",
            "checked_at": datetime.now().isoformat(),
        },
        indent=2,
    )


@tool
def compare_weather_change(location: str, threshold_temp_change: int = 5) -> str:
    """
    Detect significant weather changes from yesterday to today.

    Args:
        location: City name or coordinates
        threshold_temp_change: Temperature difference threshold in Celsius

    Returns:
        Weather comparison and change alerts
    """
    # Simulated comparison
    yesterday_temp = 15
    today_temp = 18
    temp_change = today_temp - yesterday_temp

    is_significant_change = abs(temp_change) >= threshold_temp_change

    return json.dumps(
        {
            "location": location,
            "yesterday": {
                "temperature_c": yesterday_temp,
                "condition": "Rainy",
            },
            "today": {
                "temperature_c": today_temp,
                "condition": "Partly Cloudy",
            },
            "temperature_change_c": temp_change,
            "is_significant_change": is_significant_change,
            "alert": f"Temperature increased by {temp_change}°C" if temp_change > 0 else f"Temperature decreased by {abs(temp_change)}°C",
            "checked_at": datetime.now().isoformat(),
        },
        indent=2,
    )
