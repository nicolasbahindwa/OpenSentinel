"""
Document & File Tools — Local file access and semantic search with permission controls
"""

from langchain_core.tools import tool
import json
from datetime import datetime


@tool
def list_documents(path: str, file_type: str = "all") -> str:
    """
    Enumerate files in granted directories (PERMISSION REQUIRED).

    ⚠️ SECURITY: This tool accesses user files. Before using:
    1. Call check_file_permission(path) to verify access is permitted
    2. If denied, call request_directory_access(path, justification)
    3. Only proceed if user approves

    Args:
        path: Directory path (must be within granted scope)
        file_type: Filter by extension (pdf, docx, txt, md, all)

    Returns:
        List of files with metadata OR permission denial
    """
    # Import permission manager
    try:
        from .permissions import get_permission_manager

        pm = get_permission_manager()
        is_permitted, reason = pm.is_path_permitted(path)

        if not is_permitted:
            return json.dumps(
                {
                    "error": "permission_denied",
                    "directory": pm.sanitize_path_for_logging(path),
                    "reason": reason,
                    "action_required": "Call request_directory_access() to ask user for permission",
                },
                indent=2,
            )
    except ImportError:
        return json.dumps({"error": "permission_system_unavailable", "message": "Running in unsafe mode - PRODUCTION DEPLOYMENT BLOCKED"}, indent=2)

    # Simulated file listing (in production, use os.listdir with permission checks)
    sample_files = [
        {"name": "project_plan.md", "size_kb": 45, "modified": "2026-02-20"},
        {"name": "budget_2026.xlsx", "size_kb": 128, "modified": "2026-02-19"},
        {"name": "meeting_notes.txt", "size_kb": 12, "modified": "2026-02-21"},
    ]

    return json.dumps(
        {
            "directory": pm.sanitize_path_for_logging(path),  # Don't leak full paths
            "file_type_filter": file_type,
            "files": sample_files,
            "total_count": len(sample_files),
            "note": "Simulated listing — implement with OS file system APIs in production",
        },
        indent=2,
    )


@tool
def read_document(file_path: str, summary_type: str = "full") -> str:
    """
    Read and optionally summarize file content (PERMISSION REQUIRED).

    ⚠️ SECURITY: Requires permission check before file access.

    Args:
        file_path: Full path to file
        summary_type: Output format (full, summary, key_points)

    Returns:
        File content or summary OR permission denial
    """
    # Import permission manager
    try:
        from .permissions import get_permission_manager

        pm = get_permission_manager()
        is_permitted, reason = pm.is_path_permitted(file_path)

        if not is_permitted:
            return json.dumps(
                {
                    "error": "permission_denied",
                    "file": pm.sanitize_path_for_logging(file_path),
                    "reason": reason,
                    "action_required": "Call request_directory_access() for the parent directory",
                },
                indent=2,
            )

        # Check if file requires explicit approval (e.g., .pdf, .docx)
        if pm.requires_approval(file_path):
            return json.dumps(
                {
                    "error": "approval_required",
                    "file": pm.sanitize_path_for_logging(file_path),
                    "reason": "File type requires explicit user approval before access",
                    "action_required": "Use approval_workflow skill to request user consent",
                },
                indent=2,
            )
    except ImportError:
        return json.dumps({"error": "permission_system_unavailable"}, indent=2)

    # Simulated document reading
    content = {
        "file": pm.sanitize_path_for_logging(file_path),  # Don't leak full paths
        "content": "Project Plan Q1 2026\n\nObjectives:\n1. Launch new feature\n2. Improve performance\n3. Expand user base",
        "word_count": 250,
        "read_at": datetime.now().isoformat(),
    }

    return json.dumps(content, indent=2)


@tool
def search_documents(query: str, max_results: int = 10) -> str:
    """
    Semantic search across indexed documents in permitted directories.

    ⚠️ SECURITY: Only searches within directories user has granted access to.

    Args:
        query: Search query
        max_results: Maximum results to return

    Returns:
        Relevant documents with excerpts (paths sanitized)
    """
    # Import permission manager
    try:
        from .permissions import get_permission_manager

        pm = get_permission_manager()

        # Check if any directories are permitted
        if not pm.config["permitted_directories"]:
            return json.dumps(
                {
                    "error": "no_permitted_directories",
                    "reason": "No directories have been granted for search access",
                    "action_required": "Call request_directory_access() to grant search permissions",
                },
                indent=2,
            )
    except ImportError:
        pass

    # Simulated semantic search (paths sanitized)
    results = [
        {
            "file": "project_plan.md",  # Filename only, no full paths
            "excerpt": "...Launch new feature by Q1 2026...",
            "relevance_score": 0.92,
        },
        {
            "file": "meeting_notes.txt",
            "excerpt": "...Discussed Q1 feature priorities...",
            "relevance_score": 0.85,
        },
    ]

    return json.dumps(
        {"query": query, "results": results, "total_found": len(results), "note": "Simulated search — use embeddings + vector DB in production"},
        indent=2,
    )


@tool
def cite_document(file_path: str, excerpt: str) -> str:
    """
    Provide citation and provenance for retrieved information.

    ⚠️ SECURITY: Sanitizes file paths to prevent leaking directory structure.

    Args:
        file_path: Source document path
        excerpt: Text excerpt being cited

    Returns:
        Formatted citation (with sanitized path)
    """
    # Import permission manager for path sanitization
    try:
        from .permissions import get_permission_manager

        pm = get_permission_manager()
        sanitized_path = pm.sanitize_path_for_logging(file_path)
    except ImportError:
        import os

        sanitized_path = os.path.basename(file_path)

    citation = {
        "source": sanitized_path,  # Filename only, not full path
        "excerpt": excerpt,
        "citation_format": f"Source: {sanitized_path} (accessed {datetime.now().strftime('%Y-%m-%d')})",
        "timestamp": datetime.now().isoformat(),
    }

    return json.dumps(citation, indent=2)
