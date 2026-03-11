"""Yahoo Finance tool using the yfinance library.

Provides stock quotes, historical data, company profiles, multiple quotes,
trending stocks, and market indices overview.
No API key required.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import ClassVar, Type

from cachetools import TTLCache
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.yahoo_finance", component="yahoo_finance")


# =============================================================================
# Input Schema
# =============================================================================


class YahooFinanceInput(BaseModel):
    action: str = Field(
        ...,
        description=(
            "Action to perform: "
            "'quote' — current stock quote with price/change/volume, "
            "'quotes' — multiple stock quotes at once, "
            "'historical' — OHLCV price history, "
            "'search' — search for ticker symbols, "
            "'summary' — detailed company profile and financials, "
            "'market' — major market indices overview."
        ),
    )
    symbol: str = Field(default="", description="Stock ticker symbol (e.g., 'AAPL', 'MSFT', 'TSLA').")
    symbols: str = Field(
        default="",
        description="Comma-separated ticker symbols for 'quotes' (e.g., 'AAPL,MSFT,GOOGL').",
    )
    query: str = Field(default="", description="Company name or partial symbol for 'search' action.")
    period: str = Field(
        default="1mo",
        description="Time period for 'historical': 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y (default: 1mo).",
    )
    interval: str = Field(
        default="1d",
        description="Data interval for 'historical': 1d, 1wk, 1mo (default: 1d).",
    )
    limit: int = Field(default=5, ge=1, le=20, description="Max results for 'search' (default: 5).")


# =============================================================================
# Tool Implementation
# =============================================================================


class YahooFinanceTool(BaseTool):
    name: str = "yahoo_finance"
    description: str = (
        "Get stock market data: quotes, historical prices, company profiles, "
        "and market indices. Uses Yahoo Finance (no API key required).\n\n"
        "Examples:\n"
        "- Stock quote: action='quote', symbol='AAPL'\n"
        "- Multiple quotes: action='quotes', symbols='AAPL,MSFT,GOOGL'\n"
        "- Historical data: action='historical', symbol='AAPL', period='3mo', interval='1d'\n"
        "- Search ticker: action='search', query='Tesla'\n"
        "- Company profile: action='summary', symbol='AAPL'\n"
        "- Market overview: action='market'"
    )
    args_schema: Type[BaseModel] = YahooFinanceInput
    handle_tool_error: bool = True

    _cache: TTLCache = PrivateAttr()

    MAX_CONTENT_CHARS: ClassVar[int] = 3000

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cache = TTLCache(maxsize=200, ttl=300)  # 5 min cache

    def _get_quote(self, symbol: str) -> str:
        import yfinance as yf

        if not symbol:
            return json.dumps({"error": "Provide a stock symbol (e.g., symbol='AAPL')"})

        cache_key = f"quote:{symbol.upper()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info or "regularMarketPrice" not in info:
            # Try fast_info as fallback
            try:
                fast = ticker.fast_info
                result = json.dumps({
                    "symbol": symbol.upper(),
                    "price": getattr(fast, "last_price", None),
                    "previous_close": getattr(fast, "previous_close", None),
                    "market_cap": getattr(fast, "market_cap", None),
                    "currency": getattr(fast, "currency", None),
                }, indent=2)
                self._cache[cache_key] = result
                return result
            except Exception:
                return json.dumps({"error": f"No data found for '{symbol.upper()}'"})

        result = json.dumps({
            "symbol": info.get("symbol", symbol.upper()),
            "name": info.get("shortName") or info.get("longName"),
            "price": info.get("regularMarketPrice") or info.get("currentPrice"),
            "change": info.get("regularMarketChange"),
            "change_percent": info.get("regularMarketChangePercent"),
            "previous_close": info.get("regularMarketPreviousClose") or info.get("previousClose"),
            "open": info.get("regularMarketOpen") or info.get("open"),
            "day_high": info.get("regularMarketDayHigh") or info.get("dayHigh"),
            "day_low": info.get("regularMarketDayLow") or info.get("dayLow"),
            "volume": info.get("regularMarketVolume") or info.get("volume"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "eps": info.get("trailingEps"),
            "dividend_yield": info.get("dividendYield"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
            "exchange": info.get("exchange"),
            "currency": info.get("currency"),
        }, indent=2)

        self._cache[cache_key] = result
        return result

    def _get_quotes(self, symbols: str) -> str:
        import yfinance as yf

        if not symbols:
            return json.dumps({"error": "Provide symbols (e.g., symbols='AAPL,MSFT,GOOGL')"})

        symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
        quotes = []

        for sym in symbol_list:
            try:
                ticker = yf.Ticker(sym)
                info = ticker.info
                quotes.append({
                    "symbol": sym,
                    "name": info.get("shortName"),
                    "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                    "change": info.get("regularMarketChange"),
                    "change_percent": info.get("regularMarketChangePercent"),
                    "volume": info.get("regularMarketVolume") or info.get("volume"),
                    "market_cap": info.get("marketCap"),
                })
            except Exception:
                quotes.append({"symbol": sym, "error": "Failed to fetch"})

        return json.dumps({"count": len(quotes), "quotes": quotes}, indent=2)

    def _get_historical(self, symbol: str, period: str, interval: str) -> str:
        import yfinance as yf

        if not symbol:
            return json.dumps({"error": "Provide a stock symbol (e.g., symbol='AAPL')"})

        cache_key = f"hist:{symbol.upper()}:{period}:{interval}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = yf.Ticker(symbol.upper())
        hist = ticker.history(period=period, interval=interval)

        if hist.empty:
            return json.dumps({"error": f"No historical data for '{symbol.upper()}'"})

        quotes = []
        for date, row in hist.iterrows():
            quotes.append({
                "date": str(date.date()) if hasattr(date, "date") else str(date),
                "open": round(row.get("Open", 0), 2),
                "high": round(row.get("High", 0), 2),
                "low": round(row.get("Low", 0), 2),
                "close": round(row.get("Close", 0), 2),
                "volume": int(row.get("Volume", 0)),
            })

        closes = [q["close"] for q in quotes if q["close"]]
        first_close = closes[0] if closes else None
        last_close = closes[-1] if closes else None
        change = ((last_close - first_close) / first_close * 100) if first_close and last_close else None

        result = json.dumps({
            "symbol": symbol.upper(),
            "period": period,
            "interval": interval,
            "data_points": len(quotes),
            "summary": {
                "start_price": first_close,
                "end_price": last_close,
                "change": f"{change:.2f}%" if change is not None else None,
                "high": max(closes) if closes else None,
                "low": min(closes) if closes else None,
            },
            "quotes": quotes,
        }, indent=2)

        self._cache[cache_key] = result
        return result

    def _search(self, query: str, limit: int) -> str:
        import yfinance as yf

        if not query:
            return json.dumps({"error": "Provide a search query (e.g., query='Apple')"})

        # yfinance doesn't have a direct search API, use Ticker to validate
        # For search, we use a workaround with yfinance's search
        try:
            tickers = yf.Tickers(query)
            # Try simple lookup
            ticker = yf.Ticker(query.upper())
            info = ticker.info
            if info and info.get("symbol"):
                return json.dumps({
                    "query": query,
                    "count": 1,
                    "results": [{
                        "symbol": info.get("symbol"),
                        "name": info.get("shortName") or info.get("longName"),
                        "type": info.get("quoteType"),
                        "exchange": info.get("exchange"),
                        "industry": info.get("industry"),
                    }],
                }, indent=2)
        except Exception:
            pass

        return json.dumps({
            "query": query,
            "count": 0,
            "results": [],
            "hint": "Try using the exact ticker symbol (e.g., 'AAPL' for Apple, 'TSLA' for Tesla).",
        }, indent=2)

    def _get_summary(self, symbol: str) -> str:
        import yfinance as yf

        if not symbol:
            return json.dumps({"error": "Provide a stock symbol (e.g., symbol='AAPL')"})

        cache_key = f"summary:{symbol.upper()}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        ticker = yf.Ticker(symbol.upper())
        info = ticker.info

        if not info:
            return json.dumps({"error": f"No data found for '{symbol.upper()}'"})

        result = json.dumps({
            "symbol": symbol.upper(),
            "company": {
                "name": info.get("longName"),
                "summary": (info.get("longBusinessSummary") or "")[:500],
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "website": info.get("website"),
                "employees": info.get("fullTimeEmployees"),
                "country": info.get("country"),
                "city": info.get("city"),
            },
            "valuation": {
                "market_cap": info.get("marketCap"),
                "enterprise_value": info.get("enterpriseValue"),
                "pe_ratio": info.get("trailingPE"),
                "forward_pe": info.get("forwardPE"),
                "peg_ratio": info.get("pegRatio"),
                "price_to_book": info.get("priceToBook"),
            },
            "financials": {
                "revenue": info.get("totalRevenue"),
                "revenue_per_share": info.get("revenuePerShare"),
                "gross_margin": info.get("grossMargins"),
                "operating_margin": info.get("operatingMargins"),
                "profit_margin": info.get("profitMargins"),
                "return_on_equity": info.get("returnOnEquity"),
                "debt_to_equity": info.get("debtToEquity"),
            },
            "dividend": {
                "yield": info.get("dividendYield"),
                "rate": info.get("dividendRate"),
                "payout_ratio": info.get("payoutRatio"),
                "ex_date": info.get("exDividendDate"),
            },
            "trading": {
                "beta": info.get("beta"),
                "50d_avg": info.get("fiftyDayAverage"),
                "200d_avg": info.get("twoHundredDayAverage"),
                "avg_volume": info.get("averageVolume"),
            },
        }, indent=2)

        self._cache[cache_key] = result
        return result

    def _get_market(self) -> str:
        import yfinance as yf

        indices = {
            "^GSPC": "S&P 500",
            "^DJI": "Dow Jones",
            "^IXIC": "Nasdaq",
            "^RUT": "Russell 2000",
            "^VIX": "VIX",
        }

        quotes = []
        for ticker_sym, name in indices.items():
            try:
                ticker = yf.Ticker(ticker_sym)
                info = ticker.info
                quotes.append({
                    "symbol": ticker_sym,
                    "name": name,
                    "price": info.get("regularMarketPrice") or info.get("currentPrice"),
                    "change": info.get("regularMarketChange"),
                    "change_percent": info.get("regularMarketChangePercent"),
                    "volume": info.get("regularMarketVolume") or info.get("volume"),
                })
            except Exception:
                quotes.append({"symbol": ticker_sym, "name": name, "error": "Failed to fetch"})

        return json.dumps({"count": len(quotes), "indices": quotes}, indent=2)

    # -------------------------------------------------------------------------
    # BaseTool interface
    # -------------------------------------------------------------------------

    def _run(
        self,
        action: str,
        symbol: str = "",
        symbols: str = "",
        query: str = "",
        period: str = "1mo",
        interval: str = "1d",
        limit: int = 5,
    ) -> str:
        logger.info("yahoo_finance_action", action=action, symbol=symbol)
        try:
            match action.lower():
                case "quote":
                    return self._get_quote(symbol)
                case "quotes":
                    return self._get_quotes(symbols)
                case "historical":
                    return self._get_historical(symbol, period, interval)
                case "search":
                    return self._search(query, limit)
                case "summary":
                    return self._get_summary(symbol)
                case "market":
                    return self._get_market()
                case _:
                    return json.dumps({
                        "error": f"Unknown action '{action}'. "
                        "Use: quote, quotes, historical, search, summary, market"
                    })
        except Exception as e:
            logger.error("yahoo_finance_error", error=str(e))
            return json.dumps({"error": str(e)})

    async def _arun(
        self,
        action: str,
        symbol: str = "",
        symbols: str = "",
        query: str = "",
        period: str = "1mo",
        interval: str = "1d",
        limit: int = 5,
    ) -> str:
        return await asyncio.to_thread(
            self._run, action, symbol, symbols, query, period, interval, limit
        )
