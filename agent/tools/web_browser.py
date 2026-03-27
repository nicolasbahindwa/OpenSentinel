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
import json
import os
import re
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from enum import Enum
from html.parser import HTMLParser
from typing import ClassVar, Type, Optional, Dict, List, Tuple, Any
from urllib.parse import urlparse, urljoin, quote

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


class SecurityLevel(str, Enum):
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
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_REDIRECTS = 5
DEFAULT_MAX_RESPONSE_SIZE = 5_000_000  # 5MB
DEFAULT_RETURN_CONTENT_SIZE = 20_000   # chars returned to LLM per call
DEFAULT_MAX_SNAPSHOT_AGE_SECONDS = 300  # 5 minutes

# Multi-session limits
MAX_SESSIONS = 5
MAX_PAGES_PER_SESSION = 10
MAX_LOG_ENTRIES = 100

# Stealth mode scripts
STEALTH_SCRIPTS = {
    "gentle": [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
    ],
    "balanced": [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]})",
        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']})",
        "window.chrome = {runtime: {}}",
    ],
    "aggressive": [
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        "Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]})",
        "Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']})",
        "window.chrome = {runtime: {}}",
        "const origQuery = window.navigator.permissions.query;"
        "window.navigator.permissions.query = (parameters) => ("
        "  parameters.name === 'notifications' ?"
        "  Promise.resolve({state: Notification.permission}) :"
        "  origQuery(parameters)"
        ");",
        "Object.defineProperty(navigator, 'platform', {get: () => 'Win32'})",
        "Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8})",
    ],
}


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


@dataclass
class NavigationEntry:
    """Single navigation history entry."""
    url: str
    title: str
    timestamp: str
    page_id: str


@dataclass
class ConsoleEntry:
    """Captured console log entry."""
    type: str  # log, warn, error, info
    text: str
    timestamp: str
    page_id: str


@dataclass
class NetworkError:
    """Captured network error."""
    url: str
    status: Optional[int]
    failure: str
    timestamp: str
    page_id: str


@dataclass
class BrowserSession:
    """State for one browser session (launched or CDP-connected)."""
    session_id: str
    browser: Optional[Browser] = None
    context: Optional[BrowserContext] = None
    pages: Dict[str, Page] = field(default_factory=dict)
    active_page_id: str = ""
    history: List[NavigationEntry] = field(default_factory=list)
    console_logs: List[ConsoleEntry] = field(default_factory=list)
    network_errors: List[NetworkError] = field(default_factory=list)
    stealth_enabled: bool = False
    stealth_level: str = "balanced"
    is_cdp: bool = False


# =============================================================================
# HTML Cleaner
# =============================================================================


class _HtmlCleaner(HTMLParser):
    """Strips HTML down to readable text + image URLs using stdlib only."""

    # Tags whose entire content (including children) should be discarded
    _SKIP_TAGS = {"script", "style", "noscript", "head", "meta", "link",
                  "svg", "canvas", "iframe", "object", "embed", "applet"}
    # Tags that should produce a line-break in the output
    _BLOCK_TAGS = {"p", "div", "section", "article", "main", "header",
                   "footer", "aside", "li", "tr", "h1", "h2", "h3",
                   "h4", "h5", "h6", "br", "hr", "blockquote", "pre"}

    def __init__(self, base_url: str = ""):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._parts: List[str] = []
        self._skip_depth = 0  # >0 means we're inside a skip-tag
        self._images: List[str] = []

    def handle_starttag(self, tag: str, attrs):
        if self._skip_depth > 0:
            if tag in self._SKIP_TAGS:
                self._skip_depth += 1
            return
        if tag in self._SKIP_TAGS:
            self._skip_depth += 1
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")
        if tag == "img":
            attr_dict = dict(attrs)
            src = attr_dict.get("src", "") or attr_dict.get("data-src", "")
            alt = attr_dict.get("alt", "")
            if src:
                full_src = urljoin(self.base_url, src) if self.base_url else src
                if full_src not in self._images:
                    self._images.append(full_src)
                label = alt or src.split("/")[-1]
                self._parts.append(f"[Image: {label}]")
        if tag == "a":
            attr_dict = dict(attrs)
            href = attr_dict.get("href", "")
            if href and not href.startswith(("#", "javascript:")):
                full_href = urljoin(self.base_url, href) if self.base_url else href
                self._parts.append(f"[Link→{full_href}] ")

    def handle_endtag(self, tag: str):
        if self._skip_depth > 0:
            if tag in self._SKIP_TAGS:
                self._skip_depth -= 1
            return
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str):
        if self._skip_depth > 0:
            return
        text = data.strip()
        if text:
            self._parts.append(text + " ")

    def get_text(self) -> str:
        raw = "".join(self._parts)
        # Collapse runs of whitespace/newlines
        raw = re.sub(r" {2,}", " ", raw)
        raw = re.sub(r"\n{3,}", "\n\n", raw)
        return raw.strip()

    def get_images(self) -> List[str]:
        return self._images


def clean_html(html: str, base_url: str = "", max_chars: int = 0) -> Tuple[str, List[str]]:
    """
    Parse raw HTML and return (readable_text, [image_urls]).
    Strips all scripts, styles, and tags — keeps text, links, image refs.
    """
    parser = _HtmlCleaner(base_url=base_url)
    try:
        parser.feed(html)
    except Exception:
        # Fallback: crude tag strip
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s{2,}", " ", text).strip()
        return text[:max_chars] if max_chars else text, []

    text = parser.get_text()
    if max_chars:
        text = text[:max_chars]
    return text, parser.get_images()


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
        """Execute function with circuit breaker protection.

        ValueError and KeyboardInterrupt are treated as caller errors and are
        NOT counted against the failure threshold.
        """
        async with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self.last_failure_time and (time.time() - self.last_failure_time) > self.recovery_timeout:
                    self.state = CircuitBreakerState.HALF_OPEN
                    self.success_count = 0
                    logger.info("circuit_breaker_half_open")
                else:
                    raise Exception("Circuit breaker is OPEN - service temporarily unavailable. Try again in a moment.")

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
                    # Successful call in CLOSED state — gradually heal failure count
                    if self.failure_count > 0:
                        self.failure_count = max(0, self.failure_count - 1)
            return result
        except ValueError:
            # Input/validation errors are caller mistakes, not service failures.
            # Do NOT count them against the circuit breaker.
            raise
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
# Browser Manager (multi-session, multi-tab)
# =============================================================================


class BrowserManager:
    """Manages multiple browser sessions, each with multiple tabs."""

    def __init__(self) -> None:
        self._playwright: Optional[Any] = None
        self._sessions: Dict[str, BrowserSession] = {}

    async def _ensure_playwright(self) -> Any:
        if self._playwright is None:
            self._playwright = await async_playwright().start()
        return self._playwright

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def launch_session(
        self,
        session_id: str = "default",
        mode: str = "headless",
        security_level: SecurityLevel = SecurityLevel.RELAXED,
    ) -> BrowserSession:
        """Launch a new browser session (or reuse existing connected one)."""
        if session_id in self._sessions:
            session = self._sessions[session_id]
            if session.browser and session.browser.is_connected():
                return session
            # Dead session — remove and re-launch
            self._sessions.pop(session_id, None)

        if len(self._sessions) >= MAX_SESSIONS:
            raise ValueError(f"Max sessions ({MAX_SESSIONS}) reached. Close one first.")

        pw = await self._ensure_playwright()
        browser = await pw.chromium.launch(
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
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            java_script_enabled=(security_level != SecurityLevel.STRICT),
        )
        page = await context.new_page()
        page_id = "page_0"

        session = BrowserSession(
            session_id=session_id,
            browser=browser,
            context=context,
            pages={page_id: page},
            active_page_id=page_id,
        )
        self._setup_page_listeners(session, page, page_id)
        self._sessions[session_id] = session
        logger.info("browser_session_launched", session_id=session_id, mode=mode)
        return session

    async def connect_over_cdp(
        self,
        cdp_url: str,
        session_id: str = "cdp",
    ) -> BrowserSession:
        """Connect to an existing Chrome instance via CDP."""
        if session_id in self._sessions:
            await self.close_session(session_id)

        if len(self._sessions) >= MAX_SESSIONS:
            raise ValueError(f"Max sessions ({MAX_SESSIONS}) reached. Close one first.")

        pw = await self._ensure_playwright()
        browser = await pw.chromium.connect_over_cdp(cdp_url)
        contexts = browser.contexts
        context = contexts[0] if contexts else await browser.new_context()
        existing_pages = context.pages

        page_dict: Dict[str, Page] = {}
        for i, p in enumerate(existing_pages):
            page_dict[f"page_{i}"] = p

        if not page_dict:
            new_page = await context.new_page()
            page_dict["page_0"] = new_page

        session = BrowserSession(
            session_id=session_id,
            browser=browser,
            context=context,
            pages=page_dict,
            active_page_id=list(page_dict.keys())[0],
            is_cdp=True,
        )

        for pid, p in page_dict.items():
            self._setup_page_listeners(session, p, pid)

        self._sessions[session_id] = session
        logger.info("browser_cdp_connected", session_id=session_id, cdp_url=cdp_url,
                     pages=len(page_dict))
        return session

    # ------------------------------------------------------------------
    # Page listeners (console + network)
    # ------------------------------------------------------------------

    def _setup_page_listeners(self, session: BrowserSession, page: Page, page_id: str) -> None:
        """Attach console and network-error capture to a page."""
        def on_console(msg):
            if len(session.console_logs) >= MAX_LOG_ENTRIES:
                session.console_logs.pop(0)
            session.console_logs.append(ConsoleEntry(
                type=msg.type,
                text=msg.text,
                timestamp=datetime.now().isoformat(),
                page_id=page_id,
            ))

        def on_request_failed(request):
            if len(session.network_errors) >= MAX_LOG_ENTRIES:
                session.network_errors.pop(0)
            session.network_errors.append(NetworkError(
                url=request.url,
                status=None,
                failure=request.failure or "unknown",
                timestamp=datetime.now().isoformat(),
                page_id=page_id,
            ))

        page.on("console", on_console)
        page.on("requestfailed", on_request_failed)

    # ------------------------------------------------------------------
    # Session / page accessors
    # ------------------------------------------------------------------

    def get_session(self, session_id: str = "default") -> BrowserSession:
        session = self._sessions.get(session_id)
        if not session:
            raise ValueError(
                f"Session '{session_id}' not found. Available: {list(self._sessions.keys())}"
            )
        return session

    def get_page(
        self, session_id: str = "default", page_id: str = ""
    ) -> Tuple[BrowserSession, Page]:
        session = self.get_session(session_id)
        pid = page_id or session.active_page_id
        page = session.pages.get(pid)
        if not page or page.is_closed():
            raise ValueError(f"Page '{pid}' not found or closed in session '{session_id}'")
        return session, page

    # ------------------------------------------------------------------
    # Tab management
    # ------------------------------------------------------------------

    async def new_page(self, session_id: str = "default") -> Tuple[str, Page]:
        session = self.get_session(session_id)
        if len(session.pages) >= MAX_PAGES_PER_SESSION:
            raise ValueError(f"Max pages ({MAX_PAGES_PER_SESSION}) for session '{session_id}'")

        page = await session.context.new_page()
        idx = len(session.pages)
        page_id = f"page_{idx}"
        while page_id in session.pages:
            idx += 1
            page_id = f"page_{idx}"

        session.pages[page_id] = page
        session.active_page_id = page_id
        self._setup_page_listeners(session, page, page_id)
        return page_id, page

    async def close_page(self, session_id: str = "default", page_id: str = "") -> None:
        session = self.get_session(session_id)
        pid = page_id or session.active_page_id
        page = session.pages.get(pid)
        if page and not page.is_closed():
            await page.close()
        session.pages.pop(pid, None)

        if pid == session.active_page_id:
            remaining = [k for k in session.pages if not session.pages[k].is_closed()]
            session.active_page_id = remaining[0] if remaining else ""

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    async def close_session(self, session_id: str) -> None:
        session = self._sessions.pop(session_id, None)
        if not session:
            return
        for page in session.pages.values():
            if not page.is_closed():
                try:
                    await page.close()
                except Exception:
                    pass
        if session.context:
            try:
                await session.context.close()
            except Exception:
                pass
        if session.browser and not session.is_cdp:
            try:
                await session.browser.close()
            except Exception:
                pass
        logger.info("browser_session_closed", session_id=session_id)

    async def shutdown(self) -> None:
        """Close all sessions and stop Playwright."""
        for sid in list(self._sessions.keys()):
            await self.close_session(sid)
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("browser_manager_shutdown")

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> dict:
        stats: Dict[str, Any] = {}
        for sid, session in self._sessions.items():
            stats[sid] = {
                "pages": len(session.pages),
                "active_page": session.active_page_id,
                "history_count": len(session.history),
                "console_logs": len(session.console_logs),
                "network_errors": len(session.network_errors),
                "stealth": session.stealth_enabled,
                "is_cdp": session.is_cdp,
            }
        return stats

    @property
    def has_sessions(self) -> bool:
        return bool(self._sessions)


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
        "Browse and interact with web pages. Supports multi-session, multi-tab browsing.\n"
        "Core actions: 'fetch', 'browse', 'search', 'snapshot', 'act', 'screenshot'.\n"
        "Session: 'connect' (CDP), 'new_page', 'list_pages', 'switch_page', 'close_page'.\n"
        "Monitoring: 'get_logs', 'breadcrumbs', 'diagnose'.\n"
        "Interaction: 'fill_form', 'wait', 'extract', 'evaluate', 'handle_dialog'.\n"
        "Management: 'get_cookies', 'clear_cookies', 'stealth'.\n"
        "\nExamples:\n"
        '- Fetch: action="fetch", url="https://example.com"\n'
        '- CDP: action="connect", cdp_url="http://localhost:9222"\n'
        '- New tab: action="new_page", url="https://example.com"\n'
        '- Fill form: action="fill_form", fields=[{selector, value}]\n'
        '- Extract: action="extract", pattern="all_links"\n'
        "Security: HTTPS only, domain allowlist, private IPs blocked."
    )
    args_schema: Type[BaseModel] = None  # Set below
    handle_tool_error: bool = True
    
    # Configuration
    MAX_CONTENT_LENGTH: ClassVar[int] = DEFAULT_MAX_RESPONSE_SIZE

    # Pydantic fields (declared so BaseTool / Pydantic v2 accepts them)
    allowed_domains: Optional[set] = None
    security_level: SecurityLevel = SecurityLevel.RELAXED
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
    _browser_manager: BrowserManager = PrivateAttr()
    _snapshots: Dict[str, Snapshot] = PrivateAttr(default_factory=dict)

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
        self._circuit_breaker = CircuitBreaker(failure_threshold=10, recovery_timeout=30)
        self._url_validator = URLValidator(
            allowed_domains=self.allowed_domains,
            security_level=self.security_level,
        )

        # Initialize search providers
        self._search_providers = {
            SearchProvider.DUCKDUCKGO: DuckDuckGoProvider(),
            SearchProvider.BRAVE: BraveSearchProvider(api_key=self.brave_api_key),
        }

        # Initialize browser manager
        self._browser_manager = BrowserManager()
    
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
    
    async def _ensure_browser(
        self,
        mode: str = "headless",
        session_id: str = "default",
    ) -> Tuple[BrowserSession, Page]:
        """Get or create browser session + active page."""
        session = await self._browser_manager.launch_session(
            session_id=session_id,
            mode=mode,
            security_level=self.security_level,
        )
        page = session.pages.get(session.active_page_id)
        if not page or page.is_closed():
            _, page = await self._browser_manager.new_page(session_id)
        return session, page

    def _snapshot_key(self, session_id: str, page_id: str) -> str:
        """Key for the snapshots dict."""
        return f"{session_id}:{page_id}"

    def _get_current_snapshot(
        self, session_id: str = "default", page_id: str = ""
    ) -> Optional[Snapshot]:
        """Get the snapshot for a given session/page."""
        if not page_id:
            session = self._browser_manager._sessions.get(session_id)
            if session:
                page_id = session.active_page_id
        return self._snapshots.get(self._snapshot_key(session_id, page_id))

    def _set_current_snapshot(
        self, snapshot: Snapshot, session_id: str = "default", page_id: str = ""
    ) -> None:
        if not page_id:
            session = self._browser_manager._sessions.get(session_id)
            if session:
                page_id = session.active_page_id
        self._snapshots[self._snapshot_key(session_id, page_id)] = snapshot

    async def close(self) -> None:
        """Clean up resources."""
        await self._browser_manager.shutdown()
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        self._snapshots.clear()
        logger.info("web_browser_closed")

    def __del__(self):
        """Destructor: best-effort cleanup."""
        try:
            if self._browser_manager.has_sessions:
                asyncio.run(self._browser_manager.shutdown())
        except Exception:
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
    
    def _validate_snapshot(self, session_id: str = "default", page_id: str = "") -> Snapshot:
        """Validate current snapshot is still valid. Returns snapshot."""
        snap = self._get_current_snapshot(session_id, page_id)
        if not snap:
            raise ValueError("No snapshot available. Call 'snapshot' action first.")
        if not snap.is_valid():
            snap.is_expired = True
            raise ValueError(
                "Snapshot expired (older than 5 minutes). Call 'snapshot' action again to refresh."
            )
        return snap

    def _validate_ref(self, ref_id: str, session_id: str = "default", page_id: str = "") -> None:
        """Validate ref exists in current snapshot."""
        snap = self._get_current_snapshot(session_id, page_id)
        if not snap:
            raise ValueError("No snapshot available. Call 'snapshot' action first.")
        if ref_id not in snap.elements:
            available_refs = ", ".join(list(snap.elements.keys())[:10])
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
            
            raw = response.text
            # Clean HTML → readable text + image list
            if "html" in content_type:
                content, images = clean_html(raw, base_url=url, max_chars=self.MAX_CONTENT_LENGTH)
            else:
                content, images = raw[:self.MAX_CONTENT_LENGTH], []

            return WebBrowserResult(
                action="fetch",
                url=url,
                status="success",
                status_code=response.status_code,
                content=content,
                metadata={
                    "content_type": content_type,
                    "content_length": len(raw),
                    "cleaned_length": len(content),
                    "images": images[:20],
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
    
    async def _snapshot(
        self, url: str, mode: str = "ai",
        session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Capture page snapshot with element references."""
        start_time = time.monotonic()

        try:
            session, page = await self._ensure_browser("headless", session_id)
            pid = page_id or session.active_page_id

            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)

            # Record navigation
            session.history.append(NavigationEntry(
                url=url, title=await page.title(),
                timestamp=datetime.now().isoformat(), page_id=pid,
            ))

            # Generate snapshot
            snapshot_mode = SnapshotMode.AI if mode == "ai" else SnapshotMode.ROLE
            engine = SnapshotEngine(mode=snapshot_mode)
            snapshot = await engine.generate_snapshot(page)

            # Store for subsequent actions
            self._set_current_snapshot(snapshot, session_id, pid)

            return WebBrowserResult(
                action="snapshot",
                url=url,
                status="success",
                status_code=200,
                content=snapshot.summary(),
                metadata={
                    "mode": mode,
                    "element_count": len(snapshot.elements),
                    "session_id": session_id,
                    "page_id": pid,
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
        session_id: str = "default",
        page_id: str = "",
    ) -> WebBrowserResult:
        """Perform action on element by reference."""
        start_time = time.monotonic()

        try:
            snap = self._validate_snapshot(session_id, page_id)
            self._validate_ref(ref, session_id, page_id)

            session, page = self._browser_manager.get_page(session_id, page_id)
            pid = page_id or session.active_page_id

            element = snap.elements[ref]

            # Resolve ref to element handle
            engine = SnapshotEngine()
            engine._elements = snap.elements
            handle = await engine.resolve_ref(page, ref)

            if not handle:
                return WebBrowserResult(
                    action="act", url=snap.url,
                    status="failed", status_code=None, content="", metadata={},
                    error=f"Ref {ref} not found. Page may have changed. Call 'snapshot' again.",
                    duration_ms=(time.monotonic() - start_time) * 1000,
                )

            # Execute action
            if action_type == "click":
                await handle.click(timeout=5000)
            elif action_type in ("type", "fill"):
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

            await asyncio.sleep(0.5)

            # Refresh snapshot after action
            new_snapshot = await SnapshotEngine().generate_snapshot(page)
            self._set_current_snapshot(new_snapshot, session_id, pid)

            return WebBrowserResult(
                action="act", url=new_snapshot.url,
                status="success", status_code=200,
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
            snap = self._get_current_snapshot(session_id, page_id)
            return WebBrowserResult(
                action="act", url=snap.url if snap else "",
                status="failed", status_code=None, content="", metadata={},
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
    
    async def _screenshot(
        self, url: str, mode: str = "headless",
        session_id: str = "default",
    ) -> WebBrowserResult:
        """Capture screenshot of webpage."""
        start_time = time.monotonic()

        try:
            session, page = await self._ensure_browser(mode, session_id)

            await page.goto(url, wait_until="networkidle", timeout=self.timeout_seconds * 1000)

            screenshot = await page.screenshot(type="png", full_page=True)

            return WebBrowserResult(
                action="screenshot", url=url,
                status="success", status_code=200,
                content=f"[Screenshot captured - {len(screenshot)} bytes]",
                metadata={"size_bytes": len(screenshot), "format": "png", "full_page": True},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

        except Exception as e:
            return WebBrowserResult(
                action="screenshot", url=url,
                status="failed", status_code=None, content="", metadata={},
                error=f"Screenshot failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _browse(
        self, url: str, mode: str = "headless",
        wait_for: Optional[str] = None,
        session_id: str = "default",
    ) -> WebBrowserResult:
        """Full browser automation (legacy, kept for compatibility)."""
        start_time = time.monotonic()

        try:
            session, page = await self._ensure_browser(mode, session_id)
            pid = session.active_page_id

            await page.goto(url, wait_until="domcontentloaded", timeout=self.timeout_seconds * 1000)

            # Record navigation
            session.history.append(NavigationEntry(
                url=url, title=await page.title(),
                timestamp=datetime.now().isoformat(), page_id=pid,
            ))

            if wait_for:
                await page.wait_for_selector(wait_for, timeout=self.timeout_seconds * 1000)

            # Extract clean text + images directly from the live DOM
            content = await page.evaluate("""() => {
                // Remove clutter nodes in-place (doesn't affect live page)
                const clone = document.body.cloneNode(true);
                clone.querySelectorAll(
                    'script,style,noscript,svg,canvas,iframe,object,embed,applet,nav,footer'
                ).forEach(el => el.remove());

                // Collect image refs
                const imgs = Array.from(document.querySelectorAll('img[src]'))
                    .map(i => ({ src: i.src, alt: i.alt || '' }))
                    .filter(i => i.src.startsWith('http'))
                    .slice(0, 20);

                const imgsText = imgs.length
                    ? '\\n\\n[Images]\\n' + imgs.map(i => `  [Image: ${i.alt || i.src}] ${i.src}`).join('\\n')
                    : '';

                return (clone.innerText || '').replace(/\\n{3,}/g, '\\n\\n').trim() + imgsText;
            }""")

            return WebBrowserResult(
                action="browse", url=url,
                status="success", status_code=200,
                content=content[:self.MAX_CONTENT_LENGTH],
                metadata={"title": await page.title()},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

        except Exception as e:
            return WebBrowserResult(
                action="browse", url=url,
                status="failed", status_code=None, content="", metadata={},
                error=f"Browse failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    # ==========================================================================
    # New Actions (CDP, multi-tab, forms, extraction, etc.)
    # ==========================================================================

    async def _connect(self, cdp_url: str, session_id: str = "cdp") -> WebBrowserResult:
        """Connect to an existing Chrome via CDP."""
        start_time = time.monotonic()
        try:
            session = await self._browser_manager.connect_over_cdp(cdp_url, session_id)
            page = session.pages.get(session.active_page_id)
            current_url = page.url if page else "about:blank"
            return WebBrowserResult(
                action="connect", url=current_url,
                status="success", status_code=200,
                content=f"Connected to Chrome via CDP at {cdp_url}",
                metadata={
                    "session_id": session_id,
                    "pages": len(session.pages),
                    "active_page": session.active_page_id,
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="connect", url=cdp_url,
                status="failed", status_code=None, content="", metadata={},
                error=f"CDP connect failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _new_page(self, session_id: str = "default", url: str = "") -> WebBrowserResult:
        """Create a new tab in a session."""
        start_time = time.monotonic()
        try:
            # Ensure session exists
            if session_id not in self._browser_manager._sessions:
                await self._ensure_browser("headless", session_id)
            page_id, page = await self._browser_manager.new_page(session_id)
            if url:
                await page.goto(url, wait_until="domcontentloaded",
                                timeout=self.timeout_seconds * 1000)
            return WebBrowserResult(
                action="new_page", url=url or "about:blank",
                status="success", status_code=200,
                content=f"New tab created: {page_id}",
                metadata={"session_id": session_id, "page_id": page_id},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="new_page", url=url,
                status="failed", status_code=None, content="", metadata={},
                error=f"New page failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _list_pages(self, session_id: str = "default") -> WebBrowserResult:
        """List all open tabs in a session."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            pages_info = []
            for pid, page in session.pages.items():
                if not page.is_closed():
                    pages_info.append({
                        "page_id": pid,
                        "url": page.url,
                        "title": await page.title(),
                        "active": pid == session.active_page_id,
                    })
            content = "\n".join(
                f"{'> ' if p['active'] else '  '}{p['page_id']}: {p['title']} ({p['url']})"
                for p in pages_info
            )
            return WebBrowserResult(
                action="list_pages", url="",
                status="success", status_code=200,
                content=content or "No open pages",
                metadata={"session_id": session_id, "pages": pages_info},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="list_pages", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"List pages failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _switch_page(self, session_id: str = "default", page_id: str = "") -> WebBrowserResult:
        """Switch active tab in a session."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            if page_id not in session.pages:
                raise ValueError(f"Page '{page_id}' not found. Available: {list(session.pages.keys())}")
            session.active_page_id = page_id
            page = session.pages[page_id]
            await page.bring_to_front()
            return WebBrowserResult(
                action="switch_page", url=page.url,
                status="success", status_code=200,
                content=f"Switched to {page_id}: {await page.title()}",
                metadata={"session_id": session_id, "page_id": page_id},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="switch_page", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Switch page failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _close_page(self, session_id: str = "default", page_id: str = "") -> WebBrowserResult:
        """Close a tab in a session."""
        start_time = time.monotonic()
        try:
            await self._browser_manager.close_page(session_id, page_id)
            session = self._browser_manager.get_session(session_id)
            return WebBrowserResult(
                action="close_page", url="",
                status="success", status_code=200,
                content=f"Page closed. Active: {session.active_page_id}",
                metadata={"session_id": session_id, "remaining_pages": len(session.pages)},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="close_page", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Close page failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _get_logs(
        self, session_id: str = "default",
        log_filter: str = "all", limit: int = 50,
    ) -> WebBrowserResult:
        """Get captured console logs and network errors."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            lines = []

            if log_filter in ("all", "console"):
                for entry in session.console_logs[-limit:]:
                    lines.append(f"[{entry.type}] [{entry.page_id}] {entry.text}")

            if log_filter in ("all", "network"):
                for entry in session.network_errors[-limit:]:
                    lines.append(f"[NET-ERR] [{entry.page_id}] {entry.url} — {entry.failure}")

            content = "\n".join(lines) if lines else "No logs captured."
            return WebBrowserResult(
                action="get_logs", url="",
                status="success", status_code=200,
                content=content,
                metadata={
                    "console_count": len(session.console_logs),
                    "network_error_count": len(session.network_errors),
                },
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="get_logs", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Get logs failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _breadcrumbs(self, session_id: str = "default", limit: int = 20) -> WebBrowserResult:
        """Get navigation history for a session."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            entries = session.history[-limit:]
            lines = [
                f"{i+1}. [{e.page_id}] {e.title} — {e.url} ({e.timestamp})"
                for i, e in enumerate(entries)
            ]
            return WebBrowserResult(
                action="breadcrumbs", url="",
                status="success", status_code=200,
                content="\n".join(lines) if lines else "No navigation history.",
                metadata={"total_entries": len(session.history)},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="breadcrumbs", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Breadcrumbs failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _fill_form(
        self, fields: List[Dict[str, Any]],
        submit: bool = False, submit_selector: str = "",
        session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Batch fill multiple form fields."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)
            filled = []

            for f in fields:
                selector = f.get("selector", "")
                value = f.get("value", "")
                field_type = f.get("type", "text")

                if not selector:
                    continue

                if field_type == "checkbox":
                    is_checked = await page.is_checked(selector)
                    if (value.lower() in ("true", "1", "yes")) != is_checked:
                        await page.click(selector)
                elif field_type == "select":
                    await page.select_option(selector, value)
                else:
                    await page.fill(selector, value)

                filled.append(f"{selector} = {value}")

            if submit:
                if submit_selector:
                    await page.click(submit_selector)
                else:
                    await page.keyboard.press("Enter")
                await asyncio.sleep(1)

            return WebBrowserResult(
                action="fill_form", url=page.url,
                status="success", status_code=200,
                content=f"Filled {len(filled)} fields" + (" and submitted" if submit else ""),
                metadata={"fields_filled": filled, "submitted": submit},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="fill_form", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Fill form failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _wait(
        self, session_id: str = "default", page_id: str = "",
        wait_ms: int = 2000, idle_time: int = 500,
    ) -> WebBrowserResult:
        """Wait for page stability (network idle + DOM settle)."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)

            # Wait for network to be idle
            try:
                await page.wait_for_load_state("networkidle", timeout=wait_ms)
            except Exception:
                pass  # timeout is acceptable — page is still usable

            # Extra settle time
            await asyncio.sleep(idle_time / 1000)

            return WebBrowserResult(
                action="wait", url=page.url,
                status="success", status_code=200,
                content=f"Page stable after {(time.monotonic() - start_time)*1000:.0f}ms",
                metadata={"wait_ms": wait_ms, "idle_time": idle_time},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="wait", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Wait failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _extract(
        self, pattern: str = "all_text",
        selector: str = "body",
        session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Smart content extraction from page."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)

            if pattern == "all_text":
                content = await page.evaluate(
                    "(sel) => document.querySelector(sel)?.innerText || ''", selector
                )

            elif pattern == "all_links":
                links = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                        text: a.innerText.trim().substring(0, 100),
                        href: a.href
                    })).filter(l => l.text && l.href.startsWith('http'));
                }""")
                content = "\n".join(f"- [{lnk['text']}]({lnk['href']})" for lnk in links[:100])

            elif pattern == "all_headings":
                headings = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6')).map(h => ({
                        level: h.tagName,
                        text: h.innerText.trim()
                    }));
                }""")
                content = "\n".join(f"{h['level']}: {h['text']}" for h in headings)

            elif pattern == "tables":
                tables = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('table')).map((t, i) => {
                        const rows = Array.from(t.querySelectorAll('tr')).map(r =>
                            Array.from(r.querySelectorAll('th,td')).map(c => c.innerText.trim())
                        );
                        return {index: i, rows: rows.slice(0, 50)};
                    });
                }""")
                parts = []
                for t in tables[:5]:
                    header = " | ".join(t["rows"][0]) if t["rows"] else ""
                    body = "\n".join(" | ".join(r) for r in t["rows"][1:])
                    parts.append(f"Table {t['index']}:\n{header}\n{body}")
                content = "\n\n".join(parts) if parts else "No tables found."

            elif pattern == "forms":
                forms = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('form')).map((f, i) => ({
                        index: i,
                        action: f.action,
                        method: f.method,
                        fields: Array.from(f.querySelectorAll('input,select,textarea')).map(el => ({
                            tag: el.tagName.toLowerCase(),
                            type: el.type || '',
                            name: el.name || '',
                            id: el.id || '',
                            placeholder: el.placeholder || '',
                        }))
                    }));
                }""")
                parts = []
                for f in forms[:5]:
                    fields_str = "\n".join(
                        f"  {fld['tag']}[{fld['type']}] name={fld['name']} id={fld['id']}"
                        for fld in f["fields"]
                    )
                    parts.append(
                        f"Form {f['index']} ({f['method']} → {f['action']}):\n{fields_str}"
                    )
                content = "\n\n".join(parts) if parts else "No forms found."

            elif pattern == "metadata":
                meta = await page.evaluate("""() => ({
                    title: document.title,
                    description: document.querySelector('meta[name="description"]')?.content || '',
                    og_title: document.querySelector('meta[property="og:title"]')?.content || '',
                    og_description: document.querySelector('meta[property="og:description"]')?.content || '',
                    og_image: document.querySelector('meta[property="og:image"]')?.content || '',
                    canonical: document.querySelector('link[rel="canonical"]')?.href || '',
                    lang: document.documentElement.lang || '',
                })""")
                content = "\n".join(f"{k}: {v}" for k, v in meta.items() if v)

            elif pattern == "prices":
                prices = await page.evaluate(r"""() => {
                    const pricePattern = /[\$\€\£\¥]\s*[\d,]+\.?\d*/g;
                    const text = document.body.innerText;
                    const matches = text.match(pricePattern) || [];
                    return [...new Set(matches)].slice(0, 50);
                }""")
                content = "\n".join(prices) if prices else "No prices found."

            else:
                # Custom CSS selector
                content = await page.evaluate(
                    "(sel) => document.querySelector(sel)?.innerText || 'Element not found'",
                    pattern,
                )

            return WebBrowserResult(
                action="extract", url=page.url,
                status="success", status_code=200,
                content=str(content)[:self.MAX_CONTENT_LENGTH],
                metadata={"pattern": pattern, "selector": selector},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="extract", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Extract failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _evaluate(
        self, script: str,
        session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Run custom JavaScript on the page."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)
            result = await page.evaluate(script)
            content = json.dumps(result, indent=2, default=str) if result is not None else "undefined"
            return WebBrowserResult(
                action="evaluate", url=page.url,
                status="success", status_code=200,
                content=content[:self.MAX_CONTENT_LENGTH],
                metadata={"script_length": len(script)},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="evaluate", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Evaluate failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _handle_dialog(
        self, dialog_action: str = "accept", prompt_text: str = "",
        session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Set up handler for browser dialogs (alert/confirm/prompt)."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)

            async def handler(dialog):
                if dialog_action == "dismiss":
                    await dialog.dismiss()
                else:
                    await dialog.accept(prompt_text if dialog.type == "prompt" else None)

            page.on("dialog", handler)

            return WebBrowserResult(
                action="handle_dialog", url=page.url,
                status="success", status_code=200,
                content=f"Dialog handler set: {dialog_action}"
                        + (f" with text '{prompt_text}'" if prompt_text else ""),
                metadata={"dialog_action": dialog_action, "prompt_text": prompt_text},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="handle_dialog", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Handle dialog failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _get_cookies(
        self, session_id: str = "default",
    ) -> WebBrowserResult:
        """Get cookies for the current session context."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            cookies = await session.context.cookies()
            lines = [
                f"{c['name']}={c['value'][:40]}{'...' if len(c['value'])>40 else ''} "
                f"(domain={c.get('domain','')}, path={c.get('path','/')})"
                for c in cookies[:50]
            ]
            return WebBrowserResult(
                action="get_cookies", url="",
                status="success", status_code=200,
                content="\n".join(lines) if lines else "No cookies.",
                metadata={"cookie_count": len(cookies)},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="get_cookies", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Get cookies failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _clear_cookies(self, session_id: str = "default") -> WebBrowserResult:
        """Clear all cookies for the current session context."""
        start_time = time.monotonic()
        try:
            session = self._browser_manager.get_session(session_id)
            await session.context.clear_cookies()
            return WebBrowserResult(
                action="clear_cookies", url="",
                status="success", status_code=200,
                content="All cookies cleared.",
                metadata={"session_id": session_id},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="clear_cookies", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Clear cookies failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _stealth(
        self, stealth_level: str = "balanced",
        session_id: str = "default",
    ) -> WebBrowserResult:
        """Enable anti-detection stealth mode."""
        start_time = time.monotonic()
        try:
            if stealth_level not in STEALTH_SCRIPTS:
                raise ValueError(f"Unknown stealth level: {stealth_level}. Use gentle/balanced/aggressive.")

            session = self._browser_manager.get_session(session_id)
            scripts = STEALTH_SCRIPTS[stealth_level]

            for script in scripts:
                await session.context.add_init_script(script)

            session.stealth_enabled = True
            session.stealth_level = stealth_level

            return WebBrowserResult(
                action="stealth", url="",
                status="success", status_code=200,
                content=f"Stealth mode enabled: {stealth_level} ({len(scripts)} patches applied)",
                metadata={"level": stealth_level, "patches": len(scripts)},
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="stealth", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Stealth setup failed: {e}",
                duration_ms=(time.monotonic() - start_time) * 1000,
            )

    async def _diagnose(
        self, session_id: str = "default", page_id: str = "",
    ) -> WebBrowserResult:
        """Run page health diagnostics with suggestions."""
        start_time = time.monotonic()
        try:
            session, page = self._browser_manager.get_page(session_id, page_id)

            diagnostics = await page.evaluate("""() => {
                const issues = [];
                const suggestions = [];

                // Check for console errors
                // (captured externally, just note the page state)

                // Check page load status
                if (document.readyState !== 'complete') {
                    issues.push('Page not fully loaded (readyState: ' + document.readyState + ')');
                    suggestions.push('Use action="wait" to wait for page stability');
                }

                // Check for forms
                const forms = document.querySelectorAll('form');
                if (forms.length > 0) {
                    suggestions.push('Found ' + forms.length + ' form(s). Use action="extract", pattern="forms" to inspect, then action="fill_form" to fill.');
                }

                // Check for iframes
                const iframes = document.querySelectorAll('iframe');
                if (iframes.length > 0) {
                    issues.push(iframes.length + ' iframe(s) detected — content inside may not be accessible');
                }

                // Check for CSP
                const cspMeta = document.querySelector('meta[http-equiv="Content-Security-Policy"]');
                if (cspMeta) {
                    issues.push('CSP detected — some scripts may be blocked');
                }

                // Check for SPA indicators
                const spa = document.querySelector('[id="__next"]') ||
                             document.querySelector('[id="app"]') ||
                             document.querySelector('[id="root"]');
                if (spa) {
                    suggestions.push('SPA detected. Use action="wait" before interacting to ensure content has rendered.');
                }

                // Check images
                const images = document.querySelectorAll('img');
                let brokenImages = 0;
                images.forEach(img => {
                    if (!img.complete || img.naturalWidth === 0) brokenImages++;
                });
                if (brokenImages > 0) {
                    issues.push(brokenImages + ' broken image(s) found');
                }

                return {
                    url: location.href,
                    title: document.title,
                    readyState: document.readyState,
                    elementCount: document.querySelectorAll('*').length,
                    formCount: forms.length,
                    linkCount: document.querySelectorAll('a').length,
                    imageCount: images.length,
                    iframeCount: iframes.length,
                    issues: issues,
                    suggestions: suggestions,
                };
            }""")

            # Add server-side info
            diagnostics["session_id"] = session_id
            diagnostics["console_errors"] = len(
                [entry for entry in session.console_logs if entry.type == "error"]
            )
            diagnostics["network_errors"] = len(session.network_errors)

            if diagnostics["console_errors"] > 0:
                diagnostics["suggestions"].append(
                    f'{diagnostics["console_errors"]} console error(s). Use action="get_logs" to inspect.'
                )
            if diagnostics["network_errors"] > 0:
                diagnostics["suggestions"].append(
                    f'{diagnostics["network_errors"]} network error(s). Use action="get_logs", log_filter="network".'
                )

            # Format output
            lines = [
                f"URL: {diagnostics['url']}",
                f"Title: {diagnostics['title']}",
                f"Ready: {diagnostics['readyState']}",
                f"Elements: {diagnostics['elementCount']}, Links: {diagnostics['linkCount']}, "
                f"Forms: {diagnostics['formCount']}, Images: {diagnostics['imageCount']}",
            ]
            if diagnostics["issues"]:
                lines.append("\nIssues:")
                for issue in diagnostics["issues"]:
                    lines.append(f"  - {issue}")
            if diagnostics["suggestions"]:
                lines.append("\nSuggestions:")
                for sug in diagnostics["suggestions"]:
                    lines.append(f"  - {sug}")

            return WebBrowserResult(
                action="diagnose", url=diagnostics["url"],
                status="success", status_code=200,
                content="\n".join(lines),
                metadata=diagnostics,
                duration_ms=(time.monotonic() - start_time) * 1000,
            )
        except Exception as e:
            return WebBrowserResult(
                action="diagnose", url="",
                status="failed", status_code=None, content="", metadata={},
                error=f"Diagnose failed: {e}",
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
        session_id: str = "default",
        page_id: str = "",
        cdp_url: str = "",
        log_filter: str = "all",
        limit: int = 50,
        fields: List[Dict[str, Any]] = None,
        submit: bool = False,
        submit_selector: str = "",
        wait_ms: int = 2000,
        idle_time: int = 500,
        pattern: str = "all_text",
        selector: str = "body",
        script: str = "",
        dialog_action: str = "accept",
        prompt_text: str = "",
        stealth_level: str = "balanced",
        **_ignored: Any,
    ) -> str:
        """Execute web browser action."""
        if fields is None:
            fields = []

        # Normalize url: treat "None"/"null"/"undefined" as empty
        _bad = {"none", "null", "undefined", ""}
        if str(url).lower() in _bad:
            url = ""
        # If url is empty but query looks like a URL, use it
        if not url and query and query.startswith(("http://", "https://", "www.")):
            url, query = query, ""

        self._request_count += 1
        timeout = timeout_seconds or self.timeout_seconds
        retries = max_retries or self.max_retries

        try:
            await self._rate_limiter.acquire()

            async def execute_with_circuit_breaker():
                nonlocal url
                # Validate URL if required for original actions
                if action in ("fetch", "browse", "snapshot", "screenshot"):
                    if not url:
                        raise ValueError(
                            f"url parameter is required for action='{action}'. "
                            f"Example: action='{action}', url='https://example.com'"
                        )
                    url = self._validate_url(url)
                elif action == "act":
                    if url:
                        url = self._validate_url(url)

                # ----- Original actions -----
                if action == "fetch":
                    return await self._fetch_with_firecrawl_fallback(url, timeout)
                elif action == "browse":
                    return await self._browse(url, mode, session_id=session_id)
                elif action == "search":
                    if not query:
                        raise ValueError("Query is required for search action")
                    return await self._search(query, search_provider)
                elif action == "snapshot":
                    return await self._snapshot(url, snapshot_mode, session_id, page_id)
                elif action == "act":
                    if not ref:
                        raise ValueError("Ref is required for act action")
                    if not action_type:
                        raise ValueError("Action type is required (click, type, etc.)")
                    return await self._act(
                        ref, action_type, value or None, session_id, page_id
                    )
                elif action == "screenshot":
                    return await self._screenshot(url, mode, session_id)

                # ----- New actions -----
                elif action == "connect":
                    if not cdp_url:
                        raise ValueError("cdp_url is required for connect action")
                    return await self._connect(cdp_url, session_id)
                elif action == "new_page":
                    return await self._new_page(session_id, url)
                elif action == "list_pages":
                    return await self._list_pages(session_id)
                elif action == "switch_page":
                    if not page_id:
                        raise ValueError("page_id is required for switch_page action")
                    return await self._switch_page(session_id, page_id)
                elif action == "close_page":
                    return await self._close_page(session_id, page_id)
                elif action == "get_logs":
                    return await self._get_logs(session_id, log_filter, limit)
                elif action == "breadcrumbs":
                    return await self._breadcrumbs(session_id, limit)
                elif action == "fill_form":
                    if not fields:
                        raise ValueError("fields is required for fill_form action")
                    return await self._fill_form(
                        fields, submit, submit_selector, session_id, page_id
                    )
                elif action == "wait":
                    return await self._wait(session_id, page_id, wait_ms, idle_time)
                elif action == "extract":
                    return await self._extract(pattern, selector, session_id, page_id)
                elif action == "evaluate":
                    if not script:
                        raise ValueError("script is required for evaluate action")
                    return await self._evaluate(script, session_id, page_id)
                elif action == "handle_dialog":
                    return await self._handle_dialog(
                        dialog_action, prompt_text, session_id, page_id
                    )
                elif action == "get_cookies":
                    return await self._get_cookies(session_id)
                elif action == "clear_cookies":
                    return await self._clear_cookies(session_id)
                elif action == "stealth":
                    return await self._stealth(stealth_level, session_id)
                elif action == "diagnose":
                    return await self._diagnose(session_id, page_id)
                else:
                    raise ValueError(f"Unknown action: {action}")

            # Wrap retries inside one circuit-breaker call so each logical
            # request counts as a single event (not one per retry).
            async def execute_with_retries():
                last_err = None
                for attempt in range(retries + 1):
                    try:
                        return await execute_with_circuit_breaker()
                    except ValueError:
                        # Input/validation errors are not service failures — don't retry.
                        raise
                    except Exception as exc:
                        last_err = exc
                        logger.warning(
                            "web_browser_action_retry",
                            action=action, attempt=attempt + 1, error=str(exc),
                        )
                        if attempt < retries:
                            await asyncio.sleep(1 * (attempt + 1))
                raise last_err  # type: ignore[misc]

            try:
                result = await self._circuit_breaker.call(execute_with_retries)

                self._success_count += 1
                self._total_duration_ms += result.duration_ms
                logger.info(
                    "web_browser_action_completed",
                    action=action, url=url,
                    status=result.status,
                    duration_ms=result.duration_ms,
                )
                return result.summary() + "\n\n" + result.content[:DEFAULT_RETURN_CONTENT_SIZE]

            except ValueError as e:
                # Input/validation error — return message directly, no failure counter
                logger.warning("web_browser_input_error", action=action, error=str(e))
                return f"Input error: {e}"
            except Exception as e:
                self._failure_count += 1
                logger.error("web_browser_action_failed", action=action, error=str(e))
                return f"Action failed: {e}"

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
        session_id: str = "default",
        page_id: str = "",
        cdp_url: str = "",
        log_filter: str = "all",
        limit: int = 50,
        fields: List[Dict[str, Any]] = None,
        submit: bool = False,
        submit_selector: str = "",
        wait_ms: int = 2000,
        idle_time: int = 500,
        pattern: str = "all_text",
        selector: str = "body",
        script: str = "",
        dialog_action: str = "accept",
        prompt_text: str = "",
        stealth_level: str = "balanced",
        **_ignored: Any,
    ) -> str:
        """Synchronous wrapper."""
        return asyncio.run(self._arun(
            action=action, url=url, query=query, ref=ref,
            action_type=action_type, value=value, mode=mode,
            snapshot_mode=snapshot_mode, search_provider=search_provider,
            timeout_seconds=timeout_seconds, max_retries=max_retries,
            session_id=session_id, page_id=page_id, cdp_url=cdp_url,
            log_filter=log_filter, limit=limit, fields=fields,
            submit=submit, submit_selector=submit_selector,
            wait_ms=wait_ms, idle_time=idle_time, pattern=pattern,
            selector=selector, script=script, dialog_action=dialog_action,
            prompt_text=prompt_text, stealth_level=stealth_level,
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
                    "sessions": self._browser_manager.get_stats(),
                    "snapshots": len(self._snapshots),
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
        description=(
            "Action to perform. Original: 'fetch', 'browse', 'search', 'snapshot', 'act', 'screenshot'. "
            "New: 'connect', 'new_page', 'list_pages', 'switch_page', 'close_page', "
            "'get_logs', 'breadcrumbs', 'fill_form', 'wait', 'extract', 'evaluate', "
            "'handle_dialog', 'get_cookies', 'clear_cookies', 'stealth', 'diagnose'."
        ),
    )
    url: str = Field(default="", description="Target URL (for fetch, browse, snapshot, screenshot, new_page)")
    query: str = Field(default="", description="Search query (for search)")
    ref: str = Field(default="", description="Element ref from snapshot (for act)")
    action_type: str = Field(default="", description="Action type: click, type, press, hover, select (for act)")
    value: str = Field(default="", description="Value for type/select actions")
    mode: str = Field(default="headless", description="Browser mode: 'headless' or 'headful'")
    snapshot_mode: str = Field(default="ai", description="Snapshot mode: 'ai' or 'role'")
    search_provider: str = Field(default="auto", description="Search provider: 'auto', 'brave', 'duckduckgo'")
    timeout_seconds: int = Field(default=30, ge=5, le=120)
    max_retries: int = Field(default=2, ge=0, le=5)

    # Multi-session / multi-tab
    session_id: str = Field(default="default", description="Browser session ID (for multi-session)")
    page_id: str = Field(default="", description="Tab/page ID within session (empty = active tab)")
    cdp_url: str = Field(default="", description="Chrome DevTools Protocol URL (for connect)")

    # Logging
    log_filter: str = Field(default="all", description="Log filter: 'all', 'console', 'network' (for get_logs)")
    limit: int = Field(default=50, ge=1, le=200, description="Max items to return (for get_logs, breadcrumbs)")

    # Form filling
    fields: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Form fields: [{selector, value, type?}] (for fill_form)",
    )
    submit: bool = Field(default=False, description="Submit after filling (for fill_form)")
    submit_selector: str = Field(default="", description="Submit button selector (for fill_form)")

    # Wait
    wait_ms: int = Field(default=2000, ge=100, le=30000, description="Max wait time in ms (for wait)")
    idle_time: int = Field(default=500, ge=0, le=5000, description="Extra settle time in ms (for wait)")

    # Extract
    pattern: str = Field(
        default="all_text",
        description=(
            "Extraction pattern: 'all_text', 'all_links', 'all_headings', 'tables', "
            "'forms', 'metadata', 'prices', or a CSS selector (for extract)"
        ),
    )
    selector: str = Field(default="body", description="CSS selector scope (for extract)")

    # Evaluate
    script: str = Field(default="", description="JavaScript to evaluate (for evaluate)")

    # Dialog
    dialog_action: str = Field(default="accept", description="'accept' or 'dismiss' (for handle_dialog)")
    prompt_text: str = Field(default="", description="Text for prompt dialogs (for handle_dialog)")

    # Stealth
    stealth_level: str = Field(
        default="balanced",
        description="Stealth level: 'gentle', 'balanced', 'aggressive' (for stealth)",
    )


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
    "BrowserManager",
    "BrowserSession",
    "SnapshotEngine",
    "Snapshot",
    "ElementRef",
    "SearchProvider",
    "SecurityLevel",
    "BrowserMode",
]
