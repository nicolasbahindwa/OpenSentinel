import os
import asyncio
from collections import Counter
from typing import Optional, Type, ClassVar

import httpx
from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.tools import BaseTool
from cachetools import TTLCache


# ==============================
# Input Schema
# ==============================

class WeatherInput(BaseModel):
    city: str = Field(..., min_length=1, description="City name (e.g. 'London' or 'Tokyo,JP')")
    units: str = Field(default="metric", description="Units: 'metric' (Celsius) or 'imperial' (Fahrenheit)")


# ==============================
# Tool Implementation
# ==============================

class WeatherLookupTool(BaseTool):
    name: str = "weather_lookup"
    description: str = (
        "Look up current weather conditions and 5-day forecast for a city. "
        "Use this tool when: "
        "1) User asks about weather, temperature, or forecast "
        "2) User needs to plan outdoor activities or travel "
        "3) Part of a daily briefing that includes weather. "
        "Returns current conditions (temp, humidity, wind, description) and 5-day forecast."
    )
    args_schema: Type[BaseModel] = WeatherInput
    handle_tool_error: bool = True

    _api_key: str = PrivateAttr()
    _client: httpx.Client = PrivateAttr()
    _cache: TTLCache = PrivateAttr()

    BASE_URL: ClassVar[str] = "https://api.openweathermap.org/data/2.5"
    MAX_FORECAST_DAYS: ClassVar[int] = 5

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)

        api_key = api_key or os.environ.get("OPENWEATHERMAP_API_KEY")
        if not api_key:
            raise ValueError("OPENWEATHERMAP_API_KEY environment variable required")

        self._api_key = api_key
        self._client = httpx.Client(timeout=10.0)
        self._cache = TTLCache(maxsize=200, ttl=1800)  # 30 min cache

    # ------------------------------
    # Sync version
    # ------------------------------

    def _run(self, city: str, units: str = "metric") -> str:
        cache_key = f"{city}:{units}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        params = {"appid": self._api_key, "units": units, "q": city}

        try:
            current_resp = self._client.get(f"{self.BASE_URL}/weather", params=params)
            current_resp.raise_for_status()
            current = current_resp.json()

            forecast_resp = self._client.get(f"{self.BASE_URL}/forecast", params=params)
            forecast_resp.raise_for_status()
            forecast = forecast_resp.json()
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"OpenWeatherMap API error: {e.response.status_code} - {e.response.text}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Weather lookup failed: {str(e)}") from e

        output = self._format_output(current, forecast, units)
        self._cache[cache_key] = output
        return output

    # ------------------------------
    # Async version (non-blocking)
    # ------------------------------

    async def _arun(self, city: str, units: str = "metric") -> str:
        return await asyncio.to_thread(self._run, city, units)

    # ------------------------------
    # Formatting
    # ------------------------------

    def _format_output(self, current: dict, forecast: dict, units: str) -> str:
        unit_sym = "°C" if units == "metric" else "°F"
        speed_unit = "m/s" if units == "metric" else "mph"

        sections = []

        # Current conditions
        sections.append("=== CURRENT WEATHER ===")
        location = f"{current.get('name', 'Unknown')}, {current.get('sys', {}).get('country', '')}"
        sections.append(f"Location: {location}")

        main = current.get("main", {})
        weather_desc = current.get("weather", [{}])[0].get("description", "N/A")
        sections.append(f"Conditions: {weather_desc.title()}")
        sections.append(f"Temperature: {main.get('temp', 'N/A')}{unit_sym} (feels like {main.get('feels_like', 'N/A')}{unit_sym})")
        sections.append(f"Humidity: {main.get('humidity', 'N/A')}%")

        wind = current.get("wind", {})
        sections.append(f"Wind: {wind.get('speed', 'N/A')} {speed_unit}")

        # 5-day forecast (aggregate from 3-hour intervals)
        sections.append("\n=== 5-DAY FORECAST ===")
        daily: dict[str, dict] = {}
        for entry in forecast.get("list", []):
            date = entry["dt_txt"].split(" ")[0]
            if date not in daily:
                daily[date] = {"temps": [], "descriptions": []}
            daily[date]["temps"].append(entry["main"]["temp"])
            daily[date]["descriptions"].append(entry["weather"][0]["description"])

        for date, data in list(daily.items())[:self.MAX_FORECAST_DAYS]:
            avg_temp = sum(data["temps"]) / len(data["temps"])
            min_temp = min(data["temps"])
            max_temp = max(data["temps"])
            most_common = Counter(data["descriptions"]).most_common(1)[0][0]
            sections.append(f"\n{date}: {most_common.title()}")
            sections.append(f"  High: {max_temp:.1f}{unit_sym} | Low: {min_temp:.1f}{unit_sym} | Avg: {avg_temp:.1f}{unit_sym}")

        return "\n".join(sections)
