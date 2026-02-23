"""
Security and permissions configuration.

Contains settings for file access control, permissions, and security policies.
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List

from .base import BaseConfig, get_env_bool, get_env_list, expand_path


@dataclass
class SecurityConfig(BaseConfig):
    """
    Security and permissions configuration.

    Attributes:
        permissions_config_path: Path to permissions configuration file
        permissions_audit_log_path: Path to audit log file
        permitted_directories: List of directories agent can access
        additional_blocked_patterns: Additional file patterns to block
        app_monitoring_enabled: Enable application usage monitoring
        require_api_consent: Require user consent for external API calls
    """

    permissions_config_path: Path = field(
        default_factory=lambda: Path.home() / ".opensentinel" / "permissions.json"
    )
    permissions_audit_log_path: Path = field(
        default_factory=lambda: Path.home() / ".opensentinel" / "logs" / "audit.jsonl"
    )
    permitted_directories: List[str] = field(default_factory=list)
    additional_blocked_patterns: List[str] = field(default_factory=list)
    app_monitoring_enabled: bool = False
    require_api_consent: bool = True

    @classmethod
    def from_env(cls) -> "SecurityConfig":
        """Load security configuration from environment variables"""
        # Load paths with expansion
        permissions_config = expand_path(
            os.getenv("PERMISSIONS_CONFIG_PATH", "~/.opensentinel/permissions.json")
        )
        audit_log = expand_path(
            os.getenv("PERMISSIONS_AUDIT_LOG_PATH", "~/.opensentinel/logs/audit.jsonl")
        )

        return cls(
            permissions_config_path=Path(permissions_config),
            permissions_audit_log_path=Path(audit_log),
            permitted_directories=get_env_list("PERMITTED_DIRECTORIES", default=[]),
            additional_blocked_patterns=get_env_list("ADDITIONAL_BLOCKED_PATTERNS", default=[]),
            app_monitoring_enabled=get_env_bool("APP_MONITORING_ENABLED", False),
            require_api_consent=get_env_bool("REQUIRE_API_CONSENT", True),
        )

    def validate(self) -> List[str]:
        """Validate security configuration"""
        errors = []

        # Ensure directories for config and logs can be created
        for path_attr, path_name in [
            (self.permissions_config_path, "permissions_config_path"),
            (self.permissions_audit_log_path, "permissions_audit_log_path"),
        ]:
            try:
                path_attr.parent.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"SecurityConfig: Cannot create directory for {path_name}: {e}")

        return errors

    def ensure_directories(self):
        """Create necessary directories for security files"""
        self.permissions_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.permissions_audit_log_path.parent.mkdir(parents=True, exist_ok=True)
