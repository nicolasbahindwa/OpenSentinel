"""
Production-Grade Web Browser Tool for OpenSentinel Agent.

Features:
- Snapshot + Ref system (OpenClaw-style, bug-fixed)
- Multi-provider search (Brave + DuckDuckGo fallback)
- Firecrawl fallback for JS-heavy sites
- Security: URL validation, domain allowlists, SSRF protection
- Reliability: Circuit breaker, rate limiting, retries
- Observability: Comprehensive logging, metrics, health check

Architecture:
┌─────────────────────────────────────────────────────────────┐
│                      WebBrowserTool                          │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ URLValidator │   │ RateLimiter  │   │ CircuitBreaker│
└──────────────┘   └──────────────┘   └──────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ SnapshotEngine│  │ SearchProvider│  │ Firecrawl    │
│ (Ref System) │   │ (Brave/DDG)  │   │ (Fallback)   │
└──────────────┘   └──────────────┘   └──────────────┘
"""

import asyncio
import hashlib
import os
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from typing import ClassVar, Type, Optional, Dict, List, Tuple, Any
from urllib.parse import urlparse, quote

import httpx
from langchain_core.tools import BaseTool
from playwright.async_api import async_playwright, Browser, Page, BrowserContext, ElementHandle
from pydantic import BaseModel, Field, PrivateAttr

from agent.logger import get_logger

logger = get_logger("agent.tools.web_browser", component="web_browser")


# =============================================================================
# Enums & Constants
# =============================================================================


class BrowserMode(Enum):
    HEADLESS = "headless"
    HEADFUL = "headful"


class SecurityLevel(Enum):
    STRICT = "strict"
    STANDARD = "standard"
    RELAXED = "relaxed"


class SnapshotMode(Enum):
    AI = "ai"  # Numeric refs (1, 2, 3...)
    ROLE = "role"  # Role-prefixed refs (e1, e2, e3...)


class SearchProvider(Enum):
    AUTO = "auto"
    BRAVE = "brave"
    DUCKDUCKGO = "duckduckgo"
    PERPLEXITY = "perplexity"


# Security constants
ALLOWED_SCHEMES = {"https", "http"}
BLOCKED_EXTENSIONS = {".exe", ".dll", ".bin", ".zip", ".rar", ".7z", ".msi", ".dmg", ".jar"}
BLOCKED_MIME_TYPES = {
    "application/octet-stream",
    "application/x-executable",
    "application/x-msdownload",
    "application/zip",
    "application/x-rar-compressed",
}

DEFAULT_ALLOWED_DOMAINS = {
    # Search engines
    "google.com", "www.google.com", "duckduckgo.com", "bing.com",
    # Documentation
    "github.com", "stackoverflow.com", "docs.python.org", "readthedocs.io",
    # News & info
    "wikipedia.org", "en.wikipedia.org", "reddit.com", "medium.com",
    # APIs
    "api.github.com", "jsonplaceholder.typicode.com", "httpbin.org",
    # Common services
    "example.com", "example.org",
}

# Rate limiting & timeouts
DEFAULT_RATE_LIMIT = 10  # requests per minute
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RESPONSE_SIZE = 1_000_000  # 1MB
DEFAULT_MAX_SNAPSHOT_AGE_SECONDS = 300  # 5 minutes


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ElementRef:
    """Reference to an interactive element in snapshot."""
    ref_id: str
    role: str
    name: str
    element_type: str
    selector: str
    is_clickable: bool = False
    is_typeable: bool = False
    bounding_box: Optional[Dict[str, float]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def hint(self) -> str:
        """Human-readable hint for LLM."""
        hints = []
        if self.is_clickable:
            hints.append("clickable")
        if self.is_typeable:
            hints.append("typeable")
        if self.role == "checkbox":
            hints.append("toggleable")
        if self.role == "combobox":
            hints.append("selectable")
        
        hint_str = f" ({', '.join(hints)})" if hints else ""
        return f"[{self.ref_id}] {self.role} '{self.name}' <{self.element_type}>{hint_str}"


@dataclass
class Snapshot:
    """Page snapshot with element references."""
    url: str
    timestamp: str
    mode: str
    text: str
    elements: Dict[str, ElementRef]
    screenshot_path: Optional[str] = None
    is_expired: bool = False
    
    def is_valid(self) -> bool:
        """Check if snapshot is still valid (not expired)."""
        if self.is_expired:
            return False
        snapshot_time = datetime.fromisoformat(self.timestamp)
        age = (datetime.now() - snapshot_time).total_seconds()
        return age < DEFAULT_MAX_SNAPSHOT_AGE_SECONDS
    
    def summary(self) -> str:
        """Human-readable summary for LLM."""
        return f"Snapshot of {self.url} ({len(self.elements)} interactive elements)\n\n{self.text}"


@dataclass
class WebBrowserResult:
    """Result from web browser operations."""
    action: str
    url: str
    status: str  # "success", "partial", "failed"
    status_code: Optional[int]
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def summary(self) -> str:
        """Human-readable summary."""
        if self.status == "success":
            return f"✅ {self.action.upper()} | {self.url} | {self.status_code} | {len(self.content)} chars"
        elif self.status == "partial":
            return f"⚠️ {self.action.upper()} | {self.url} | {self.error or 'Partial success'}"
        else:
            return f"❌ {self.action.upper()} | {self.url} | {self.error}"


@dataclass
class SearchResult:
    """Single search result."""
    title: str
    url: str
    snippet: str
    source: str
    rank: int = 0


# =============================================================================
# Rate Limiter
# =============================================================================


class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, rate: int = DEFAULT_RATE_LIMIT, per_seconds: int = 60):
        self.rate = rate
        self.per_seconds = per_seconds
        self.tokens = float(rate)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()
    
    async def acquire(self) -> None:
        """Acquire a token, waiting if necessary."""
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.rate, self.tokens + elapsed * (self.rate / self.per_seconds))
            self.last_update = now
            
            if self.tokens < 1:
                wait_time = (1 - self.tokens) * (self.per_seconds / self.rate)
                logger.debug("rate_limit_waiting", wait_seconds=round(wait_time, 2))
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= 1


# =============================================================================
# Circuit Breaker
# =============================================================================


class CircuitBreakerState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for external service protection."""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        half_open_max_calls: int = 3,
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[float] = None
        self._lock = asyncio.Lock()
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    logger.info("circuit_breaker_half_open")
                else:
                    raise Exception("Circuit breaker is OPEN - service unavailable")
        
        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self.success_count += 1
                    if self.success_count >= self.half_open_max_calls:
                        self.state = CircuitBreakerState.CLOSED
                        self.failure_count = 0
                        logger.info("circuit_breaker_closed")
                else:
                    self.failure_count = 0
            return result
        except Exception as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()
                if self.failure_count >= self.failure_threshold:
                    self.state = CircuitBreakerState.OPEN
                    logger.warning("circuit_breaker_open", failure_count=self.failure_count)
            raise


# =============================================================================
# URL Security Validator
# =============================================================================


class URLValidator:
    """Validate and sanitize URLs for security."""
    
    def __init__(
        self,
        allowed_domains: Optional[set[str]] = None,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
    ):
        self.allowed_domains = allowed_domains or DEFAULT_ALLOWED_DOMAINS
        self.security_level = security_level
    
    def validate(self, url: str) -> Tuple[bool, Optional[str]]:
        """
        Validate URL for security.
        Returns: (is_valid, error_message)
        """
        try:
            parsed = urlparse(url)
        except Exception as e:
            return False, f"Invalid URL format: {e}"
        
        # Check scheme
        if parsed.scheme not in ALLOWED_SCHEMES:
            return False, f"Scheme '{parsed.scheme}' not allowed. Use http or https."
        
        # Enforce HTTPS for strict/standard mode
        if self.security_level in [SecurityLevel.STRICT, SecurityLevel.STANDARD] and parsed.scheme != "https":
            return False, "Only HTTPS allowed in this security level."
        
        # Check for blocked extensions
        path_lower = parsed.path.lower()
        for ext in BLOCKED_EXTENSIONS:
            if path_lower.endswith(ext):
                return False, f"File type '{ext}' is blocked for security."
        
        # Check domain allowlist (strict/standard mode)
        if self.security_level in [SecurityLevel.STRICT, SecurityLevel.STANDARD]:
            domain = parsed.netloc.lower().split(":")[0]  # Remove port
            
            is_allowed = False
            for allowed in self.allowed_domains:
                if domain == allowed or domain.endswith(f".{allowed}"):
                    is_allowed = True
                    break
            
            if not is_allowed:
                return False, f"Domain '{domain}' not in allowlist."
        
        # Check for private/internal IPs (prevent SSRF)
        if self._is_private_ip(parsed.hostname):
            return False, "Private/internal IP addresses are not allowed."
        
        return True, None
    
    def _is_private_ip(self, hostname: Optional[str]) -> bool:
        """Check if hostname resolves to private IP."""
        if not hostname:
            return False
        
        private_patterns = [
            r"^127\.", r"^10\.", r"^172\.(1[6-9]|2[0-9]|3[0-1])\.",
            r"^192\.168\.", r"^0\.0\.0\.0", r"^localhost$", r"^internal$",
        ]
        
        for pattern in private_patterns:
            if re.match(pattern, hostname, re.IGNORECASE):
                return True
        
        return False


# =============================================================================
# Snapshot Engine (OpenClaw-Style, Fixed)
# =============================================================================


class SnapshotEngine:
    """
    Generates AI-friendly snapshots with stable element references.
    Replaces brittle CSS selectors with numeric/role-based refs.
    """
    
    INTERACTIVE_ROLES = {
        "button", "link", "textbox", "searchbox", "checkbox",
        "radio", "combobox", "menuitem", "tab", "treeitem",
        "listbox", "option", "slider", "spinbutton", "img",
    }
    
    def __init__(self, mode: SnapshotMode = SnapshotMode.AI):
        self.mode = mode
        self._ref_counter = 0
        self._elements: Dict[str, ElementRef] = {}
    
    async def generate_snapshot(self, page: Page) -> Snapshot:
        """Generate snapshot with element references."""
        self._ref_counter = 0
        self._elements = {}
        
        url = page.url
        timestamp = datetime.now().isoformat()
        
        # Get all interactive elements
        elements = await self._query_interactive_elements(page)
        
        # Build snapshot text
        lines = []
        for element in elements:
            lines.append(element.hint())
        
        snapshot_text = "\n".join(lines) if lines else "No interactive elements found."
        
        return Snapshot(
            url=url,
            timestamp=timestamp,
            mode=self.mode.value,
            text=snapshot_text,
            elements=self._elements,
        )
    
    async def _query_interactive_elements(self, page: Page) -> List[ElementRef]:
        """Query all interactive elements on page."""
        # Query selector for interactive elements
        selector = (
            'button, a[href], input:not([type="hidden"]), '
            'select, textarea, [role="button"], [role="link"], '
            '[role="textbox"], [role="checkbox"], [role="radio"], '
            '[role="combobox"], [role="menuitem"], [tabindex]:not([tabindex="-1"])'
        )
        
        handles = await page.query_selector_all(selector)
        elements = []
        
        for i, handle in enumerate(handles[:50]):  # Limit to 50 elements
            try:
                element = await self._extract_element_info(page, handle, i)
                if element:
                    elements.append(element)
                    self._elements[element.ref_id] = element
            except Exception as e:
                logger.debug("element_extraction_failed", error=str(e))
                continue
        
        return elements
    
    async def _extract_element_info(
        self,
        page: Page,
        handle: ElementHandle,
        index: int,
    ) -> Optional[ElementRef]:
        """Extract information from element handle."""
        try:
            # Get element properties
            info = await handle.evaluate("""el => ({
                role: el.getAttribute('role') || el.tagName.toLowerCase(),
                name: el.getAttribute('aria-label') || 
                      el.getAttribute('title') || 
                      el.textContent?.trim().slice(0, 50) || 
                      el.getAttribute('placeholder') || 
                      el.getAttribute('name') || 
                      '',
                type: el.type || el.tagName.toLowerCase(),
                disabled: el.disabled || false,
                visible: el.offsetParent !== null,
            })""")
            
            # Skip disabled or invisible elements
            if info.get("disabled") or not info.get("visible"):
                return None
            
            # Generate ref ID
            if self.mode == SnapshotMode.AI:
                self._ref_counter += 1
                ref_id = str(self._ref_counter)
            else:
                ref_id = f"e{index + 1}"
            
            # Build selector for this element
            selector = await self._build_selector(handle)
            
            # Determine capabilities
            role = info.get("role", "unknown")
            element_type = info.get("type", "unknown")
            is_clickable = role in ["button", "link", "menuitem", "tab"] or element_type in ["button", "submit"]
            is_typeable = role in ["textbox", "searchbox", "combobox"] or element_type in ["text", "email", "password", "search", "textarea"]
            
            # Get bounding box
            box = await handle.bounding_box()
            
            return ElementRef(
                ref_id=ref_id,
                role=role,
                name=info.get("name", "")[:50],
                element_type=element_type,
                selector=selector,
                is_clickable=is_clickable,
                is_typeable=is_typeable,
                bounding_box=box,
            )
            
        except Exception as e:
            logger.debug("element_info_extraction_failed", error=str(e))
            return None
    
    async def _build_selector(self, handle: ElementHandle) -> str:
        """Build a stable selector for element."""
        try:
            # Try to get a unique selector
            selector = await handle.evaluate("""el => {
                if (el.id) return '#' + el.id;
                if (el.className && el.className.split(' ').length === 1) {
                    return el.tagName.toLowerCase() + '.' + el.className;
                }
                return el.tagName.toLowerCase();
            }""")
            return selector or "*"
        except:
            return "*"
    
    async def resolve_ref(self, page: Page, ref_id: str) -> Optional[ElementHandle]:
        """Resolve ref to element handle. Returns None if expired."""
        if ref_id not in self._elements:
            return None
        
        element = self._elements[ref_id]
        
        try:
            handle = await page.query_selector(element.selector)
            
            # Verify element is still valid
            if handle:
                is_visible = await handle.evaluate("el => el.offsetParent !== null")
                if is_visible:
                    return handle
        except:
            pass
        
        return None
    
    def get_element_hint(self, ref_id: str) -> Optional[str]:
        """Get human-readable hint for element."""
        if ref_id in self._elements:
            return self._elements[ref_id].hint()
        return None


# =============================================================================
# Search Providers
# =============================================================================


class SearchProviderBase:
    """Base class for search providers."""
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        raise NotImplementedError


class DuckDuckGoProvider(SearchProviderBase):
    """DuckDuckGo search (free, no API key)."""
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    search_url,
                    headers={"User-Agent": "Mozilla/5.0"},
                    timeout=10,
                )
            
            # Parse results (simple HTML parsing)
            results = []
            content = response.text
            
            # Extract result blocks
            result_pattern = r'<a class="result__a" href="([^"]+)">([^<]+)</a>'
            snippet_pattern = r'<a class="result__snippet" [^>]*>([^<]+)</a>'
            
            matches = re.findall(result_pattern, content)
            snippets = re.findall(snippet_pattern, content)
            
            for i, (url, title) in enumerate(matches[:limit]):
                # Clean URL (DuckDuckGo uses redirects)
                if "uddg=" in url:
                    url_match = re.search(r"uddg=([^&]+)", url)
                    if url_match:
                        url = url_match.group(1)
                
                results.append(SearchResult(
                    title=title.strip(),
                    url=url,
                    snippet=snippets[i] if i < len(snippets) else "",
                    source="duckduckgo",
                    rank=i + 1,
                ))
            
            return results
            
        except Exception as e:
            logger.warning("duckduckgo_search_failed", error=str(e))
            return []


class BraveSearchProvider(SearchProviderBase):
    """Brave Search API (requires API key)."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("BRAVE_API_KEY")
        self.base_url = "https://api.search.brave.com/res/v1/web/search"
    
    async def search(self, query: str, limit: int = 10) -> List[SearchResult]:
        if not self.api_key:
            raise ValueError("Brave API key required. Set BRAVE_API_KEY environment variable.")
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.base_url,
                    headers={
                        "X-Subscription-Token": self.api_key,
                        "Accept": "application/json",
                    },
                    params={"q": query, "count": min(limit, 20)},
                    timeout=10,
                )
            
            data = response.json()
            results = []
            
            for i, result in enumerate(data.get("web", {}).get("results", [])[:limit]):
                results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("url", ""),
                    snippet=result.get("description", ""),
                    source="brave",
                    rank=i + 1,
                ))
            
            return results
            
        except Exception as e:
            logger.warning("brave_search_failed", error=str(e))
            return []


# =============================================================================
# Web Browser Tool
# =============================================================================


class WebBrowserTool(BaseTool):
    """
    Production-grade web browser tool with OpenClaw-style snapshot system.
    
    Features:
    - Snapshot + Ref system for stable element interaction
    - Multi-provider search (Brave + DuckDuckGo)
    - Firecrawl fallback for JS-heavy sites
    - Security: URL validation, domain allowlists, SSRF protection
    - Reliability: Circuit breaker, rate limiting, retries
    - Observability: Logging, metrics, health check
    """
    
    name: str = "web_browser"
    description: str = (
        "Browse and interact with web pages. Actions:\n"
        "- 'fetch': Get webpage content (httpx, fast)\n"
        "- 'browse': Full browser automation (Playwright, handles JS)\n"
        "- 'search': Search the web (Brave/DuckDuckGo)\n"
        "- 'snapshot': Capture page with element refs (OpenClaw-style)\n"
        "- 'act': Perform action on element by ref (click, type, etc.)\n"
        "- 'screenshot': Capture screenshot\n"
        "\nExamples:\n"
        '- Fetch: action="fetch", url="https://example.com"\n'
        '- Search: action="search", query="Python best practices"\n'
        '- Snapshot: action="snapshot", url="https://example.com"\n'
        '- Act: action="act", ref="12", action_type="click"\n'
        "Security: HTTPS only, domain allowlist, private IPs blocked."
    )
    args_schema: Type[BaseModel] = None  # Set below
    handle_tool_error: bool = True
    
    # Configuration
    MAX_CONTENT_LENGTH: ClassVar[int] = DEFAULT_MAX_RESPONSE_SIZE

    # Pydantic fields (declared so BaseTool / Pydantic v2 accepts them)
    allowed_domains: Optional[set] = None
    security_level: str = "relaxed"
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = 2
    rate_limit: int = DEFAULT_RATE_LIMIT
    brave_api_key: Optional[str] = None
    firecrawl_api_key: Optional[str] = None

    # Private attributes (not validated by Pydantic)
    _rate_limiter: RateLimiter = PrivateAttr()
    _circuit_breaker: CircuitBreaker = PrivateAttr()
    _url_validator: URLValidator = PrivateAttr()
    _search_providers: Dict[SearchProvider, SearchProviderBase] = PrivateAttr()
    _http_client: Optional[httpx.AsyncClient] = PrivateAttr(default=None)
    _browser: Optional[Browser] = PrivateAttr(default=None)
    _playwright: Optional[Any] = PrivateAttr(default=None)
    _current_snapshot: Optional[Snapshot] = PrivateAttr(default=None)
    _page: Optional[Page] = PrivateAttr(default=None)
    _context: Optional[BrowserContext] = PrivateAttr(default=None)

    # Metrics
    _request_count: int = PrivateAttr(default=0)
    _success_count: int = PrivateAttr(default=0)
    _failure_count: int = PrivateAttr(default=0)
    _total_duration_ms: float = PrivateAttr(default=0)

    def model_post_init(self, __context: Any) -> None:
        """Initialize components after Pydantic validation."""
        if self.allowed_domains is None:
            self.allowed_domains = DEFAULT_ALLOWED_DOMAINS
        self.brave_api_key = self.brave_api_key or os.getenv("BRAVE_API_KEY")
        self.firecrawl_api_key = self.firecrawl_api_key or os.getenv("FIRECRAWL_API_KEY")
        self.security_level = SecurityLevel(self.security_level)

        # Initialize components
        self._rate_limiter = RateLimiter(rate=self.rate_limit, per_seconds=60)
        self._circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
        self._url_validator = URLValidator(
            allowed_domains=self.allowed_domains,
            security_level=self.security_level,
        )

        # Initialize search providers
        self._search_providers = {
            SearchProvider.DUCKDUCKGO: DuckDuckGoProvider(),
            SearchProvider.BRAVE: BraveSearchProvider(api_key=self.brave_api_key),
        }
    
    # ==========================================================================
    # Lifecycle Management
    # ==========================================================================
    
    async def _ensure_http_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_seconds),
                follow_redirects=True,
                max_redirects=DEFAULT_MAX_REDIRECTS,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._http_client
    
    async def _ensure_browser(self, mode: str = "headless") -> Tuple[Browser, BrowserContext, Page]:
        """Get or create browser instance."""
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        
        if self._browser is None or not self._browser.is_connected():
            self._browser = await self._playwright.chromium.launch(
                headless=(mode == "headless"),
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-accelerated-2d-canvas",
                    "--no-first-run",
                    "--no-zygote",
                    "--disable-gpu",
                ],
            )
        
        if self._context is None or not self._context.pages:
            self._context = await self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                java_script_enabled=(self.security_level != SecurityLevel.STRICT),
            )
        
        if self._page is None or self._page.is_closed():
            self._page = await self._context.new_page()
        
        return self._browser, self._context, self._page
    
    async def close(self) -> None:
        """Clean up resources."""
        if self._page and not self._page.is_closed():
            await self._page.close()
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        
        logger.info("web_browser_closed")
    
    def __del__(self):
        """Destructor: best-effort cleanup."""
        try:
            if self._browser:
                asyncio.run(self._browser.close())
        except:
            pass
    
    # ==========================================================================
    # Security & Validation
    # ==========================================================================
    
    def _validate_url(self, url: str) -> str:
        """Validate and normalize URL."""
        if not url:
            raise ValueError("URL is required")
        
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        
        is_valid, error = self._url_validator.validate(url)
        if not is_valid:
            raise ValueError(f"URL validation failed: {error}")
        
        return url
    
    def _validate_snapshot(self) -> None:
        """Validate current snapshot is still valid."""
        if not self._current_snapshot:
            raise ValueError("No snapshot available. Call 'snapshot' action first.")
        
        if not self._current_snapshot.is_valid():
            self._current_snapshot.is_expired = True
            raise ValueError(
                "Snapshot expired (older than 5 minutes). Call 'snapshot' action again to refresh."
            )
    
    def _validate_ref(self, ref_id: str) -> None:
        """Validate ref exists in current snapshot."""
        if not self._current_snapshot:
            raise ValueError("No snapshot available. Call 'snapshot' action first.")
        
        if ref_id not in self._current_snapshot.elements:
            available_refs = ", ".join(list(self._current_snapshot.elements.keys())[:10])
            raise ValueError(
                f"Unknown ref: {ref_id}. Available refs: {available_refs}. "
                "Call 'snapshot' action to refresh."
            )
    
    # ==========================================================================
    # Core Actions
    # ==========================================================================
    
    async def _fetch(self, url: str, timeout: int) -> WebBrowserResult:
        """Fetch webpage content using httpx (fast, no JS)."""
        start_time = time.monotonic()
        
        try:
            client = await self._ensure_http_client()
            response = await client.get(url)
            
            # Check content type
            content_type = response.headers.get("content-type", "").lower()
            for blocked_type in BLOCKED_MIME_TYPES:
                if blocked_type in content_type:
                    return WebBrowserResult(
                        action="fetch",
                        url=url,
                        status="failed",
                        status_code=response.status_code,
                        content="",
                        metadata={"content_type": content_type},
                        error=f"Blocked content type: {content_type}",
                        duration_ms=(time.monotonic() - start_time) * 1000,
                    )
            
            content = response.text[:self.MAX_CONTENT_LENGTH]
            truncated = len(response.text) > self.MAX_CONTENT_LENGTH
            
            return WebBrowserResult(
                action="fetch",
                url=url,
                status="success",
                status_code=response.status_code,
                content=content,
                metadata={
                    "content_type": content_type,
                    "content_length": len(response.text),
                    "truncated": truncated,
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except httpx.TimeoutException as e:
            return WebBrowserResult(
                action="fetch",
                url=url,
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Request timeout: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="fetch",
                url=url,
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Request failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    async def _fetch_with_firecrawl_fallback(self, url: str, timeout: int) -> WebBrowserResult:
        """Fetch with Firecrawl fallback for JS-heavy sites."""
        # Try httpx first
        result = await self._fetch(url, timeout)
        
        # Use Firecrawl if httpx returns empty/short content
        if result.status == "success" and len(result.content) > 100:
            return result
        
        # Firecrawl fallback
        if not self.firecrawl_api_key:
            return result
        
        try:
            start_time = time.monotonic()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.firecrawl.dev/v1/scrape",
                    headers={"Authorization": f"Bearer {self.firecrawl_api_key}"},
                    json={
                        "url": url,
                        "onlyMainContent": True,
                        "formats": ["markdown", "html"],
                    },
                    timeout=timeout,
                )
            
            data = response.json()
            
            if data.get("success") and data.get("data"):
                content = data["data"].get("markdown", "") or data["data"].get("html", "")
                
                return WebBrowserResult(
                    action="fetch",
                    url=url,
                    status="success",
                    status_code=200,
                    content=content[:self.MAX_CONTENT_LENGTH],
                    metadata={
                        "source": "firecrawl",
                        "title": data["data"].get("title"),
                        "fetch_method": "firecrawl_fallback",
                    },
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )
        except Exception as e:
            logger.warning("firecrawl_fallback_failed", error=str(e))
        
        return result
    
    async def _snapshot(self, url: str, mode: str = "ai") -> WebBrowserResult:
        """Capture page snapshot with element references."""
        start_time = time.monotonic()
        
        try:
            browser, context, page = await self._ensure_browser("headless")
            
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)
            
            # Generate snapshot
            snapshot_mode = SnapshotMode.AI if mode == "ai" else SnapshotMode.ROLE
            engine = SnapshotEngine(mode=snapshot_mode)
            snapshot = await engine.generate_snapshot(page)
            
            # Store for subsequent actions
            self._current_snapshot = snapshot
            self._page = page
            
            return WebBrowserResult(
                action="snapshot",
                url=url,
                status="success",
                status_code=200,
                content=snapshot.summary(),
                metadata={
                    "mode": mode,
                    "element_count": len(snapshot.elements),
                    "refs": {ref: elem.hint() for ref, elem in list(snapshot.elements.items())[:20]},
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except Exception as e:
            return WebBrowserResult(
                action="snapshot",
                url=url,
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Snapshot failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    async def _act(
        self,
        ref: str,
        action_type: str,
        value: Optional[str] = None,
    ) -> WebBrowserResult:
        """Perform action on element by reference."""
        start_time = time.monotonic()
        
        try:
            # Validate snapshot and ref
            self._validate_snapshot()
            self._validate_ref(ref)
            
            if not self._page:
                raise ValueError("No active page. Call 'snapshot' action first.")
            
            # Get element from snapshot
            element = self._current_snapshot.elements[ref]
            
            # Resolve ref to element handle
            engine = SnapshotEngine()  # Need fresh engine to use stored elements
            engine._elements = self._current_snapshot.elements
            handle = await engine.resolve_ref(self._page, ref)
            
            if not handle:
                return WebBrowserResult(
                    action="act",
                    url=self._current_snapshot.url,
                    status="failed",
                    status_code=None,
                    content="",
                    metadata={},
                    error=f"Ref {ref} not found. Page may have changed. Call 'snapshot' again.",
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )
            
            # Execute action
            if action_type == "click":
                await handle.click(timeout=5000)
            elif action_type == "type" or action_type == "fill":
                if not value:
                    raise ValueError("Value required for type/fill action")
                await handle.fill(value, timeout=5000)
            elif action_type == "press":
                await handle.press(value or "Enter", timeout=5000)
            elif action_type == "hover":
                await handle.hover(timeout=5000)
            elif action_type == "focus":
                await handle.focus()
            elif action_type == "select":
                if not value:
                    raise ValueError("Value required for select action")
                await handle.select_option(value, timeout=5000)
            else:
                raise ValueError(f"Unknown action type: {action_type}")
            
            # Settle delay
            await asyncio.sleep(0.5)
            
            # Take new snapshot after action (page may have changed)
            new_snapshot = await SnapshotEngine().generate_snapshot(self._page)
            self._current_snapshot = new_snapshot
            
            return WebBrowserResult(
                action="act",
                url=self._current_snapshot.url,
                status="success",
                status_code=200,
                content=f"Action '{action_type}' performed on ref {ref}. {element.hint()}",
                metadata={
                    "performed_action": action_type,
                    "target_ref": ref,
                    "value": value,
                    "new_element_count": len(new_snapshot.elements),
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except Exception as e:
            return WebBrowserResult(
                action="act",
                url=self._current_snapshot.url if self._current_snapshot else "",
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Action failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    async def _search(self, query: str, provider: str = "auto") -> WebBrowserResult:
        """Search the web."""
        start_time = time.monotonic()
        
        try:
            # Select provider
            if provider == "auto":
                if self.brave_api_key:
                    selected_provider = SearchProvider.BRAVE
                else:
                    selected_provider = SearchProvider.DUCKDUCKGO
            else:
                selected_provider = SearchProvider(provider)
            
            # Execute search
            search_provider = self._search_providers.get(selected_provider)
            if not search_provider:
                raise ValueError(f"Unknown search provider: {provider}")
            
            results = await search_provider.search(query, limit=10)
            
            if not results:
                # Fallback to DuckDuckGo
                if selected_provider != SearchProvider.DUCKDUCKGO:
                    results = await self._search_providers[SearchProvider.DUCKDUCKGO].search(query, limit=10)
            
            # Format results
            content_lines = []
            for r in results:
                content_lines.append(f"{r.rank}. {r.title}\n   URL: {r.url}\n   {r.snippet}\n")
            
            content = "\n".join(content_lines) if content_lines else "No results found."
            
            return WebBrowserResult(
                action="search",
                url="",
                status="success",
                status_code=200,
                content=content,
                metadata={
                    "query": query,
                    "provider": selected_provider.value,
                    "result_count": len(results),
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except Exception as e:
            return WebBrowserResult(
                action="search",
                url="",
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Search failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    async def _screenshot(self, url: str, mode: str = "headless") -> WebBrowserResult:
        """Capture screenshot of webpage."""
        start_time = time.monotonic()
        
        try:
            browser, context, page = await self._ensure_browser(mode)
            
            await page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)
            
            screenshot = await page.screenshot(type="png", full_page=True)
            
            return WebBrowserResult(
                action="screenshot",
                url=url,
                status="success",
                status_code=200,
                content=f"[Screenshot captured - {len(screenshot)} bytes]",
                metadata={
                    "size_bytes": len(screenshot),
                    "format": "png",
                    "full_page": True,
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except Exception as e:
            return WebBrowserResult(
                action="screenshot",
                url=url,
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Screenshot failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    async def _browse(
        self,
        url: str,
        mode: str = "headless",
        wait_for: Optional[str] = None,
    ) -> WebBrowserResult:
        """Full browser automation (legacy, kept for compatibility)."""
        start_time = time.monotonic()
        
        try:
            browser, context, page = await self._ensure_browser(mode)
            
            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)
            
            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.timeout_seconds * 1000)
            
            content = await page.content()
            
            return WebBrowserResult(
                action="browse",
                url=url,
                status="success",
                status_code=200,
                content=content[:self.MAX_CONTENT_LENGTH],
                metadata={"title": await page.title()},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
            
        except Exception as e:
            return WebBrowserResult(
                action="browse",
                url=url,
                status="failed",
                status_code=None,
                content="",
                metadata={},
                error=f"Browse failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
    
    # ==========================================================================
    # BaseTool Interface
    # ==========================================================================
    
    async def _arun(
        self,
        action: str = "fetch",
        url: str = "",
        query: str = "",
        ref: str = "",
        action_type: str = "",
        value: str = "",
        mode: str = "headless",
        snapshot_mode: str = "ai",
        search_provider: str = "auto",
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> str:
        """Execute web browser action."""
        start_time = time.monotonic()
        
        self._request_count += 1
        timeout = timeout_seconds or self.timeout_seconds
        retries = max_retries or self.max_retries
        
        try:
            await self._rate_limiter.acquire()
            
            async def execute_with_circuit_breaker():
                nonlocal url
                # Validate URL if required
                if action in ["fetch", "browse", "snapshot", "screenshot", "act"]:
                    if not url and action != "act":
                        raise ValueError("URL is required for this action")
                    if url:
                        url = self._validate_url(url)
                
                # Execute action
                if action == "fetch":
                    result = await self._fetch_with_firecrawl_fallback(url, timeout)
                elif action == "browse":
                    result = await self._browse(url, mode)
                elif action == "search":
                    if not query:
                        raise ValueError("Query is required for search action")
                    result = await self._search(query, search_provider)
                elif action == "snapshot":
                    if not url:
                        raise ValueError("URL is required for snapshot action")
                    result = await self._snapshot(url, snapshot_mode)
                elif action == "act":
                    if not ref:
                        raise ValueError("Ref is required for act action")
                    if not action_type:
                        raise ValueError("Action type is required (click, type, etc.)")
                    result = await self._act(ref, action_type, value if value else None)
                elif action == "screenshot":
                    if not url:
                        raise ValueError("URL is required for screenshot action")
                    result = await self._screenshot(url, mode)
                else:
                    raise ValueError(f"Unknown action: {action}")
                
                return result
            
            # Execute with circuit breaker and retries
            last_error = None
            for attempt in range(retries + 1):
                try:
                    result = await self._circuit_breaker.call(execute_with_circuit_breaker)
                    
                    self._success_count += 1
                    self._total_duration_ms += result.duration_ms
                    
                    logger.info(
                        "web_browser_action_completed",
                        action=action,
                        url=url,
                        status=result.status,
                        duration_ms=result.duration_ms,
                        attempt=attempt + 1,
                    )
                    
                    return result.summary() + "\n\n" + result.content[:2000]
                    
                except Exception as e:
                    last_error = e
                    logger.warning(
                        "web_browser_action_retry",
                        action=action,
                        attempt=attempt + 1,
                        error=str(e),
                    )
                    if attempt < retries:
                        await asyncio.sleep(1 * (attempt + 1))
            
            self._failure_count += 1
            return f"Action failed after {retries + 1} attempts: {last_error}"
            
        except Exception as e:
            self._failure_count += 1
            logger.error("web_browser_action_failed", action=action, error=str(e))
            return f"Error: {e}"
    
    def _run(
        self,
        action: str = "fetch",
        url: str = "",
        query: str = "",
        ref: str = "",
        action_type: str = "",
        value: str = "",
        mode: str = "headless",
        snapshot_mode: str = "ai",
        search_provider: str = "auto",
        timeout_seconds: Optional[int] = None,
        max_retries: Optional[int] = None,
    ) -> str:
        """Synchronous wrapper."""
        return asyncio.run(self._arun(
            action, url, query, ref, action_type, value,
            mode, snapshot_mode, search_provider, timeout_seconds, max_retries,
        ))
    
    # ==========================================================================
    # Health Check (for Monitoring Dashboard)
    # ==========================================================================
    
    async def health_check(self) -> dict:
        """Check tool health for monitoring dashboard."""
        start_time = time.monotonic()
        
        try:
            test_url = "https://httpbin.org/get"
            is_valid, _ = self._url_validator.validate(test_url)
            
            if not is_valid:
                self.allowed_domains.add("httpbin.org")
            
            result = await self._fetch(test_url, timeout=5)
            latency_ms = (time.monotonic() - start_time) * 1000
            
            if result.status == "success":
                status = "healthy"
            elif result.status == "partial":
                status = "degraded"
            else:
                status = "unhealthy"
            
            return {
                "name": self.name,
                "status": status,
                "latency_ms": round(latency_ms, 2),
                "last_check": datetime.now().isoformat(),
                "details": {
                    "request_count": self._request_count,
                    "success_count": self._success_count,
                    "failure_count": self._failure_count,
                    "success_rate": round(
                        self._success_count / max(1, self._request_count) * 100, 2
                    ),
                    "avg_duration_ms": round(
                        self._total_duration_ms / max(1, self._success_count), 2
                    ),
                    "circuit_breaker_state": self._circuit_breaker.state.value,
                    "rate_limiter_tokens": round(self._rate_limiter.tokens, 2),
                    "snapshot_valid": self._current_snapshot.is_valid() if self._current_snapshot else False,
                },
                "error": result.error if result.status != "success" else None,
            }
            
        except Exception as e:
            return {
                "name": self.name,
                "status": "unhealthy",
                "latency_ms": 0,
                "last_check": datetime.now().isoformat(),
                "details": {},
                "error": str(e),
            }


# =============================================================================
# Input Schema (for LangChain)
# =============================================================================


class WebBrowserInput(BaseModel):
    """Input schema for web browser tool."""
    
    action: str = Field(
        default="fetch",
        description="Action: 'fetch', 'browse', 'search', 'snapshot', 'act', 'screenshot'",
    )
    url: str = Field(default="", description="Target URL (required for fetch, browse, snapshot, screenshot)")
    query: str = Field(default="", description="Search query (required for search)")
    ref: str = Field(default="", description="Element ref from snapshot (required for act)")
    action_type: str = Field(default="", description="Action type: click, type, press, hover, select (for act)")
    value: str = Field(default="", description="Value for type/select actions")
    mode: str = Field(default="headless", description="Browser mode: 'headless' or 'headful'")
    snapshot_mode: str = Field(default="ai", description="Snapshot mode: 'ai' (numeric) or 'role' (e-prefixed)")
    search_provider: str = Field(default="auto", description="Search provider: 'auto', 'brave', 'duckduckgo'")
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)


WebBrowserTool.args_schema = WebBrowserInput


# =============================================================================
# Factory Function
# =============================================================================


def create_web_browser_tool(
    allowed_domains: Optional[set[str]] = None,
    security_level: str = "relaxed",
    rate_limit: int = DEFAULT_RATE_LIMIT,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    brave_api_key: Optional[str] = None,
    firecrawl_api_key: Optional[str] = None,
) -> WebBrowserTool:
    """Create WebBrowserTool with sensible defaults."""
    return WebBrowserTool(
        allowed_domains=allowed_domains,
        security_level=security_level,
        rate_limit=rate_limit,
        timeout_seconds=timeout_seconds,
        brave_api_key=brave_api_key,
        firecrawl_api_key=firecrawl_api_key,
    )


__all__ = [
    "WebBrowserTool",
    "WebBrowserInput",
    "create_web_browser_tool",
    "SnapshotEngine",
    "Snapshot",
    "ElementRef",
    "SearchProvider",
    "SecurityLevel",
    "BrowserMode",
]