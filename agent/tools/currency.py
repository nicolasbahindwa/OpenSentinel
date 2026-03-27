"""Currency exchange tool using the free Frankfurter API.

Provides exchange rates, conversion, historical rates, and currency listing.
No API key required.
"""

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor
from typing import ClassVar, Type

import httpx
from cachetools import TTLCache
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.currency", component="currency")

API_BASE = "https://api.frankfurter.app"
HEADERS = {"Accept": "application/json", "User-Agent": "OpenSentinel-Currency/1.0"}


# =============================================================================
# Input Schema
# =============================================================================


class CurrencyInput(BaseModel):
    action: str = Field(
        ...,
        description=(
            "Action to perform: "
            "'rates' — get current exchange rates for a base currency, "
            "'convert' — convert an amount from one currency to another, "
            "'history' — get historical rates between two currencies, "
            "'list' — list all supported currencies, "
            "'multi' — convert an amount to multiple currencies at once."
        ),
    )
    base: str = Field(default="USD", description="Base currency code (e.g., 'USD', 'EUR').")
    target: str = Field(default="", description="Target currency code for 'convert' or 'history'.")
    targets: str = Field(
        default="",
        description="Comma-separated target currencies for 'rates' or 'multi' (e.g., 'EUR,GBP,JPY').",
    )
    amount: float = Field(default=1.0, description="Amount to convert (default: 1.0).")
    start_date: str = Field(default="", description="Start date for 'history' (YYYY-MM-DD).")
    end_date: str = Field(default="", description="End date for 'history' (YYYY-MM-DD).")


# =============================================================================
# Tool Implementation
# =============================================================================


class CurrencyTool(BaseTool):
    name: str = "currency"
    description: str = (
        "Get currency exchange rates, convert amounts, and view historical rates. "
        "Uses the free Frankfurter API (no API key required). "
        "Supports all major currencies.\n\n"
        "Examples:\n"
        "- Current rates: action='rates', base='USD', targets='EUR,GBP,JPY'\n"
        "- Convert: action='convert', base='USD', target='EUR', amount=100\n"
        "- Historical: action='history', base='USD', target='EUR', start_date='2024-01-01', end_date='2024-12-31'\n"
        "- List currencies: action='list'\n"
        "- Multi-convert: action='multi', base='USD', targets='EUR,GBP,JPY', amount=100"
    )
    args_schema: Type[BaseModel] = CurrencyInput
    handle_tool_error: bool = True

    _cache: TTLCache = PrivateAttr()
    _client: httpx.AsyncClient = PrivateAttr()

    MAX_CONTENT_CHARS: ClassVar[int] = 3000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = TTLCache(maxsize=200, ttl=600)  # 10 min cache
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=15.0)

    async def _fetch(self, url: str) -> dict:
        """Fetch JSON from Frankfurter API."""
        cache_key = url
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = await self._client.get(url)
        response.raise_for_status()
        data = response.json()
        self._cache[cache_key] = data
        return data

    async def _get_rates(self, base: str, targets: str) -> str:
        url = f"{API_BASE}/latest?from={base.upper()}"
        if targets:
            symbols = ",".join(s.strip().upper() for s in targets.split(",") if s.strip())
            url += f"&to={symbols}"

        data = await self._fetch(url)
        rates = [
            {"currency": code, "rate": rate, "inverse": f"{1/rate:.6f}"}
            for code, rate in data.get("rates", {}).items()
        ]

        return json.dumps({
            "base": data.get("base"),
            "date": data.get("date"),
            "count": len(rates),
            "rates": rates,
        }, indent=2)

    async def _convert(self, base: str, target: str, amount: float) -> str:
        if not target:
            return json.dumps({"error": "Provide a target currency (e.g., target='EUR')"})

        url = f"{API_BASE}/latest?amount={amount}&from={base.upper()}&to={target.upper()}"
        data = await self._fetch(url)

        converted = data.get("rates", {}).get(target.upper())
        if converted is None:
            return json.dumps({"error": f"Currency '{target.upper()}' not found"})

        rate = converted / amount if amount else 0

        return json.dumps({
            "from": base.upper(),
            "to": target.upper(),
            "amount": amount,
            "converted": round(converted, 2),
            "rate": round(rate, 6),
            "date": data.get("date"),
            "formatted": f"{amount} {base.upper()} = {converted:.2f} {target.upper()}",
        }, indent=2)

    async def _get_history(self, base: str, target: str, start_date: str, end_date: str) -> str:
        if not target or not start_date or not end_date:
            return json.dumps({
                "error": "Provide target, start_date (YYYY-MM-DD), and end_date (YYYY-MM-DD)"
            })

        url = f"{API_BASE}/{start_date}..{end_date}?from={base.upper()}&to={target.upper()}"
        data = await self._fetch(url)

        history = []
        for date, rates in sorted(data.get("rates", {}).items()):
            rate_val = rates.get(target.upper())
            if rate_val is not None:
                history.append({"date": date, "rate": rate_val})

        rate_values = [h["rate"] for h in history]
        if rate_values:
            first, last = rate_values[0], rate_values[-1]
            change = ((last - first) / first) * 100 if first else 0
            summary = {
                "start_rate": first,
                "end_rate": last,
                "change": f"{change:.2f}%",
                "high": round(max(rate_values), 4),
                "low": round(min(rate_values), 4),
                "average": round(sum(rate_values) / len(rate_values), 4),
            }
        else:
            summary = {}

        return json.dumps({
            "base": base.upper(),
            "target": target.upper(),
            "period": {"start": start_date, "end": end_date},
            "data_points": len(history),
            "summary": summary,
            "history": history,
        }, indent=2)

    async def _list_currencies(self) -> str:
        data = await self._fetch(f"{API_BASE}/currencies")

        currencies = [{"code": code, "name": name} for code, name in data.items()]
        major_codes = {"USD", "EUR", "GBP", "JPY", "CHF", "AUD", "CAD", "CNY"}
        major = [c for c in currencies if c["code"] in major_codes]
        other = [c for c in currencies if c["code"] not in major_codes]

        return json.dumps({
            "total": len(currencies),
            "major": major,
            "other": other,
        }, indent=2)

    async def _multi_convert(self, base: str, targets: str, amount: float) -> str:
        if not targets:
            return json.dumps({"error": "Provide target currencies (e.g., targets='EUR,GBP,JPY')"})

        symbols = ",".join(s.strip().upper() for s in targets.split(",") if s.strip())
        url = f"{API_BASE}/latest?amount={amount}&from={base.upper()}&to={symbols}"
        data = await self._fetch(url)

        conversions = [
            {"currency": code, "value": f"{value:.2f}", "formatted": f"{value:.2f} {code}"}
            for code, value in data.get("rates", {}).items()
        ]

        return json.dumps({
            "from": base.upper(),
            "amount": amount,
            "date": data.get("date"),
            "conversions": conversions,
        }, indent=2)

    # -------------------------------------------------------------------------
    # BaseTool interface
    # -------------------------------------------------------------------------

    async def _arun(
        self,
        action: str,
        base: str = "USD",
        target: str = "",
        targets: str = "",
        amount: float = 1.0,
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        logger.info("currency_action", action=action, base=base, target=target)
        try:
            match action.lower():
                case "rates":
                    return await self._get_rates(base, targets)
                case "convert":
                    return await self._convert(base, target, amount)
                case "history":
                    return await self._get_history(base, target, start_date, end_date)
                case "list":
                    return await self._list_currencies()
                case "multi":
                    return await self._multi_convert(base, targets, amount)
                case _:
                    return json.dumps({
                        "error": f"Unknown action '{action}'. Use: rates, convert, history, list, multi"
                    })
        except httpx.HTTPStatusError as e:
            logger.error("currency_http_error", status=e.response.status_code)
            return json.dumps({"error": f"API error: HTTP {e.response.status_code}"})
        except Exception as e:
            logger.error("currency_error", error=str(e))
            return json.dumps({"error": str(e)})

    def _run(
        self,
        action: str,
        base: str = "USD",
        target: str = "",
        targets: str = "",
        amount: float = 1.0,
        start_date: str = "",
        end_date: str = "",
    ) -> str:
        coro = self._arun(action, base, target, targets, amount, start_date, end_date)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coro)

        # If a loop is already running in this thread, run the coroutine in a
        # dedicated worker thread so the sync tool interface still completes.
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
