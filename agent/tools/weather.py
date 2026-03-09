"""Weather lookup tool backed by the free Open-Meteo API."""

import asyncio
import threading
from typing import ClassVar, Type

import httpx
from cachetools import TTLCache
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.weather", component="weather")

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def describe_weather_code(code: int) -> str:
    return WMO_CODES.get(code, f"Unknown ({code})")


def wind_direction_label(degrees: float) -> str:
    labels = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    return labels[round(degrees / 22.5) % 16]


class WeatherInput(BaseModel):
    location: str = Field(
        ...,
        min_length=1,
        description="City name or place (for example: London, Tokyo, New York).",
    )
    units: str = Field(
        default="metric",
        description="Unit system: metric (Celsius, km/h) or imperial (Fahrenheit, mph).",
    )


class WeatherLookupTool(BaseTool):
    name: str = "weather_lookup"
    description: str = (
        "Get current weather and a 3-day forecast for any location using Open-Meteo. "
        "Use for weather, temperature, and outdoor planning requests.\n\n"
        "Examples:\n"
        '- City name: location="Istanbul", units="metric"\n'
        '- Imperial units: location="New York", units="imperial"\n'
        '- Default metric: location="Tokyo"'
    )
    args_schema: Type[BaseModel] = WeatherInput
    handle_tool_error: bool = True

    GEOCODING_URL: ClassVar[str] = "https://geocoding-api.open-meteo.com/v1/search"
    WEATHER_URL: ClassVar[str] = "https://api.open-meteo.com/v1/forecast"

    _cache: TTLCache = PrivateAttr()
    _cache_lock: threading.RLock = PrivateAttr()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = TTLCache(maxsize=200, ttl=900)  # 15 min cache
        self._cache_lock = threading.RLock()

    @staticmethod
    def _normalize_cache_key(location: str, units: str) -> str:
        """Create a consistent cache key from user input."""
        normalized_location = " ".join(location.lower().strip().split())
        return f"{normalized_location}:{units}"

    def _geocode(self, client: httpx.Client, location: str) -> dict | None:
        response = client.get(
            self.GEOCODING_URL,
            params={"name": location, "count": 1, "language": "en", "format": "json"},
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        if not results:
            return None
        place = results[0]
        return {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "name": place["name"],
            "admin1": place.get("admin1", ""),
            "country": place.get("country", ""),
        }

    def _run(self, location: str, units: str = "metric") -> str:
        units = units.lower().strip()
        if units not in {"metric", "imperial"}:
            units = "metric"

        cache_key = self._normalize_cache_key(location, units)

        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        is_imperial = units == "imperial"
        temp_unit = "fahrenheit" if is_imperial else "celsius"
        wind_unit = "mph" if is_imperial else "kmh"
        temp_symbol = "F" if is_imperial else "C"
        wind_symbol = "mph" if is_imperial else "km/h"

        try:
            with httpx.Client(timeout=10.0) as client:
                place = self._geocode(client, location)
                if not place:
                    return f"No location found for '{location}'."

                weather_params = {
                    "latitude": place["latitude"],
                    "longitude": place["longitude"],
                    "current": (
                        "temperature_2m,relative_humidity_2m,weather_code,"
                        "wind_speed_10m,wind_direction_10m,apparent_temperature,uv_index"
                    ),
                    "daily": "temperature_2m_max,temperature_2m_min,weather_code",
                    "temperature_unit": temp_unit,
                    "wind_speed_unit": wind_unit,
                    "timezone": "auto",
                    "forecast_days": 3,
                }
                response = client.get(self.WEATHER_URL, params=weather_params)
                response.raise_for_status()
                wx = response.json()
        except Exception as e:
            logger.error(
                "weather_api_error",
                location=location,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

        output = self._format_output(place, wx, temp_symbol, wind_symbol)

        with self._cache_lock:
            self._cache[cache_key] = output

        return output

    async def _arun(self, location: str, units: str = "metric") -> str:
        return await asyncio.to_thread(self._run, location, units)

    def _format_output(
        self, place: dict, wx: dict, temp_symbol: str, wind_symbol: str
    ) -> str:
        location_parts = [place["name"], place["admin1"], place["country"]]
        location_str = ", ".join([part for part in location_parts if part])

        current = wx["current"]
        lines = [
            f"Weather for {location_str}",
            f"Current: {describe_weather_code(current['weather_code'])}",
            (
                f"Temperature: {current['temperature_2m']} {temp_symbol} "
                f"(feels like {current['apparent_temperature']} {temp_symbol})"
            ),
            f"Humidity: {current['relative_humidity_2m']}%",
            (
                f"Wind: {current['wind_speed_10m']} {wind_symbol} "
                f"{wind_direction_label(current['wind_direction_10m'])}"
            ),
            f"UV Index: {current.get('uv_index', 'N/A')}",
            "",
            "3-Day Forecast:",
        ]

        daily = wx.get("daily", {})
        for idx in range(len(daily.get("time", []))):
            date = daily["time"][idx]
            high = daily["temperature_2m_max"][idx]
            low = daily["temperature_2m_min"][idx]
            desc = describe_weather_code(daily["weather_code"][idx])
            lines.append(f"- {date}: {low}-{high} {temp_symbol}, {desc}")

        return "\n".join(lines)


__all__ = ["WeatherLookupTool", "WeatherInput"]

