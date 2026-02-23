"""
Permission System — Prevent information leakage and enforce access controls
"""

from langchain_core.tools import tool
import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import fnmatch


# ── Permission Configuration ─────────────────────────────────────────
class PermissionManager:
    """Manages file access permissions and security policies."""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or os.path.expanduser("~/.opensentinel/permissions.json")
        self.config = self._load_config()

    def _load_config(self) -> Dict:
        """Load permission configuration or create default."""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r") as f:
                    return json.load(f)
        except Exception:
            pass

        # Default deny-all configuration
        return {
            "permitted_directories": [],
            "blocked_patterns": [
                "*.env",
                "*.key",
                "*.pem",
                "*.ppk",
                "*.keystore",
                "*.p12",
                "credentials*",
                "secrets*",
                "password*",
                ".ssh/*",
                ".aws/*",
                ".config/*",
                ".gnupg/*",
                "AppData/*",
                "Library/Keychains/*",
            ],
            "require_approval_patterns": [
                "*.pdf",  # May contain sensitive documents
                "*.docx",
                "*.xlsx",
            ],
            "app_monitoring_enabled": False,
            "external_api_consent": {},
        }

    def save_config(self):
        """Persist permission configuration."""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(self.config, indent=2, fp=f)

    def is_path_permitted(self, file_path: str) -> tuple[bool, str]:
        """
        Check if file access is permitted.

        Returns:
            (is_permitted: bool, reason: str)
        """
        file_path = os.path.abspath(file_path)
        filename = os.path.basename(file_path)

        # Check blocked patterns first (highest priority)
        for pattern in self.config["blocked_patterns"]:
            if fnmatch.fnmatch(filename, pattern) or fnmatch.fnmatch(file_path, pattern):
                return False, f"Access denied: File matches blocked pattern '{pattern}' (potential sensitive data)"

        # Check if path is within permitted directories
        permitted_dirs = self.config["permitted_directories"]
        if not permitted_dirs:
            return False, "Access denied: No directories have been granted permission (deny by default)"

        for permitted_dir in permitted_dirs:
            permitted_dir = os.path.abspath(permitted_dir)
            try:
                # Check if file_path is within permitted_dir
                Path(file_path).relative_to(permitted_dir)
                return True, "Access granted"
            except ValueError:
                continue

        return False, f"Access denied: Path not in permitted directories"

    def requires_approval(self, file_path: str) -> bool:
        """Check if file access requires explicit user approval."""
        filename = os.path.basename(file_path)
        for pattern in self.config["require_approval_patterns"]:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False

    def grant_directory_access(self, directory: str) -> str:
        """Grant access to a directory."""
        directory = os.path.abspath(directory)
        if directory not in self.config["permitted_directories"]:
            self.config["permitted_directories"].append(directory)
            self.save_config()
            return f"✅ Access granted to: {directory}"
        return f"ℹ️ Directory already permitted: {directory}"

    def revoke_all_access(self) -> str:
        """Emergency revocation of all permissions."""
        self.config["permitted_directories"] = []
        self.config["external_api_consent"] = {}
        self.save_config()
        return "🚨 ALL ACCESS REVOKED. All directory permissions and API consents cleared."

    def sanitize_path_for_logging(self, file_path: str) -> str:
        """Remove sensitive path information for logging."""
        # Return only filename, not full path
        return os.path.basename(file_path)


# Global permission manager instance
_permission_manager = None


def get_permission_manager() -> PermissionManager:
    """Get or create the global permission manager."""
    global _permission_manager
    if _permission_manager is None:
        _permission_manager = PermissionManager()
    return _permission_manager


# ── Permission Tools ─────────────────────────────────────────────────


@tool
def check_file_permission(file_path: str) -> str:
    """
    Check if agent has permission to access a file.

    Args:
        file_path: Path to file to check

    Returns:
        Permission status and reasoning
    """
    pm = get_permission_manager()
    is_permitted, reason = pm.is_path_permitted(file_path)

    return json.dumps(
        {
            "file": pm.sanitize_path_for_logging(file_path),
            "permitted": is_permitted,
            "reason": reason,
            "requires_approval": pm.requires_approval(file_path) if is_permitted else False,
        },
        indent=2,
    )


@tool
def request_directory_access(directory: str, justification: str) -> str:
    """
    Request user permission to access a directory.

    Args:
        directory: Directory path to request access to
        justification: Explanation of why access is needed

    Returns:
        Approval card for user decision
    """
    pm = get_permission_manager()

    approval_card = {
        "type": "directory_access_request",
        "action": f"Grant read access to directory: {directory}",
        "justification": justification,
        "impact": "Agent will be able to list and read files in this directory and subdirectories",
        "risk": "medium",
        "blocked_patterns_info": "The following patterns will always be blocked: .env, *.key, credentials*, .ssh/*, etc.",
        "options": {
            "approve": "Grant access to this directory",
            "deny": "Deny access request",
            "approve_readonly": "Grant read-only access (no file modifications)",
        },
        "note": "You can revoke access at any time with /revoke-all-access",
    }

    return json.dumps(approval_card, indent=2)


@tool
def revoke_all_permissions() -> str:
    """
    Emergency revocation of all file access and API permissions.
    Use when suspicious activity detected or user requests full lockdown.

    Returns:
        Confirmation of revocation
    """
    pm = get_permission_manager()
    result = pm.revoke_all_access()

    return json.dumps(
        {
            "status": "revoked",
            "message": result,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "next_steps": "To re-enable access, user must explicitly grant directory permissions again",
        },
        indent=2,
    )


@tool
def list_current_permissions() -> str:
    """
    Show what directories and APIs the agent currently has access to.

    Returns:
        Current permission configuration
    """
    pm = get_permission_manager()

    return json.dumps(
        {
            "permitted_directories": pm.config["permitted_directories"],
            "blocked_patterns": pm.config["blocked_patterns"][:10],  # First 10 for brevity
            "app_monitoring_enabled": pm.config["app_monitoring_enabled"],
            "external_api_consents": list(pm.config["external_api_consent"].keys()),
            "note": "User can revoke all access with /revoke-all-access command",
        },
        indent=2,
    )


@tool
def redact_pii(text: str) -> str:
    """
    Redact personally identifiable information before sending to external APIs.

    Args:
        text: Text that may contain PII

    Returns:
        Redacted text with PII replaced by placeholders
    """
    import re

    redacted = text

    # Email addresses
    redacted = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]", redacted)

    # Phone numbers (various formats)
    redacted = re.sub(r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]", redacted)
    redacted = re.sub(r"\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]", redacted)

    # Social Security Numbers (US)
    redacted = re.sub(r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]", redacted)

    # Credit card numbers
    redacted = re.sub(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b", "[CARD_REDACTED]", redacted)

    # IP addresses
    redacted = re.sub(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "[IP_REDACTED]", redacted)

    # Common paths that might leak usernames
    redacted = re.sub(r"/home/[^/\s]+/", "/home/[USER]/", redacted)
    redacted = re.sub(r"C:\\Users\\[^\\]+\\", "C:\\Users\\[USER]\\", redacted)

    return json.dumps(
        {
            "original_length": len(text),
            "redacted_text": redacted,
            "redacted_length": len(redacted),
            "pii_found": redacted != text,
        },
        indent=2,
    )
