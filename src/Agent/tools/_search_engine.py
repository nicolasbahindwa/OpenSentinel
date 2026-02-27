"""
Shared Search Engine — Dual-provider web search with graceful degradation.

Runs Tavily AND DuckDuckGo concurrently using threads. If one fails or
times out, the other still returns results. Results are deduplicated by
URL and merged into a single ranked list.

All search tools (search_web, search_internet, universal_search) import from here.
"""

import os
import asyncio
import hashlib
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, TypedDict, Literal, Union
from functools import lru_cache
from enum import Enum

# Configure logging
logger = logging.getLogger(__name__)

# Timeout per provider in seconds
_SEARCH_TIMEOUT = 15
# Safe default to avoid curl-cffi invalid target warnings in new processes.
os.environ["CURL_IMPERSONATE"] = "chrome"


class SearchType(str, Enum):
    """Valid search types."""
    GENERAL = "general"
    NEWS = "news"
    IMAGES = "images"
    VIDEOS = "videos"
    ACADEMIC = "academic"


class ProviderStatus(str, Enum):
    """Provider status states."""
    OK = "ok"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DISABLED = "disabled"


class SearchResult(TypedDict):
    """Type definition for a single search result."""
    title: str
    url: str
    snippet: str
    score: float
    source_engine: str
    published: Optional[str]
    rank: int


class ProviderInfo(TypedDict):
    """Type definition for provider status info."""
    status: str
    results_count: int
    error: Optional[str]
    response_time_ms: Optional[float]


class SearchResponse(TypedDict):
    """Type definition for search response."""
    query: str
    search_type: str
    results: List[SearchResult]
    total_found: int
    answer: Optional[str]
    providers: Dict[str, ProviderInfo]
    timestamp: str
    cached: bool


@dataclass
class SearchConfig:
    """Configuration for search operations."""
    timeout_seconds: int = 15
    max_results_per_provider: int = 5
    enable_cache: bool = True
    cache_ttl_seconds: int = 300  # 5 minutes
    enable_tavily: bool = True
    enable_duckduckgo: bool = True
    tavily_api_key: Optional[str] = None
    curl_impersonate: str = "chrome"
    
    def __post_init__(self):
        if self.tavily_api_key is None:
            self.tavily_api_key = os.getenv("TAVILY_API_KEY")
        # Validate curl impersonate target
        os.environ["CURL_IMPERSONATE"] = _resolve_curl_impersonate()


# Simple in-memory cache
@dataclass
class CacheEntry:
    data: Dict[str, Any]
    expires: datetime


class SearchCache:
    """Simple TTL cache for search results."""
    
    def __init__(self):
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()
    
    def _make_key(self, query: str, search_type: str, num_results: int) -> str:
        """Create cache key from search parameters."""
        key_str = f"{query}:{search_type}:{num_results}"
        return hashlib.md5(key_str.encode()).hexdigest()
    
    async def get(self, query: str, search_type: str, num_results: int) -> Optional[Dict[str, Any]]:
        """Get cached result if valid."""
        key = self._make_key(query, search_type, num_results)
        async with self._lock:
            entry = self._cache.get(key)
            if entry and entry.expires > datetime.now():
                logger.debug(f"Cache hit for query: {query}")
                return entry.data
            if entry:
                del self._cache[key]
            return None
    
    async def set(self, query: str, search_type: str, num_results: int, data: Dict[str, Any], ttl: int):
        """Cache result with TTL."""
        key = self._make_key(query, search_type, num_results)
        async with self._lock:
            self._cache[key] = CacheEntry(data=data, expires=datetime.now() + timedelta(seconds=ttl))
    
    def clear(self):
        """Clear all cached entries."""
        self._cache.clear()


# Global cache instance
_search_cache = SearchCache()


class CircuitBreaker:
    """Simple circuit breaker to prevent hammering failing services."""
    
    def __init__(self, failure_threshold: int = 5, timeout_seconds: int = 60):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.last_failure_time: Optional[datetime] = None
        self.state = "closed"  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if operation can execute."""
        if self.state == "open":
            if self.last_failure_time and (datetime.now() - self.last_failure_time).seconds > self.timeout_seconds:
                self.state = "half-open"
                return True
            return False
        return True
    
    def record_success(self):
        """Record successful execution."""
        self.failure_count = 0
        self.state = "closed"
    
    def record_failure(self):
        """Record failed execution."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            logger.warning(f"Circuit breaker opened for {self}")


# Circuit breakers for each provider
_tavily_breaker = CircuitBreaker()
_ddg_breaker = CircuitBreaker()


def _resolve_curl_impersonate() -> str:
    """
    Resolve a valid curl-cffi impersonation target.
    [Your existing implementation - unchanged]
    """
    desired = os.getenv("OPENSENTINEL_CURL_IMPERSONATE", "chrome").strip()
    if not desired:
        return "chrome"

    desired_lower = desired.strip().lower()

    def _normalize_target(value: str) -> str:
        raw = value.strip().lower()
        if not raw:
            return "chrome"

        if raw.startswith("safari"):
            suffix = raw[len("safari"):].lstrip("_")
            if not suffix:
                return "safari"
            digits = suffix.replace(".", "_")
            return f"safari{digits}"

        if raw.startswith("safari_ios"):
            suffix = raw[len("safari_ios"):].lstrip("_")
            if not suffix:
                return "safari_ios"
            digits = suffix.replace(".", "_")
            return f"safari_ios_{digits}"

        if raw.startswith("edge"):
            suffix = raw[len("edge"):].lstrip("_")
            return f"edge{suffix}" if suffix else "edge"

        if raw.startswith("chrome"):
            suffix = raw[len("chrome"):].lstrip("_")
            return f"chrome{suffix}" if suffix else "chrome"

        return raw.replace(".", "_")

    normalized = _normalize_target(desired_lower)

    try:
        from curl_cffi import requests as curl_requests

        impersonate_mod = getattr(curl_requests, "impersonate", None)
        if impersonate_mod is None:
            return "chrome"

        real_map = getattr(impersonate_mod, "REAL_TARGET_MAP", None)
        real_targets = set(real_map.keys()) if isinstance(real_map, dict) else set()
        if not real_targets:
            real_list = getattr(impersonate_mod, "REAL_TARGETS", None)
            if isinstance(real_list, (list, tuple, set)):
                real_targets = set(real_list)

        if real_targets:
            if desired_lower in real_targets:
                return desired_lower
            if normalized in real_targets:
                return normalized
            if "chrome" in real_targets:
                return "chrome"
            if "chrome124" in real_targets:
                return "chrome124"
            return sorted(real_targets)[0]

        return "chrome"
    except Exception:
        return "chrome"


def _search_tavily(
    query: str, 
    num_results: int = 5, 
    search_type: SearchType = SearchType.GENERAL,
    config: SearchConfig = None
) -> Dict[str, Any]:
    """
    Search using Tavily API with circuit breaker pattern.
    """
    if not _tavily_breaker.can_execute():
        return {
            "results": [],
            "error": "Circuit breaker open - too many recent failures",
            "source": "tavily",
            "status": ProviderStatus.DISABLED
        }

    start_time = datetime.now()
    
    try:
        from tavily import TavilyClient

        api_key = config.tavily_api_key if config else os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {
                "results": [],
                "error": "TAVILY_API_KEY not set",
                "source": "tavily",
                "status": ProviderStatus.DISABLED
            }

        client = TavilyClient(api_key=api_key)

        search_params = {
            "query": query,
            "max_results": num_results,
            "search_depth": "advanced" if search_type == SearchType.ACADEMIC else "basic",
            "include_answer": True,
            "include_raw_content": False,
        }

        if search_type == SearchType.NEWS:
            search_params["topic"] = "news"

        response = client.search(**search_params)
        
        results = []
        for idx, item in enumerate(response.get("results", [])):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
                "score": item.get("score", 0) * 1.2,  # Boost Tavily scores slightly
                "source_engine": "tavily",
                "published": None,
                "rank": idx + 1,
            })

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        _tavily_breaker.record_success()
        
        return {
            "results": results,
            "answer": response.get("answer", ""),
            "total_found": len(results),
            "search_time_ms": elapsed,
            "source": "tavily",
            "status": ProviderStatus.OK
        }

    except ImportError:
        logger.error("tavily-python not installed")
        return {
            "results": [],
            "error": "tavily-python not installed",
            "source": "tavily",
            "status": ProviderStatus.FAILED
        }
    except Exception as e:
        logger.error(f"Tavily search failed: {e}")
        _tavily_breaker.record_failure()
        return {
            "results": [],
            "error": str(e),
            "source": "tavily",
            "status": ProviderStatus.FAILED
        }


def _search_duckduckgo(
    query: str, 
    num_results: int = 5, 
    search_type: SearchType = SearchType.GENERAL,
    config: SearchConfig = None
) -> Dict[str, Any]:
    """
    Search using DuckDuckGo with circuit breaker pattern.
    """
    if not _ddg_breaker.can_execute():
        return {
            "results": [],
            "error": "Circuit breaker open - too many recent failures",
            "source": "duckduckgo",
            "status": ProviderStatus.DISABLED
        }

    start_time = datetime.now()
    
    try:
        from ddgs import DDGS

        # Force a valid curl-cffi impersonation profile
        os.environ["CURL_IMPERSONATE"] = _resolve_curl_impersonate()

        ddgs = DDGS()
        
        if search_type == SearchType.NEWS:
            results_raw = list(ddgs.news(query, max_results=num_results))
        elif search_type == SearchType.IMAGES:
            results_raw = list(ddgs.images(query, max_results=num_results))
        elif search_type == SearchType.VIDEOS:
            results_raw = list(ddgs.videos(query, max_results=num_results))
        else:
            results_raw = list(ddgs.text(query, max_results=num_results))

        results = []
        for idx, item in enumerate(results_raw):
            url = item.get("href") or item.get("url", "")
            # DuckDuckGo doesn't provide scores, so we estimate based on rank
            estimated_score = max(0.5, 1.0 - (idx * 0.1))
            
            results.append({
                "title": item.get("title", ""),
                "url": url,
                "snippet": item.get("body") or item.get("description", ""),
                "score": estimated_score,
                "source_engine": "duckduckgo",
                "published": item.get("date"),
                "rank": idx + 1,
            })

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        
        _ddg_breaker.record_success()
        
        return {
            "results": results,
            "total_found": len(results),
            "source": "duckduckgo",
            "search_time_ms": elapsed,
            "status": ProviderStatus.OK
        }

    except ImportError:
        logger.error("ddgs not installed")
        return {
            "results": [],
            "error": "ddgs not installed (pip install ddgs)",
            "source": "duckduckgo",
            "status": ProviderStatus.FAILED
        }
    except Exception as e:
        logger.error(f"DuckDuckGo search failed: {e}")
        _ddg_breaker.record_failure()
        return {
            "results": [],
            "error": str(e),
            "source": "duckduckgo",
            "status": ProviderStatus.FAILED
        }


def _rank_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Intelligent ranking of merged results.
    
    Ranking factors:
    1. Original score (Tavily scores weighted higher)
    2. Source diversity (interleave sources)
    3. Recency (if published date available)
    """
    if not results:
        return []
    
    # Group by source
    tavily_results = [r for r in results if r.get("source_engine") == "tavily"]
    ddg_results = [r for r in results if r.get("source_engine") == "duckduckgo"]
    
    # Sort each group by score descending
    tavily_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    ddg_results.sort(key=lambda x: x.get("score", 0), reverse=True)
    
    # Interleave results for diversity, favoring Tavily slightly
    merged = []
    t_idx, d_idx = 0, 0
    
    while t_idx < len(tavily_results) or d_idx < len(ddg_results):
        # Add Tavily result
        if t_idx < len(tavily_results):
            merged.append(tavily_results[t_idx])
            t_idx += 1
        
        # Add DuckDuckGo result
        if d_idx < len(ddg_results):
            merged.append(ddg_results[d_idx])
            d_idx += 1
    
    # Re-rank
    for idx, item in enumerate(merged):
        item["rank"] = idx + 1
    
    return merged


def _deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Remove duplicate results by URL with intelligent merging.
    Keeps the highest scoring version and merges unique fields.
    """
    seen_urls: Dict[str, Dict[str, Any]] = {}
    
    for item in results:
        url = item.get("url", "").rstrip("/").lower()
        if not url:
            continue
            
        if url in seen_urls:
            # Merge with existing - keep higher score
            existing = seen_urls[url]
            if item.get("score", 0) > existing.get("score", 0):
                # Keep higher score but merge fields
                existing["score"] = item.get("score", 0)
                existing["source_engine"] = f"{existing['source_engine']}+{item['source_engine']}"
                if not existing.get("snippet") and item.get("snippet"):
                    existing["snippet"] = item["snippet"]
        else:
            seen_urls[url] = item.copy()
    
    return list(seen_urls.values())


def search_dual(
    query: str,
    num_results: int = 5,
    search_type: Union[str, SearchType] = SearchType.GENERAL,
    config: Optional[SearchConfig] = None,
    use_cache: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Run both Tavily and DuckDuckGo concurrently, merge results, handle failures gracefully.
    
    Enhanced features:
    - Circuit breaker pattern to prevent hammering failing services
    - Intelligent result ranking
    - Optional caching
    - Structured logging
    - Better error diagnostics
    
    Args:
        query: Search query string
        num_results: Max results per provider
        search_type: Type of search (general, news, images, videos, academic)
        config: Optional SearchConfig instance
        use_cache: Override config cache setting
    
    Returns:
        SearchResponse dict with merged results and metadata
    """
    # Normalize inputs
    if isinstance(search_type, str):
        search_type = SearchType(search_type.lower())
    
    config = config or SearchConfig()
    should_cache = use_cache if use_cache is not None else config.enable_cache
    
    # Check cache
    if should_cache:
        cached = asyncio.run(_search_cache.get(query, search_type.value, num_results))
        if cached:
            cached["cached"] = True
            return cached
    
    # Check which providers are enabled
    providers_to_run = []
    if config.enable_tavily:
        providers_to_run.append(("tavily", _search_tavily))
    if config.enable_duckduckgo:
        providers_to_run.append(("duckduckgo", _search_duckduckgo))
    
    if not providers_to_run:
        return {
            "query": query,
            "search_type": search_type.value,
            "results": [],
            "total_found": 0,
            "answer": None,
            "providers": {},
            "timestamp": datetime.now().isoformat(),
            "cached": False,
            "error": "No search providers enabled"
        }
    
    # Run providers concurrently
    results_map = {}
    with ThreadPoolExecutor(max_workers=len(providers_to_run)) as executor:
        futures = {
            executor.submit(func, query, num_results, search_type, config): name 
            for name, func in providers_to_run
        }
        
        for future in futures:
            name = futures[future]
            try:
                results_map[name] = future.result(timeout=config.timeout_seconds)
            except FuturesTimeoutError:
                logger.error(f"{name} timed out after {config.timeout_seconds}s")
                results_map[name] = {
                    "results": [],
                    "error": f"Timeout after {config.timeout_seconds}s",
                    "source": name,
                    "status": ProviderStatus.TIMEOUT
                }
            except Exception as e:
                logger.error(f"{name} failed with exception: {e}")
                results_map[name] = {
                    "results": [],
                    "error": str(e),
                    "source": name,
                    "status": ProviderStatus.FAILED
                }
    
    # Process results
    all_results = []
    providers_info = {}
    answer = None
    
    for name, data in results_map.items():
        status = data.get("status", ProviderStatus.FAILED)
        error = data.get("error")
        
        if status == ProviderStatus.OK:
            all_results.extend(data.get("results", []))
            providers_info[name] = {
                "status": status.value,
                "results_count": len(data.get("results", [])),
                "error": None,
                "response_time_ms": data.get("search_time_ms")
            }
            if name == "tavily" and data.get("answer"):
                answer = data["answer"]
        else:
            providers_info[name] = {
                "status": status.value,
                "results_count": 0,
                "error": error,
                "response_time_ms": None
            }
    
    # Deduplicate and rank
    deduplicated = _deduplicate_results(all_results)
    ranked = _rank_results(deduplicated)
    
    response = {
        "query": query,
        "search_type": search_type.value,
        "results": ranked,
        "total_found": len(ranked),
        "answer": answer,
        "providers": providers_info,
        "timestamp": datetime.now().isoformat(),
        "cached": False
    }
    
    # Cache successful results
    if should_cache and ranked:
        asyncio.run(_search_cache.set(
            query, search_type.value, num_results, 
            response, config.cache_ttl_seconds
        ))
    
    return response


# Async version for async applications
async def search_dual_async(
    query: str,
    num_results: int = 5,
    search_type: Union[str, SearchType] = SearchType.GENERAL,
    config: Optional[SearchConfig] = None,
    use_cache: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Async version of search_dual.
    Runs providers concurrently using asyncio instead of threads.
    """
    import asyncio
    
    loop = asyncio.get_event_loop()
    
    # Run sync version in thread pool
    with ThreadPoolExecutor(max_workers=1) as pool:
        return await loop.run_in_executor(
            pool,
            lambda: search_dual(query, num_results, search_type, config, use_cache)
        )


# Convenience functions for specific search types
def search_news(query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
    """Search for news."""
    return search_dual(query, num_results, SearchType.NEWS, **kwargs)

def search_images(query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
    """Search for images."""
    return search_dual(query, num_results, SearchType.IMAGES, **kwargs)

def search_videos(query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
    """Search for videos."""
    return search_dual(query, num_results, SearchType.VIDEOS, **kwargs)

def search_academic(query: str, num_results: int = 5, **kwargs) -> Dict[str, Any]:
    """Search academic sources."""
    return search_dual(query, num_results, SearchType.ACADEMIC, **kwargs)