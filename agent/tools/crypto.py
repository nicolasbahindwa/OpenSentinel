"""Cryptocurrency tool using the free CoinGecko API.

Provides price lookup, market rankings, trending coins, coin details,
historical data, and global market statistics.
No API key required.
"""

import asyncio
import json
from typing import ClassVar, Type

import httpx
from cachetools import TTLCache
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.crypto", component="crypto")

API_BASE = "https://api.coingecko.com/api/v3"
HEADERS = {"Accept": "application/json", "User-Agent": "OpenSentinel-Crypto/1.0"}


# =============================================================================
# Input Schema
# =============================================================================


class CryptoInput(BaseModel):
    action: str = Field(
        ...,
        description=(
            "Action to perform: "
            "'price' — get current price for one or more coins, "
            "'markets' — top coins by market cap, "
            "'search' — search for a coin by name/symbol, "
            "'trending' — currently trending coins, "
            "'detail' — detailed info for a single coin, "
            "'history' — historical price data, "
            "'global' — global market statistics."
        ),
    )
    ids: str = Field(
        default="",
        description=(
            "Comma-separated coin IDs for 'price' or single ID for 'detail'/'history'. "
            "Use CoinGecko IDs like 'bitcoin', 'ethereum', 'solana'. "
            "Use 'search' action to find the correct ID."
        ),
    )
    query: str = Field(default="", description="Search query for 'search' action.")
    limit: int = Field(default=20, ge=1, le=100, description="Number of results for 'markets' (default: 20).")
    days: int = Field(default=30, description="Number of days for 'history' (1, 7, 30, 90, 365).")
    currency: str = Field(default="usd", description="VS currency for prices (default: usd).")


# =============================================================================
# Tool Implementation
# =============================================================================


class CryptoTool(BaseTool):
    name: str = "crypto"
    description: str = (
        "Get cryptocurrency data: prices, market rankings, trending coins, "
        "coin details, historical prices, and global market stats. "
        "Uses the free CoinGecko API (no API key required).\n\n"
        "Examples:\n"
        "- Price check: action='price', ids='bitcoin,ethereum,solana'\n"
        "- Top coins: action='markets', limit=10\n"
        "- Search: action='search', query='cardano'\n"
        "- Trending: action='trending'\n"
        "- Coin details: action='detail', ids='bitcoin'\n"
        "- Price history: action='history', ids='bitcoin', days=30\n"
        "- Global stats: action='global'"
    )
    args_schema: Type[BaseModel] = CryptoInput
    handle_tool_error: bool = True

    _cache: TTLCache = PrivateAttr()
    _client: httpx.AsyncClient = PrivateAttr()

    MAX_CONTENT_CHARS: ClassVar[int] = 3000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = TTLCache(maxsize=200, ttl=300)  # 5 min cache
        self._client = httpx.AsyncClient(headers=HEADERS, timeout=15.0)

    async def _fetch(self, endpoint: str) -> dict:
        """Fetch JSON from CoinGecko API."""
        url = f"{API_BASE}{endpoint}"
        cache_key = url
        if cache_key in self._cache:
            return self._cache[cache_key]

        response = await self._client.get(url)
        if response.status_code == 429:
            raise RuntimeError("CoinGecko rate limit exceeded. Try again in a minute.")
        response.raise_for_status()
        data = response.json()
        self._cache[cache_key] = data
        return data

    async def _get_price(self, ids: str, currency: str) -> str:
        coin_ids = [i.strip().lower() for i in ids.split(",") if i.strip()]
        if not coin_ids:
            return json.dumps({"error": "Provide coin IDs (e.g., 'bitcoin,ethereum')"})

        data = await self._fetch(
            f"/simple/price?ids={','.join(coin_ids)}"
            f"&vs_currencies={currency}"
            f"&include_24hr_change=true&include_24hr_vol=true&include_market_cap=true"
        )

        prices = []
        for coin_id, info in data.items():
            prices.append({
                "id": coin_id,
                "price": info.get(currency),
                "change_24h": f"{info.get(f'{currency}_24h_change', 0):.2f}%",
                "volume_24h": info.get(f"{currency}_24h_vol"),
                "market_cap": info.get(f"{currency}_market_cap"),
            })

        return json.dumps({"currency": currency, "count": len(prices), "prices": prices}, indent=2)

    async def _get_markets(self, limit: int, currency: str) -> str:
        data = await self._fetch(
            f"/coins/markets?vs_currency={currency}&order=market_cap_desc"
            f"&per_page={limit}&page=1&sparkline=false"
        )

        coins = []
        for coin in data:
            coins.append({
                "rank": coin.get("market_cap_rank"),
                "id": coin.get("id"),
                "symbol": (coin.get("symbol") or "").upper(),
                "name": coin.get("name"),
                "price": coin.get("current_price"),
                "change_24h": f"{coin.get('price_change_percentage_24h', 0):.2f}%",
                "market_cap": coin.get("market_cap"),
                "volume_24h": coin.get("total_volume"),
            })

        return json.dumps({"currency": currency, "count": len(coins), "coins": coins}, indent=2)

    async def _search(self, query: str) -> str:
        if not query:
            return json.dumps({"error": "Provide a search query"})

        data = await self._fetch(f"/search?query={query}")
        coins = []
        for coin in (data.get("coins") or [])[:10]:
            coins.append({
                "id": coin.get("id"),
                "symbol": (coin.get("symbol") or "").upper(),
                "name": coin.get("name"),
                "rank": coin.get("market_cap_rank"),
            })

        return json.dumps({"query": query, "count": len(coins), "coins": coins}, indent=2)

    async def _get_trending(self) -> str:
        data = await self._fetch("/search/trending")
        coins = []
        for entry in data.get("coins", []):
            item = entry.get("item", {})
            item_data = item.get("data", {})
            coins.append({
                "id": item.get("id"),
                "symbol": (item.get("symbol") or "").upper(),
                "name": item.get("name"),
                "rank": item.get("market_cap_rank"),
                "price": item_data.get("price"),
                "change_24h": f"{(item_data.get('price_change_percentage_24h', {}).get('usd') or 0):.2f}%",
            })

        return json.dumps({"count": len(coins), "trending": coins}, indent=2)

    async def _get_detail(self, coin_id: str) -> str:
        if not coin_id:
            return json.dumps({"error": "Provide a coin ID (e.g., 'bitcoin')"})

        data = await self._fetch(
            f"/coins/{coin_id.strip().lower()}"
            f"?localization=false&tickers=false&community_data=false&developer_data=false"
        )

        md = data.get("market_data", {})
        result = {
            "id": data.get("id"),
            "symbol": (data.get("symbol") or "").upper(),
            "name": data.get("name"),
            "rank": data.get("market_cap_rank"),
            "description": (data.get("description", {}).get("en") or "")[:500],
            "categories": (data.get("categories") or [])[:5],
            "price": {
                "current": md.get("current_price", {}).get("usd"),
                "high_24h": md.get("high_24h", {}).get("usd"),
                "low_24h": md.get("low_24h", {}).get("usd"),
                "change_24h": f"{md.get('price_change_percentage_24h', 0):.2f}%",
                "change_7d": f"{md.get('price_change_percentage_7d', 0):.2f}%",
                "change_30d": f"{md.get('price_change_percentage_30d', 0):.2f}%",
            },
            "market": {
                "market_cap": md.get("market_cap", {}).get("usd"),
                "volume_24h": md.get("total_volume", {}).get("usd"),
                "circulating_supply": md.get("circulating_supply"),
                "total_supply": md.get("total_supply"),
                "max_supply": md.get("max_supply"),
            },
            "ath": {
                "price": md.get("ath", {}).get("usd"),
                "change": f"{md.get('ath_change_percentage', {}).get('usd', 0):.2f}%",
                "date": md.get("ath_date", {}).get("usd"),
            },
        }

        return json.dumps(result, indent=2)

    async def _get_history(self, coin_id: str, days: int) -> str:
        if not coin_id:
            return json.dumps({"error": "Provide a coin ID (e.g., 'bitcoin')"})

        data = await self._fetch(
            f"/coins/{coin_id.strip().lower()}/market_chart?vs_currency=usd&days={days}"
        )

        prices_raw = data.get("prices", [])
        prices = [
            {"date": p[0], "price": round(p[1], 2)}
            for p in prices_raw
        ]

        price_values = [p["price"] for p in prices]
        if price_values:
            first, last = price_values[0], price_values[-1]
            change = ((last - first) / first) * 100 if first else 0
            summary = {
                "start_price": first,
                "end_price": last,
                "change": f"{change:.2f}%",
                "high": max(price_values),
                "low": min(price_values),
            }
        else:
            summary = {}

        # Return last 30 data points to avoid token explosion
        return json.dumps({
            "id": coin_id,
            "days": days,
            "data_points": len(prices),
            "summary": summary,
            "prices": prices[-30:],
        }, indent=2)

    async def _get_global(self) -> str:
        data = await self._fetch("/global")
        d = data.get("data", {})

        return json.dumps({
            "active_cryptos": d.get("active_cryptocurrencies"),
            "markets": d.get("markets"),
            "total_market_cap": d.get("total_market_cap", {}).get("usd"),
            "total_volume_24h": d.get("total_volume", {}).get("usd"),
            "market_cap_change_24h": f"{d.get('market_cap_change_percentage_24h_usd', 0):.2f}%",
            "dominance": {
                "btc": f"{d.get('market_cap_percentage', {}).get('btc', 0):.2f}%",
                "eth": f"{d.get('market_cap_percentage', {}).get('eth', 0):.2f}%",
            },
        }, indent=2)

    # -------------------------------------------------------------------------
    # BaseTool interface
    # -------------------------------------------------------------------------

    async def _arun(
        self,
        action: str,
        ids: str = "",
        query: str = "",
        limit: int = 20,
        days: int = 30,
        currency: str = "usd",
    ) -> str:
        logger.info("crypto_action", action=action, ids=ids, query=query)
        try:
            match action.lower():
                case "price":
                    return await self._get_price(ids, currency)
                case "markets":
                    return await self._get_markets(limit, currency)
                case "search":
                    return await self._search(query)
                case "trending":
                    return await self._get_trending()
                case "detail":
                    return await self._get_detail(ids)
                case "history":
                    return await self._get_history(ids, days)
                case "global":
                    return await self._get_global()
                case _:
                    return json.dumps({
                        "error": f"Unknown action '{action}'. "
                        "Use: price, markets, search, trending, detail, history, global"
                    })
        except httpx.HTTPStatusError as e:
            logger.error("crypto_http_error", status=e.response.status_code)
            return json.dumps({"error": f"API error: HTTP {e.response.status_code}"})
        except Exception as e:
            logger.error("crypto_error", error=str(e))
            return json.dumps({"error": str(e)})

    def _run(
        self,
        action: str,
        ids: str = "",
        query: str = "",
        limit: int = 20,
        days: int = 30,
        currency: str = "usd",
    ) -> str:
        return asyncio.get_event_loop().run_until_complete(
            self._arun(action, ids, query, limit, days, currency)
        )
