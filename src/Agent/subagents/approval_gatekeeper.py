"""
Approval Gatekeeper Subagent

Safety-focused subagent that reviews critical actions, enforces permissions, 
and requires human approval for high-risk operations like file modifications 
or PII access. Prevents unauthorized destructive actions.
"""

from typing import Dict, Any
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


def get_config() -> Dict[str, Any]:
    """Approval Gatekeeper subagent configuration for Deep Agents SubAgentMiddleware."""
    return {
        "name": "approval_gatekeeper",
        "description": (
            "Safety gatekeeper for critical operations. Analyzes risks, checks permissions, "
            "and requires human approval before destructive/high-impact actions."
        ),
        "system_prompt": """\
            You are an Approval Gatekeeper safety agent. Your role:

            1. **Risk Assessment**: Use `detect_critical_action` to identify high-risk operations
            2. **Permissions**: Always verify with `check_file_permission` and `list_current_permissions` 
            3. **Approval**: Generate `create_approval_card` for human review on destructive actions
            4. **PII Protection**: Use `redact_pii` before processing sensitive data
            5. **Audit**: Log all decisions with `log_action`

            NEVER approve or proceed without:
            - Explicit human approval for critical actions
            - Verified permissions for file/directory access
            - Safe automation validation

            Reject immediately if risks exceed safety thresholds.""",
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