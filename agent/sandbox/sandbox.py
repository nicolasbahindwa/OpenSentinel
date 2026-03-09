from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import re
import shlex
import shutil
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime
from json import JSONEncoder
from pathlib import Path
from typing import Any, Optional

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox

logger = logging.getLogger(__name__)


# =============================================================================
# Type Definitions
# =============================================================================

@dataclass
class SandboxMetrics:
    """Metrics for monitoring and observability."""
    executed_commands: int = 0
    files_uploaded: int = 0
    files_downloaded: int = 0
    total_timeout_events: int = 0
    total_errors: int = 0
    blocked_commands: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)


@dataclass
class DangerousPatternRule:
    """Rule for detecting potentially dangerous commands."""
    pattern: re.Pattern
    description: str


# =============================================================================
# Custom Errors
# =============================================================================

class SandboxError(Exception):
    """Base exception for sandbox-related errors."""
    pass


class SandboxInitializationError(SandboxError):
    """Raised when sandbox initialization fails."""
    pass


class InvalidCommandError(SandboxError):
    """Raised when command is invalid."""
    pass


class CommandNotAllowedError(SandboxError):
    """Raised when a command is not in the allowlist."""
    pass


class InvalidPathError(SandboxError):
    """Raised when a path is invalid."""
    pass


class PathTraversalError(SandboxError):
    """Raised when path traversal is detected."""
    pass


# =============================================================================
# Utility Functions
# =============================================================================

class _SafeJSONEncoder(JSONEncoder):
    """JSON encoder that falls back to str() for non-serializable objects."""

    def default(self, obj: Any) -> Any:
        return str(obj)


def error_to_log_context(error: Exception | str | Any) -> dict[str, Any]:
    """Convert an error to a structured log context."""
    if isinstance(error, Exception):
        return {
            "name": error.__class__.__name__,
            "message": str(error),
        }
    elif isinstance(error, str):
        return {"message": error}
    else:
        return {"error": str(error)}


# =============================================================================
# Logger
# =============================================================================

class SandboxLogger:
    """Structured logger for sandbox operations."""

    def __init__(self, debug: bool = False):
        self.debug = debug
        self.prefix = "[LocalSandbox]"

    def _safe_json(self, obj: Any) -> str:
        """Serialize to JSON safely, falling back to str() for unknown types."""
        return json.dumps(obj, cls=_SafeJSONEncoder)

    def info(self, message: str, context: dict[str, Any] | None = None) -> None:
        context_str = f" | {self._safe_json(context)}" if context else ""
        logger.info(f"{self.prefix} {message}{context_str}")

    def warn(self, message: str, context: dict[str, Any] | None = None) -> None:
        context_str = f" | {self._safe_json(context)}" if context else ""
        logger.warning(f"{self.prefix} {message}{context_str}")

    def error(self, message: str, error: Exception | str | Any | None = None) -> None:
        error_context = error_to_log_context(error) if error else None
        context_str = f" | {self._safe_json(error_context)}" if error_context else ""
        logger.error(f"{self.prefix} {message}{context_str}")

    def debug_log(self, message: str, context: dict[str, Any] | None = None) -> None:
        if self.debug:
            context_str = f" | {self._safe_json(context)}" if context else ""
            logger.debug(f"{self.prefix} {message}{context_str}")


# =============================================================================
# Security & Configuration Constants
# =============================================================================

# Environment variables safe to expose to sandboxed commands
SAFE_ENV_VARS: set[str] = {
    # POSIX / shell essentials
    "PATH", "HOME", "USER", "SHELL", "TERM", "LANG", "LC_ALL",
    "TMPDIR", "XDG_RUNTIME_DIR",
    # Runtime paths for Python / Node
    "NODE_PATH", "PYTHONPATH", "VIRTUAL_ENV",
    # Display (headless check)
    "DISPLAY",
    # Timezone
    "TZ",
}

# Commands allowed to execute. Set to None to disable allowlist (not recommended).
DEFAULT_ALLOWED_COMMANDS: set[str] | None = {
    # Shell builtins / core utils
    "echo", "cat", "head", "tail", "wc", "sort", "uniq", "tr", "cut",
    "grep", "sed", "awk", "find", "ls", "pwd", "date", "env", "printenv",
    "test", "true", "false", "expr", "seq", "tee", "xargs",
    # File operations
    "mkdir", "cp", "mv", "touch", "rm", "ln", "readlink", "realpath",
    "basename", "dirname", "stat", "file", "diff",
    # Python
    "python", "python3", "pip", "pip3",
    # Node
    "node", "npm", "npx",
    # Git
    "git",
    # Network (read-only fetching)
    "curl", "wget",
    # Archive
    "tar", "zip", "unzip", "gzip", "gunzip",
    # Text processing
    "jq", "yq",
    # Misc
    "which", "whoami", "uname", "sleep",
}

# Dangerous command patterns that warrant logging/blocking
DANGEROUS_PATTERNS: list[DangerousPatternRule] = [
    DangerousPatternRule(re.compile(r"\brm\s+-[a-z]*r[a-z]*f?\s+[/~]"), "rm -rf on root or home"),
    DangerousPatternRule(re.compile(r"\bdd\s+.*of="), "dd write operations"),
    DangerousPatternRule(re.compile(r"\bmkfs\b"), "filesystem format"),
    DangerousPatternRule(re.compile(r"\bchmod\s+-R\s+777"), "world-writable recursion"),
    DangerousPatternRule(re.compile(r"\bcurl\b.*\|\s*(sh|bash|zsh)"), "curl piped to shell"),
    DangerousPatternRule(re.compile(r"\bwget\b.*\|\s*(sh|bash|zsh)"), "wget piped to shell"),
    DangerousPatternRule(re.compile(r"\b(python|python3|node)\s+-c\s+.*\b(exec|eval|import\s+os)\b"), "inline code execution with dangerous imports"),
    DangerousPatternRule(re.compile(r"\bbase64\b.*\|\s*(sh|bash|zsh|python)"), "base64 decode piped to interpreter"),
    DangerousPatternRule(re.compile(r">\s*/dev/sd[a-z]"), "write to block device"),
    DangerousPatternRule(re.compile(r"\b(nc|ncat|netcat)\b.*-[a-z]*l"), "netcat listener"),
    # Command substitution / injection
    DangerousPatternRule(re.compile(r"\$\("), "command substitution $()"),
    DangerousPatternRule(re.compile(r"`[^`]+`"), "backtick command substitution"),
    DangerousPatternRule(re.compile(r"\$\{.*[^}]*\}"), "variable expansion"),
    # Reverse shells
    DangerousPatternRule(re.compile(r"\b(bash|sh|zsh)\s+-i\s+>&"), "reverse shell attempt"),
    DangerousPatternRule(re.compile(r"/dev/tcp/"), "bash /dev/tcp reverse shell"),
    # Process injection
    DangerousPatternRule(re.compile(r"\bkill\s+-9\b"), "forced process kill"),
    DangerousPatternRule(re.compile(r"\bpkill\b"), "process kill by name"),
]

DEFAULT_TIMEOUT_MS = 30_000
DEFAULT_MAX_OUTPUT_SIZE = 50_000
DEFAULT_MAX_CONCURRENT = 10
MIN_TIMEOUT_MS = 1_000
MIN_MAX_OUTPUT_SIZE = 1_024


# =============================================================================
# LocalSandbox Implementation
# =============================================================================

class LocalSandboxConfig:
    """Configuration for LocalSandbox."""

    def __init__(
        self,
        workspace: str,
        path_mappings: dict[str, str] | None = None,
        timeout_ms: int | None = None,
        max_output_size: int | None = None,
        debug: bool = False,
        max_concurrent: int | None = None,
        allowed_commands: set[str] | None = DEFAULT_ALLOWED_COMMANDS,
    ):
        """Initialize sandbox configuration.

        Args:
            workspace: Root workspace directory (must be absolute path).
            path_mappings: Virtual prefix -> real prefix mappings.
            timeout_ms: Command execution timeout in milliseconds.
            max_output_size: Maximum output capture size in bytes.
            debug: Enable debug logging.
            max_concurrent: Maximum number of concurrent executions.
            allowed_commands: Set of allowed base commands. None disables allowlist.
        """
        self.workspace = workspace
        self.path_mappings = path_mappings or {}
        self.timeout_ms = timeout_ms or DEFAULT_TIMEOUT_MS
        self.max_output_size = max_output_size or DEFAULT_MAX_OUTPUT_SIZE
        self.debug = debug
        self.max_concurrent = max_concurrent or DEFAULT_MAX_CONCURRENT
        self.allowed_commands = allowed_commands


class LocalSandbox(BaseSandbox):
    """Secure local sandbox extending deepagents BaseSandbox.

    Provides async subprocess-based code execution with:
    - Command allowlist validation
    - Virtual path resolution (/skills/ -> real/path/skills/)
    - Async streaming output with size limits
    - Timeout enforcement via asyncio.wait_for
    - Environment variable filtering
    - Semaphore-based concurrency control
    - Async context manager for reliable cleanup
    - Comprehensive metrics and logging

    Example:
        >>> async with create_local_sandbox(
        ...     workspace="/tmp/sandbox",
        ...     debug=True,
        ... ) as sandbox:
        ...     result = await sandbox.execute("echo 'Hello'")
        ...     print(result.output)  # "Hello"
    """

    def __init__(self, config: LocalSandboxConfig):
        """Initialize LocalSandbox with configuration.

        Args:
            config: LocalSandboxConfig instance.

        Raises:
            SandboxInitializationError: If workspace creation fails.
            ValueError: If configuration is invalid.
        """
        super().__init__()

        self._validate_config(config)

        self._id = str(uuid.uuid4())
        self.workspace = config.workspace
        self.timeout_ms = config.timeout_ms
        self.max_output_size = config.max_output_size
        self.max_concurrent = config.max_concurrent
        self.allowed_commands = config.allowed_commands
        self.logger = SandboxLogger(debug=config.debug)
        self.active_processes: dict[str, asyncio.subprocess.Process] = {}
        self.metrics = SandboxMetrics()
        self._semaphore: asyncio.Semaphore | None = None  # lazy-init inside event loop
        self._semaphore_lock: asyncio.Lock | None = None  # guards lazy-init

        # Sort mappings longest-prefix-first to handle overlapping paths correctly
        sorted_mappings = sorted(
            config.path_mappings.items(),
            key=lambda x: len(x[0]),
            reverse=True,
        )
        self.sorted_mappings: list[tuple[str, str]] = sorted_mappings

        # Initialize workspace
        try:
            Path(self.workspace).mkdir(parents=True, exist_ok=True)
            self.logger.info(
                "Sandbox initialized",
                {
                    "id": self._id,
                    "workspace": self.workspace,
                    "timeout": self.timeout_ms,
                    "max_output": self.max_output_size,
                    "max_concurrent": self.max_concurrent,
                    "allowlist_enabled": self.allowed_commands is not None,
                },
            )
        except Exception as error:
            self.logger.error("Failed to initialize workspace", error)
            raise SandboxInitializationError(
                f"Failed to initialize workspace at {self.workspace}"
            ) from error

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> LocalSandbox:
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        await self.async_shutdown()
        return False

    # ------------------------------------------------------------------
    # Abstract property implementation
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        """Unique identifier for the sandbox backend."""
        return self._id

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_config(config: LocalSandboxConfig) -> None:
        """Validate configuration parameters."""
        if not config.workspace:
            raise ValueError("Workspace path is required")

        workspace_path = Path(config.workspace).resolve()
        if not workspace_path.is_absolute():
            raise ValueError("Workspace must be an absolute path")

        if config.timeout_ms < MIN_TIMEOUT_MS:
            raise ValueError(f"Timeout must be at least {MIN_TIMEOUT_MS}ms")

        if config.max_output_size < MIN_MAX_OUTPUT_SIZE:
            raise ValueError(f"Max output size must be at least {MIN_MAX_OUTPUT_SIZE} bytes")

        if config.max_concurrent < 1:
            raise ValueError("Max concurrent executions must be at least 1")

    # Shell operators that allow chaining arbitrary commands
    _SHELL_OPERATORS = re.compile(
        r"[;`]"            # semicolon, backtick
        r"|&&"             # logical AND
        r"|\|\|"           # logical OR
        r"|\$\("           # command substitution $(...)
        r"|\$\{"           # variable expansion ${...}
        r"|\|(?!\|)"       # single pipe (but not ||, handled above)
    )

    def _validate_command(self, command: str) -> None:
        """Validate command against the allowlist and block shell operators.

        Rejects commands containing shell chaining operators (;, &&, ||, |,
        ``, $(), ${}) that could bypass the single-command allowlist.
        Then extracts the base command (first token, stripping path prefixes)
        and checks it against the allowed set.

        Raises:
            CommandNotAllowedError: If the command is not allowed.
        """
        if self.allowed_commands is None:
            return

        # Block shell operators that chain multiple commands
        # Strip quoted strings first so operators inside quotes don't trigger
        unquoted = re.sub(r"'[^']*'", "", command)       # strip single-quoted
        unquoted = re.sub(r'"[^"]*"', "", unquoted)       # strip double-quoted

        if self._SHELL_OPERATORS.search(unquoted):
            self.metrics.blocked_commands += 1
            self.logger.warn(
                "Command blocked: shell operator detected",
                {"command": command[:100]},
            )
            raise CommandNotAllowedError(
                "Shell operators (;, &&, ||, |, ``, $()) are not allowed"
            )

        # Extract the first token as the base command
        try:
            tokens = shlex.split(command)
        except ValueError:
            # shlex can't parse — fall back to simple split
            tokens = command.split()

        if not tokens:
            return

        # Strip path prefix (e.g. /usr/bin/python -> python)
        base_cmd = Path(tokens[0]).name

        if base_cmd not in self.allowed_commands:
            self.metrics.blocked_commands += 1
            self.logger.warn(
                "Command blocked by allowlist",
                {"base_command": base_cmd, "command": command[:100]},
            )
            raise CommandNotAllowedError(
                f"Command '{base_cmd}' is not in the allowed command list"
            )

    # ------------------------------------------------------------------
    # Path resolution
    # ------------------------------------------------------------------

    def _resolve_virtual_paths(self, command: str) -> str:
        """Resolve virtual paths in commands to real filesystem paths.

        Tokenizes the command by splitting on whitespace and quote characters,
        then replaces matching virtual prefixes in each token.

        Args:
            command: Command string potentially containing virtual paths.

        Returns:
            Command with virtual paths resolved.
        """
        resolved = command

        for prefix, real_prefix in self.sorted_mappings:
            # Split on whitespace and quote boundaries, replace in each token
            tokens = re.split(r'(\s+|["\'\`])', resolved)
            for i, token in enumerate(tokens):
                if token.startswith(prefix):
                    tokens[i] = real_prefix + token[len(prefix):]
            resolved = "".join(tokens)

        return resolved

    def _build_safe_env(self) -> dict[str, str]:
        """Build a filtered environment containing only safe variables."""
        env = {}
        for key in SAFE_ENV_VARS:
            value = os.environ.get(key)
            if value is not None:
                env[key] = value
        return env

    def _build_subprocess_kwargs(self) -> dict[str, Any]:
        """Build platform-aware subprocess kwargs with resource limits.

        On Unix/Linux, sets preexec_fn to limit:
        - CPU time: 60s soft / 120s hard
        - File size: 50 MB
        - Number of processes: 64
        - Open files: 256

        On Windows, returns empty dict (resource module not available).
        """
        if platform.system() == "Windows":
            return {}

        import resource

        def _set_limits() -> None:
            # CPU time (seconds): soft 60s, hard 120s
            resource.setrlimit(resource.RLIMIT_CPU, (60, 120))
            # File size: 50 MB
            resource.setrlimit(resource.RLIMIT_FSIZE, (50 * 1024 * 1024, 50 * 1024 * 1024))
            # Number of child processes
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
            # Open file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (256, 256))

        return {"preexec_fn": _set_limits}

    def _check_dangerous_patterns(self, command: str) -> None:
        """Check command for dangerous patterns and log warnings."""
        for rule in DANGEROUS_PATTERNS:
            if rule.pattern.search(command):
                self.logger.warn(
                    "Potentially dangerous operation detected",
                    {
                        "type": rule.description,
                        "command": command[:100],
                    },
                )
                break

    # ------------------------------------------------------------------
    # Command execution (fully async)
    # ------------------------------------------------------------------

    async def _read_output(
        self,
        process: asyncio.subprocess.Process,
    ) -> tuple[str, bool]:
        """Read process stdout asynchronously with size limits.

        Returns:
            Tuple of (output_text, was_truncated).
        """
        output = ""
        truncated = False

        assert process.stdout is not None

        while True:
            line_bytes = await process.stdout.readline()
            if not line_bytes:
                break

            line = line_bytes.decode("utf-8", errors="replace")
            remaining = self.max_output_size - len(output)

            if remaining <= 0:
                truncated = True
                break

            if len(line) <= remaining:
                output += line
            else:
                output += line[:remaining]
                truncated = True
                break

        return output, truncated

    async def _ensure_semaphore(self) -> asyncio.Semaphore:
        """Thread-safe lazy initialization of the concurrency semaphore.

        Uses an asyncio.Lock to prevent multiple coroutines from
        creating duplicate semaphores during concurrent first-access.
        """
        if self._semaphore is not None:
            return self._semaphore

        # Bootstrap the lock on first call (single-threaded asyncio guarantees
        # this initial check + assignment is atomic within one event loop tick)
        if self._semaphore_lock is None:
            self._semaphore_lock = asyncio.Lock()

        async with self._semaphore_lock:
            # Double-check after acquiring the lock
            if self._semaphore is None:
                self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def _kill_process_safe(self, process: asyncio.subprocess.Process) -> None:
        """Kill a process and wait for it to exit, handling edge cases."""
        try:
            if process.returncode is None:
                process.kill()
        except ProcessLookupError:
            pass
        # Always await wait() to reap the zombie process
        try:
            await asyncio.wait_for(process.wait(), timeout=5.0)
        except asyncio.TimeoutError:
            self.logger.warn("Process did not exit after kill within 5s")

    async def execute(self, command: str, *, timeout: int | None = None) -> ExecuteResponse:
        """Execute a shell command with timeout, output limits, and concurrency control.

        Uses asyncio.create_subprocess_shell for non-blocking I/O and
        asyncio.wait_for for clean timeout handling.

        Args:
            command: Shell command to execute.
            timeout: Override timeout in seconds. If None, uses configured timeout_ms.

        Returns:
            ExecuteResponse with output, exit code, and metadata.

        Raises:
            InvalidCommandError: If command is invalid.
            CommandNotAllowedError: If command is not in the allowlist.
        """
        if not command or not isinstance(command, str):
            self.metrics.total_errors += 1
            raise InvalidCommandError("Command must be a non-empty string")

        # Validate against allowlist before anything else
        self._validate_command(command)

        # Allow per-call timeout override (seconds -> ms), fall back to config
        effective_timeout_ms = (timeout * 1000) if timeout is not None else self.timeout_ms

        # Thread-safe lazy-init semaphore inside the running event loop
        semaphore = await self._ensure_semaphore()

        async with semaphore:
            self.metrics.executed_commands += 1

            resolved = self._resolve_virtual_paths(command)
            self._check_dangerous_patterns(resolved)

            self.logger.debug_log(
                "Executing command",
                {
                    "original": command[:80],
                    "resolved": resolved[:80],
                },
            )

            execution_id = str(uuid.uuid4())
            timed_out = False
            process: asyncio.subprocess.Process | None = None

            try:
                # Build resource-limited kwargs (Unix only)
                subprocess_kwargs = self._build_subprocess_kwargs()

                # Start async subprocess
                process = await asyncio.create_subprocess_shell(
                    resolved,
                    cwd=self.workspace,
                    env=self._build_safe_env(),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    **subprocess_kwargs,
                )

                # Track AFTER successful spawn (fix race condition)
                self.active_processes[execution_id] = process

                try:
                    # Read output + wait for exit with unified timeout
                    output, truncated = await asyncio.wait_for(
                        self._read_output(process),
                        timeout=effective_timeout_ms / 1000,
                    )
                    return_code = await process.wait()

                except asyncio.TimeoutError:
                    timed_out = True
                    truncated = False
                    self.metrics.total_timeout_events += 1
                    self.logger.warn(
                        "Command execution timeout",
                        {
                            "command": command[:80],
                            "timeout": effective_timeout_ms,
                        },
                    )
                    # Kill the process safely and reap it
                    await self._kill_process_safe(process)

                    # Collect whatever output was buffered (safe: process is dead)
                    partial = b""
                    if process.stdout and not process.stdout.at_eof():
                        try:
                            partial = await asyncio.wait_for(
                                process.stdout.read(self.max_output_size),
                                timeout=1.0,
                            )
                        except (asyncio.TimeoutError, Exception):
                            pass
                    output = partial.decode("utf-8", errors="replace")[
                        : self.max_output_size
                    ]
                    return_code = process.returncode or -1

                except asyncio.CancelledError:
                    # Coroutine was cancelled — clean up the process before re-raising
                    self.logger.warn(
                        "Execution cancelled, cleaning up process",
                        {"command": command[:80]},
                    )
                    await self._kill_process_safe(process)
                    raise

                if timed_out:
                    output += f"\n[Timed out after {effective_timeout_ms}ms]"

                self.logger.debug_log(
                    "Command completed",
                    {
                        "exit_code": return_code,
                        "output_size": len(output),
                        "truncated": truncated,
                        "timed_out": timed_out,
                    },
                )

                return ExecuteResponse(
                    output=output.strip(),
                    exit_code=return_code,
                    truncated=truncated,
                )

            except (InvalidCommandError, CommandNotAllowedError, asyncio.CancelledError):
                raise

            except Exception as error:
                self.metrics.total_errors += 1
                self.logger.error("Command execution error", error)
                # If process is still running, clean it up
                if process is not None and process.returncode is None:
                    await self._kill_process_safe(process)

                return ExecuteResponse(
                    output=f"Error: {str(error)}",
                    exit_code=1,
                    truncated=False,
                )

            finally:
                self.active_processes.pop(execution_id, None)

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def _resolve_safe_path(self, user_path: str) -> str:
        """Resolve a file path ensuring it stays within the sandbox workspace.

        Prevents directory traversal attacks (../../../etc/passwd) and
        symlink escape attacks (symlink inside workspace pointing outside).

        Raises:
            InvalidPathError: If path is empty.
            PathTraversalError: If path escapes sandbox via traversal or symlink.
        """
        if not user_path:
            raise InvalidPathError("Path cannot be empty")

        # Strip leading slash to make it relative
        normalized_path = user_path.lstrip("/")

        full_path = (Path(self.workspace) / normalized_path).resolve()
        workspace_path = Path(self.workspace).resolve()

        # Check resolved path is within workspace
        try:
            full_path.relative_to(workspace_path)
        except ValueError:
            self.logger.warn("Path traversal attempt blocked", {"path": user_path})
            raise PathTraversalError(f"Path traversal detected: {user_path}")

        # Check every component of the path for symlinks that escape the workspace.
        # An attacker can create: workspace/innocent -> /etc/passwd
        # .resolve() above follows symlinks, but we must also verify each
        # intermediate component doesn't link outside.
        check = Path(self.workspace)
        for part in Path(normalized_path).parts:
            check = check / part
            if check.is_symlink():
                real_target = check.resolve()
                try:
                    real_target.relative_to(workspace_path)
                except ValueError:
                    self.logger.warn(
                        "Symlink escape attempt blocked",
                        {"path": user_path, "symlink": str(check), "target": str(real_target)},
                    )
                    raise PathTraversalError(
                        f"Symlink escape detected: {check} -> {real_target}"
                    )

        return str(full_path)

    async def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload files into the sandbox working directory.

        Parent directories are created automatically.
        """
        self.logger.debug_log("Uploading files", {"count": len(files)})

        responses = []

        for path, content in files:
            try:
                full_path = self._resolve_safe_path(path)
                parent_dir = Path(full_path).parent
                parent_dir.mkdir(parents=True, exist_ok=True)
                Path(full_path).write_bytes(content)
                self.metrics.files_uploaded += 1

                self.logger.debug_log(
                    "File uploaded",
                    {"path": path, "size": len(content)},
                )

                responses.append(FileUploadResponse(path=path, error=None))

            except (PathTraversalError, InvalidPathError):
                self.metrics.total_errors += 1
                self.logger.warn(
                    "File upload failed",
                    {"path": path, "error": "permission_denied"},
                )
                responses.append(FileUploadResponse(path=path, error="permission_denied"))

            except Exception as error:
                self.metrics.total_errors += 1
                file_error = self._map_error_code(error)
                self.logger.warn(
                    "File upload failed",
                    {"path": path, "error": file_error},
                )
                responses.append(FileUploadResponse(path=path, error=file_error))

        return responses

    async def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download files from the sandbox working directory."""
        self.logger.debug_log("Downloading files", {"count": len(paths)})

        responses = []

        for path in paths:
            try:
                full_path = self._resolve_safe_path(path)
                full_path_obj = Path(full_path)

                if not full_path_obj.exists():
                    responses.append(
                        FileDownloadResponse(path=path, content=None, error="file_not_found")
                    )
                    continue

                if full_path_obj.is_dir():
                    responses.append(
                        FileDownloadResponse(path=path, content=None, error="is_directory")
                    )
                    continue

                content = full_path_obj.read_bytes()
                self.metrics.files_downloaded += 1

                self.logger.debug_log(
                    "File downloaded",
                    {"path": path, "size": len(content)},
                )

                responses.append(FileDownloadResponse(path=path, content=content, error=None))

            except (PathTraversalError, InvalidPathError):
                self.metrics.total_errors += 1
                self.logger.warn(
                    "File download failed",
                    {"path": path, "error": "permission_denied"},
                )
                responses.append(
                    FileDownloadResponse(path=path, content=None, error="permission_denied")
                )

            except Exception as error:
                self.metrics.total_errors += 1
                file_error = self._map_error_code(error)
                self.logger.warn(
                    "File download failed",
                    {"path": path, "error": file_error},
                )
                responses.append(
                    FileDownloadResponse(path=path, content=None, error=file_error)
                )

        return responses

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _map_error_code(error: Exception) -> str:
        """Map Python error types to FileOperationError codes."""
        if isinstance(error, (PathTraversalError, InvalidPathError)):
            return "permission_denied"

        error_msg = str(error)

        if isinstance(error, FileNotFoundError) or "ENOENT" in error_msg:
            return "file_not_found"
        elif isinstance(error, PermissionError) or any(
            code in error_msg for code in ["EACCES", "EPERM"]
        ):
            return "permission_denied"
        elif isinstance(error, IsADirectoryError) or "EISDIR" in error_msg:
            return "is_directory"
        else:
            return "invalid_path"

    def get_metrics(self) -> dict[str, int]:
        """Get sandbox metrics for monitoring and observability."""
        return self.metrics.to_dict()

    def get_active_execution_count(self) -> int:
        """Get the number of currently active command executions."""
        return len(self.active_processes)

    def get_workspace(self) -> str:
        """Get the sandbox's workspace directory."""
        return self.workspace

    async def async_shutdown(self) -> None:
        """Async clean up: kill all active processes and await their exit."""
        self.logger.info(
            "Shutting down sandbox",
            {
                "id": self.id,
                "active_processes": len(self.active_processes),
            },
        )

        for proc in list(self.active_processes.values()):
            await self._kill_process_safe(proc)

        self.active_processes.clear()

    def shutdown(self) -> None:
        """Sync best-effort cleanup. Prefer async_shutdown() when possible."""
        for proc in list(self.active_processes.values()):
            try:
                if proc.returncode is None:
                    proc.kill()
            except ProcessLookupError:
                pass
            except Exception as error:
                self.logger.error("Failed to terminate process during shutdown", error)
        self.active_processes.clear()

    def __del__(self) -> None:
        """Destructor: best-effort sync cleanup (prefer async context manager)."""
        try:
            self.shutdown()
        except Exception:
            pass

    def __repr__(self) -> str:
        return (
            f"LocalSandbox(id={self.id!r}, "
            f"workspace={self.workspace!r}, "
            f"timeout={self.timeout_ms}ms)"
        )


# =============================================================================
# Factory Function
# =============================================================================

def create_local_sandbox(
    workspace: str,
    path_mappings: dict[str, str] | None = None,
    timeout_ms: int | None = None,
    max_output_size: int | None = None,
    debug: bool = False,
    max_concurrent: int | None = None,
    allowed_commands: set[str] | None = DEFAULT_ALLOWED_COMMANDS,
) -> LocalSandbox:
    """Create a new LocalSandbox instance with sensible defaults.

    Supports async context manager for reliable cleanup:

        async with create_local_sandbox(workspace="/tmp/sandbox") as sandbox:
            result = await sandbox.execute("echo hello")

    Args:
        workspace: Root workspace directory (required).
        path_mappings: Virtual prefix -> real prefix mappings.
        timeout_ms: Command execution timeout in milliseconds.
        max_output_size: Maximum output capture size in bytes.
        debug: Enable debug logging.
        max_concurrent: Maximum number of concurrent executions.
        allowed_commands: Set of allowed base commands. None disables allowlist.

    Returns:
        New LocalSandbox instance.
    """
    config = LocalSandboxConfig(
        workspace=workspace,
        path_mappings=path_mappings,
        timeout_ms=timeout_ms,
        max_output_size=max_output_size,
        debug=debug,
        max_concurrent=max_concurrent,
        allowed_commands=allowed_commands,
    )
    return LocalSandbox(config)


__all__ = [
    "LocalSandbox",
    "LocalSandboxConfig",
    "SandboxMetrics",
    "SandboxError",
    "SandboxInitializationError",
    "InvalidCommandError",
    "CommandNotAllowedError",
    "InvalidPathError",
    "PathTraversalError",
    "create_local_sandbox",
]
