import os
import asyncio
from typing import Optional, Type, ClassVar

from tavily import TavilyClient
from pydantic import BaseModel, Field, PrivateAttr
from langchain_core.tools import BaseTool
from cachetools import TTLCache


# ==============================
# Input Schema
# ==============================

class SearchInput(BaseModel):
    query: str = Field(..., min_length=1, description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Number of results (1-20)")
    search_depth: str = Field(default="basic", description="basic or advanced")


# ==============================
# Tool Implementation
# ==============================

class TavilySearchTool(BaseTool):
    name: str = "internet_search"
    description: str = (
        "Search the internet for current, real-time information. "
        "Use this tool when you need: "
        "1) Current events, news, or recent developments "
        "2) Facts, statistics, or data you don't have "
        "3) Information after January 2025 "
        "4) Product details, company info, or people "
        "5) Any user request containing 'search', 'look up', 'find', or 'latest'. "
        "Returns a summary with cited sources and URLs."
    )
    args_schema: Type[BaseModel] = SearchInput
    handle_tool_error: bool = True

    _client: TavilyClient = PrivateAttr()
    _cache: TTLCache = PrivateAttr()

    MAX_CONTENT_CHARS: ClassVar[int] = 500  # prevent token explosion

    def __init__(self, api_key: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)

        api_key = api_key or os.environ.get("TAVILY_API_KEY")
        if not api_key:
            raise ValueError("TAVILY_API_KEY environment variable required")

        self._client = TavilyClient(api_key=api_key)
        self._cache = TTLCache(maxsize=500, ttl=3600)  # 1 hour cache

    # ------------------------------
    # Sync version
    # ------------------------------

    def _run(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
    ) -> str:

        cache_key = f"{query}:{max_results}:{search_depth}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        try:
            response = self._client.search(
                query=query,
                max_results=max_results,
                search_depth=search_depth,
                include_answer=True,
                include_raw_content=False,
            )
        except Exception as e:
            raise RuntimeError(f"Tavily API error: {str(e)}") from e

        results = response.get("results", [])

        if not results:
            return "No relevant results found."

        output_sections = []

        # ---------- Summary ----------
        if response.get("answer"):
            output_sections.append(
                "=== SUMMARY ===\n"
                f"{response['answer'].strip()}\n"
            )

        # ---------- Sources ----------
        output_sections.append("=== SOURCES ===")

        for idx, r in enumerate(results, start=1):
            title = r.get("title", "No title")
            url = r.get("url", "No URL")
            content = (r.get("content") or "").strip()

            # Safe truncation
            if len(content) > self.MAX_CONTENT_CHARS:
                content = content[:self.MAX_CONTENT_CHARS] + "..."

            output_sections.append(
                f"\n[{idx}] {title}\n"
                f"{content}\n"
                f"URL: {url}"
            )

        formatted = "\n".join(output_sections)

        self._cache[cache_key] = formatted
        return formatted

    # ------------------------------
    # Async version (non-blocking)
    # ------------------------------

  