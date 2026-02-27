"""
Shared Search Engine — Dual-provider web search with graceful degradation.

Runs Tavily AND DuckDuckGo concurrently using threads. If one fails or
times out, the other still returns results. Results are deduplicated by
URL and merged into a single ranked list.

All search tools (search_web, search_internet, universal_search) import from here.
"""

import os
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from datetime import datetime
from typing import List, Dict, Any

# Timeout per provider in seconds
_SEARCH_TIMEOUT = 15


def _resolve_curl_impersonate() -> str:
    """
    Resolve a valid curl-cffi impersonation target.

    Priority:
    1) OPENSENTINEL_CURL_IMPERSONATE env var
    2) fallback default "chrome124"

    Also normalizes common invalid forms like "edge_131" -> "edge131".
    """
    desired = os.getenv("OPENSENTINEL_CURL_IMPERSONATE", "chrome124").strip()
    if not desired:
        return "chrome124"

    # Common typo/format mismatch:
    # edge_131 -> edge131, chrome_124 -> chrome124, safari_17.0 -> safari170
    normalized = desired
    if "_" in desired:
        normalized = desired.replace("_", "")
    if "." in normalized:
        normalized = normalized.replace(".", "")

    try:
        from curl_cffi import requests as curl_requests

        impersonate_mod = getattr(curl_requests, "impersonate", None)
        if impersonate_mod is None:
            return "chrome124"

        real_map = getattr(impersonate_mod, "REAL_TARGET_MAP", None)
        real_targets = set(real_map.keys()) if isinstance(real_map, dict) else set()
        if not real_targets:
            real_list = getattr(impersonate_mod, "REAL_TARGETS", None)
            if isinstance(real_list, (list, tuple, set)):
                real_targets = set(real_list)

        if real_targets:
            if desired in real_targets:
                return desired
            if normalized in real_targets:
                return normalized
            if "chrome124" in real_targets:
                return "chrome124"
            return sorted(real_targets)[0]

        # If we cannot introspect supported targets, use a known-stable default.
        return "chrome124"
    except Exception:
        # If curl_cffi is unavailable here, use a known-stable default.
        return "chrome124"


def _search_tavily(query: str, num_results: int = 5, search_type: str = "general") -> Dict[str, Any]:
    """
    Search using Tavily API.

    Returns dict with results and metadata, or error dict if unavailable.
    Never raises — all failures are captured in the return value.
    """
    try:
        from tavily import TavilyClient

        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {"results": [], "error": "TAVILY_API_KEY not set", "source": "tavily"}

        client = TavilyClient(api_key=api_key)

        search_params = {
            "query": query,
            "max_results": num_results,
            "search_depth": "advanced" if search_type == "academic" else "basic",
            "include_answer": True,
            "include_raw_content": False,
        }

        if search_type == "news":
            search_params["topic"] = "news"

        response = client.search(**search_params)

        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0),
                "source_engine": "tavily",
            })

        return {
            "results": results,
            "answer": response.get("answer", ""),
            "total_found": len(results),
            "search_time_ms": response.get("response_time", 0) * 1000,
            "source": "tavily",
        }

    except ImportError:
        return {"results": [], "error": "tavily-python not installed", "source": "tavily"}
    except Exception as e:
        return {"results": [], "error": str(e), "source": "tavily"}


def _search_duckduckgo(query: str, num_results: int = 5, search_type: str = "general") -> Dict[str, Any]:
    """
    Search using DuckDuckGo.

    Returns dict with results and metadata, or error dict if unavailable.
    Never raises — all failures are captured in the return value.
    """
    try:
        from ddgs import DDGS

        # Force a valid curl-cffi impersonation profile and avoid fallback warnings
        # like "Impersonate 'edge_131' does not exist, using 'random'".
        os.environ["CURL_IMPERSONATE"] = _resolve_curl_impersonate()

        ddgs = DDGS()
        if search_type == "news":
            results_raw = list(ddgs.news(query, max_results=num_results))
        elif search_type == "images":
            results_raw = list(ddgs.images(query, max_results=num_results))
        elif search_type == "videos":
            results_raw = list(ddgs.videos(query, max_results=num_results))
        else:
            results_raw = list(ddgs.text(query, max_results=num_results))

        results = []
        for item in results_raw:
            url = item.get("href") or item.get("url", "")
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("body") or item.get("description", ""),
                "published": item.get("date", ""),
                "source_engine": "duckduckgo",
            })

        return {
            "results": results,
            "total_found": len(results),
            "source": "duckduckgo",
        }

    except ImportError:
        return {"results": [], "error": "ddgs not installed (pip install ddgs)", "source": "duckduckgo"}
    except Exception as e:
        return {"results": [], "error": str(e), "source": "duckduckgo"}


def _deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove duplicate results by URL, keeping the first occurrence (higher priority)."""
    seen_urls = set()
    unique = []
    for item in results:
        url = item.get("url", "").rstrip("/").lower()
        if url and url in seen_urls:
            continue
        if url:
            seen_urls.add(url)
        unique.append(item)
    return unique


def search_dual(
    query: str,
    num_results: int = 5,
    search_type: str = "general",
) -> Dict[str, Any]:
    """
    Run both Tavily and DuckDuckGo concurrently, merge results, handle failures gracefully.

    - If both succeed: results are merged and deduplicated
    - If one fails or times out: the other's results are returned
    - If both fail: an error response with diagnostics is returned

    Each provider has a 15-second timeout to prevent hanging.

    Args:
        query: Search query string
        num_results: Max results per provider (total may be up to 2x after merge)
        search_type: Type of search (general, news, images, videos, academic)

    Returns:
        Dict with merged results, provider status, and metadata
    """
    # Run both providers concurrently with timeout
    with ThreadPoolExecutor(max_workers=2) as executor:
        tavily_future = executor.submit(_search_tavily, query, num_results, search_type)
        ddg_future = executor.submit(_search_duckduckgo, query, num_results, search_type)

        try:
            tavily_data = tavily_future.result(timeout=_SEARCH_TIMEOUT)
        except FuturesTimeoutError:
            tavily_data = {"results": [], "error": f"Tavily timed out after {_SEARCH_TIMEOUT}s", "source": "tavily"}
        except Exception as e:
            tavily_data = {"results": [], "error": str(e), "source": "tavily"}

        try:
            ddg_data = ddg_future.result(timeout=_SEARCH_TIMEOUT)
        except FuturesTimeoutError:
            ddg_data = {"results": [], "error": f"DuckDuckGo timed out after {_SEARCH_TIMEOUT}s", "source": "duckduckgo"}
        except Exception as e:
            ddg_data = {"results": [], "error": str(e), "source": "duckduckgo"}

    tavily_ok = not tavily_data.get("error")
    ddg_ok = not ddg_data.get("error")

    # Merge results: Tavily first (higher quality scores), then DuckDuckGo
    merged = tavily_data.get("results", []) + ddg_data.get("results", [])
    deduplicated = _deduplicate_results(merged)

    # Build provider status
    providers = {}
    if tavily_ok:
        providers["tavily"] = {"status": "ok", "results_count": len(tavily_data.get("results", []))}
    else:
        providers["tavily"] = {"status": "failed", "error": tavily_data.get("error", "unknown")}

    if ddg_ok:
        providers["duckduckgo"] = {"status": "ok", "results_count": len(ddg_data.get("results", []))}
    else:
        providers["duckduckgo"] = {"status": "failed", "error": ddg_data.get("error", "unknown")}

    return {
        "query": query,
        "search_type": search_type,
        "results": deduplicated,
        "total_found": len(deduplicated),
        "answer": tavily_data.get("answer", ""),
        "providers": providers,
        "timestamp": datetime.now().isoformat(),
    }
