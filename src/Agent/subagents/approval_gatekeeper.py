"""
Approval Gatekeeper Subagent Configuration

Reviews critical actions requiring human approval and manages permissions.
"""

from ..tools import (
    detect_critical_action,
    create_approval_card,
    validate_safe_automation,
    log_action,
    check_file_permission,
    request_directory_access,
    list_current_permissions,
    redact_pii,
)


def get_config():
    """Returns the approval gatekeeper subagent configuration."""
    return {
        "name": "approval_gatekeeper",
        "description": "Reviews critical actions requiring human approval. Use for sensitive operations.",
        "system_prompt": (
            "You are a safety reviewer. Analyze actions for potential risks, verify safety constraints, "
            "check permissions, and prepare approval requests with clear risk/benefit analysis. Never proceed without explicit approval "
            "for destructive or high-impact operations. Always verify file permissions before sensitive operations."
        ),
        "tools": [
            detect_critical_action,
            create_approval_card,
            validate_safe_automation,
            log_action,
            check_file_permission,
            request_directory_access,
            list_current_permissions,
            redact_pii,
        ],
    }
