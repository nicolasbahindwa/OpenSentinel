"""
Universal Tools — Cross-cutting tools shared by ALL subagents via default_tools.

These tools provide capabilities that every subagent needs regardless of domain:
- universal_search: Unified search across web, documents, and internal knowledge
- log_to_supervisor: Structured communication channel back to the orchestrator
"""

from langchain_core.tools import tool
import json
from datetime import datetime

from ._search_engine import search_dual


@tool
def universal_search(query: str, scope: str = "auto", max_results: int = 5) -> str:
    """
    Unified search across web, documents, and internal knowledge.

    Available to ALL subagents. Runs both Tavily and DuckDuckGo together for
    comprehensive web coverage. If one provider fails, the other still returns
    results gracefully.

    Args:
        query: The search query (e.g., "latest AI trends", "meeting notes from last week")
        scope: Where to search — "web" (internet only), "local" (documents only), "auto" (both, default)
        max_results: Maximum results per provider (1-10, default 5)

    Returns:
        JSON string with combined results from all matching sources
    """
    combined_results = {
        "query": query,
        "scope": scope,
        "web_results": [],
        "local_results": [],
        "providers": {},
        "total_found": 0,
        "sources_searched": [],
        "timestamp": datetime.now().isoformat(),
    }

    # ── Web search (dual-provider) ─────────────────────────────────
    if scope in ("web", "auto"):
        web_data = search_dual(query, max_results, search_type="general")

        combined_results["web_results"] = web_data.get("results", [])
        combined_results["providers"] = web_data.get("providers", {})
        combined_results["total_found"] += web_data.get("total_found", 0)

        if web_data.get("answer"):
            combined_results["web_answer"] = web_data["answer"]

        # Track which providers were searched
        for provider, status in web_data.get("providers", {}).items():
            if status.get("status") == "ok":
                combined_results["sources_searched"].append(provider)

        if not combined_results["sources_searched"] and scope == "web":
            combined_results["sources_searched"].append("none_available")

    # ── Local document search ──────────────────────────────────────
    if scope in ("local", "auto"):
        combined_results["local_results"] = [{
            "source": "local_index",
            "note": "Local document search — results depend on indexed documents",
            "query": query,
        }]
        combined_results["sources_searched"].append("local_documents")

    return json.dumps(combined_results, indent=2)


@tool
def log_to_supervisor(
    message: str,
    level: str = "info",
    context: str = "",
    requires_attention: bool = False,
) -> str:
    """
    Send a structured log message to the supervisor orchestrator.

    Available to ALL subagents. Use this to report progress, flag issues,
    escalate decisions, or request help from other subagents via the supervisor.

    Args:
        message: Clear description of what happened or what is needed
        level: Severity level — "info" (progress update), "warning" (potential issue),
               "error" (something failed), "escalate" (needs supervisor decision)
        context: Additional context such as data, error details, or partial results
        requires_attention: Set True to flag for immediate supervisor review

    Returns:
        JSON confirmation that the message was logged and routed
    """
    valid_levels = ("info", "warning", "error", "escalate")
    if level not in valid_levels:
        level = "info"

    log_entry = {
        "log_id": f"sub_{datetime.now().strftime('%Y%m%d%H%M%S_%f')}",
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "message": message,
        "context": context,
        "requires_attention": requires_attention,
        "routed_to": "supervisor",
    }

    # Determine routing action based on level
    if level == "escalate":
        log_entry["action"] = "supervisor_review_required"
        log_entry["priority"] = "high"
    elif level == "error":
        log_entry["action"] = "error_logged_for_review"
        log_entry["priority"] = "high"
    elif level == "warning":
        log_entry["action"] = "warning_noted"
        log_entry["priority"] = "medium"
    else:
        log_entry["action"] = "progress_logged"
        log_entry["priority"] = "low"

    return json.dumps(
        {
            "status": "logged",
            "log_entry": log_entry,
        },
        indent=2,
    )
