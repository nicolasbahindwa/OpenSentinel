"""Local file manager tool for OpenSentinel.

Provides file browsing and management within allowlisted directories
(Desktop, Documents, Downloads, etc.).
"""

import asyncio
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agent.logger import get_logger

logger = get_logger("agent.tools.file_browser", component="file_browser")


# ==============================
# Input Schema
# ==============================


class FileBrowserInput(BaseModel):
    action: str = Field(
        default="list",
        description=(
            "Action to perform: "
            "'list' — list files in a directory, "
            "'read' — read a text file's contents, "
            "'search' — find files matching a glob pattern, "
            "'create_folder' — create a new folder at path, "
            "'create_file' — create a new file (uses content param), "
            "'edit_file' — overwrite a file's contents (uses content param), "
            "'move' — move/rename a file or folder (uses destination param)."
        ),
    )
    path: str = Field(
        default="~/Desktop",
        description=(
            "Target path. Use ~ for home directory. "
            "Examples: ~/Desktop, ~/Documents/report.txt"
        ),
    )
    pattern: str = Field(
        default="",
        description="Glob pattern for 'search' action (e.g. '*.pdf', '*.xlsx').",
    )
    content: str = Field(
        default="",
        description="File content for 'create_file' or 'edit_file' actions.",
    )
    destination: str = Field(
        default="",
        description="Destination path for 'move' action. Use ~ for home directory.",
    )
    confirm: bool = Field(
        default=False,
        description=(
            "Required for write actions (create_folder, create_file, edit_file, move). "
            "First call WITHOUT confirm to preview the operation. "
            "Then call again WITH confirm=true after the user approves."
        ),
    )
    max_results: int = Field(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of items to return (for list/search).",
    )


# ==============================
# Tool Implementation
# ==============================

# Default directories the agent is allowed to access.
_DEFAULT_ALLOWED = (
    "~/Desktop",
    "~/Documents",
    "~/Downloads",
)


class FileBrowserTool(BaseTool):
    name: str = "file_browser"
    description: str = (
        "Browse and manage files on the user's local computer. "
        "Use this tool when the user asks to: "
        "1) List files on their desktop, documents, or downloads "
        "2) Read the contents of a local text file "
        "3) Search for files by name or extension "
        "4) Create a new folder or file "
        "5) Edit/update a text file "
        "6) Move or rename a file or folder. "
        "All operations are restricted to allowed directories only.\n\n"
        "Examples:\n"
        '- List desktop: action="list", path="~/Desktop"\n'
        '- Read a file: action="read", path="~/Documents/report.txt"\n'
        '- Find PDFs: action="search", path="~/Documents", pattern="*.pdf"\n'
        '- Create folder (preview): action="create_folder", path="~/Desktop/Projects"\n'
        '- Create folder (execute): action="create_folder", path="~/Desktop/Projects", confirm=true\n'
        '- Create file (preview): action="create_file", path="~/Documents/notes.txt", '
        'content="Meeting notes..."\n'
        '- Edit file (execute): action="edit_file", path="~/Documents/notes.txt", '
        'content="Updated content", confirm=true\n'
        '- Move file (preview): action="move", path="~/Desktop/report.pdf", '
        'destination="~/Documents"\n'
        "IMPORTANT: Write operations (create_folder, create_file, edit_file, move) require "
        "two calls: first WITHOUT confirm to preview, then WITH confirm=true after user approves."
    )
    args_schema: Type[BaseModel] = FileBrowserInput
    handle_tool_error: bool = True

    MAX_READ_BYTES: ClassVar[int] = 30_000
    MAX_WRITE_BYTES: ClassVar[int] = 100_000

    _allowed_roots: list[Path]

    def __init__(self, allowed_dirs: tuple[str, ...] = _DEFAULT_ALLOWED, **kwargs):
        super().__init__(**kwargs)
        self._allowed_roots = [
            Path(os.path.expanduser(d)).resolve() for d in allowed_dirs
        ]

    # ------------------------------------------------------------------
    # Security: path validation
    # ------------------------------------------------------------------

    def _resolve_and_validate(self, raw_path: str) -> Path:
        """Expand ~ and verify the path is under an allowed root."""
        resolved = Path(os.path.expanduser(raw_path)).resolve()
        for root in self._allowed_roots:
            try:
                resolved.relative_to(root)
                return resolved
            except ValueError:
                continue
        allowed = ", ".join(str(r) for r in self._allowed_roots)
        raise PermissionError(
            f"Access denied: '{resolved}' is outside allowed directories ({allowed})."
        )

    # ------------------------------------------------------------------
    # Read actions
    # ------------------------------------------------------------------

    def _list_dir(self, path: Path, max_results: int) -> str:
        if not path.exists():
            return f"Path not found: {path}"
        if not path.is_dir():
            return f"Not a directory: {path}"

        entries: list[str] = []
        for i, item in enumerate(sorted(path.iterdir())):
            if i >= max_results:
                entries.append(f"... and more (truncated at {max_results})")
                break
            kind = "DIR " if item.is_dir() else "FILE"
            try:
                stat = item.stat()
                size = self._human_size(stat.st_size) if item.is_file() else ""
                mtime = datetime.fromtimestamp(
                    stat.st_mtime, tz=timezone.utc
                ).strftime("%Y-%m-%d %H:%M")
            except OSError:
                size, mtime = "?", "?"
            entries.append(f"[{kind}] {item.name:<40s} {size:>10s}  {mtime}")

        header = f"Contents of {path}  ({len(entries)} items)\n{'=' * 70}"
        return f"{header}\n" + "\n".join(entries)

    def _read_file(self, path: Path) -> str:
        if not path.exists():
            return f"File not found: {path}"
        if not path.is_file():
            return f"Not a file: {path}"

        binary_exts = {
            ".exe", ".dll", ".bin", ".zip", ".7z", ".rar", ".gz", ".tar",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".mp3",
            ".mp4", ".avi", ".mov", ".db", ".sqlite",
        }
        if path.suffix.lower() in binary_exts:
            size = self._human_size(path.stat().st_size)
            return f"Binary file ({path.suffix}, {size}). Cannot display contents."

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            return f"Error reading {path.name}: {e}"

        if len(text) > self.MAX_READ_BYTES:
            text = text[: self.MAX_READ_BYTES] + f"\n... (truncated at {self.MAX_READ_BYTES} bytes)"

        return f"=== {path.name} ===\n{text}"

    def _search_files(self, path: Path, pattern: str, max_results: int) -> str:
        if not path.exists() or not path.is_dir():
            return f"Directory not found: {path}"
        if not pattern:
            return "No search pattern provided. Use pattern like '*.pdf' or '*.xlsx'."

        matches: list[str] = []
        for i, item in enumerate(sorted(path.rglob(pattern))):
            if i >= max_results:
                matches.append(f"... truncated at {max_results} results")
                break
            rel = item.relative_to(path)
            size = self._human_size(item.stat().st_size) if item.is_file() else ""
            matches.append(f"{rel}  {size}")

        if not matches:
            return f"No files matching '{pattern}' in {path}"

        header = f"Search '{pattern}' in {path}  ({len(matches)} matches)"
        return f"{header}\n" + "\n".join(matches)

    # ------------------------------------------------------------------
    # Write actions
    # ------------------------------------------------------------------

    _CONFIRM_HINT: ClassVar[str] = (
        "\n>> Ask the user to confirm, then call again with confirm=true."
    )

    def _create_folder(self, path: Path, confirm: bool) -> str:
        if path.exists():
            return f"Already exists: {path}"
        if not confirm:
            return f"[PREVIEW] Will create folder: {path}{self._CONFIRM_HINT}"
        try:
            path.mkdir(parents=True, exist_ok=False)
            logger.info("folder_created", path=str(path))
            return f"Folder created: {path}"
        except Exception as e:
            logger.error("folder_create_failed", path=str(path), error=str(e))
            return f"Error creating folder: {e}"

    def _create_file(self, path: Path, content: str, confirm: bool) -> str:
        if path.exists():
            return f"File already exists: {path}. Use 'edit_file' to overwrite."
        if not path.parent.exists():
            return f"Parent directory does not exist: {path.parent}"
        if len(content.encode("utf-8")) > self.MAX_WRITE_BYTES:
            return f"Content too large (max {self.MAX_WRITE_BYTES} bytes)."
        if not confirm:
            preview = content[:200] + ("..." if len(content) > 200 else "")
            return (
                f"[PREVIEW] Will create file: {path}\n"
                f"Content ({len(content)} chars): {preview}"
                f"{self._CONFIRM_HINT}"
            )
        try:
            path.write_text(content, encoding="utf-8")
            logger.info("file_created", path=str(path), size=len(content))
            return f"File created: {path} ({len(content)} chars)"
        except Exception as e:
            logger.error("file_create_failed", path=str(path), error=str(e))
            return f"Error creating file: {e}"

    def _edit_file(self, path: Path, content: str, confirm: bool) -> str:
        if not path.exists():
            return f"File not found: {path}. Use 'create_file' to create it."
        if not path.is_file():
            return f"Not a file: {path}"
        if len(content.encode("utf-8")) > self.MAX_WRITE_BYTES:
            return f"Content too large (max {self.MAX_WRITE_BYTES} bytes)."

        binary_exts = {
            ".exe", ".dll", ".bin", ".zip", ".7z", ".rar", ".gz", ".tar",
            ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico",
        }
        if path.suffix.lower() in binary_exts:
            return f"Cannot edit binary file ({path.suffix})."

        if not confirm:
            old_size = self._human_size(path.stat().st_size)
            preview = content[:200] + ("..." if len(content) > 200 else "")
            return (
                f"[PREVIEW] Will overwrite: {path} (current size: {old_size})\n"
                f"New content ({len(content)} chars): {preview}"
                f"{self._CONFIRM_HINT}"
            )
        try:
            path.write_text(content, encoding="utf-8")
            logger.info("file_edited", path=str(path), size=len(content))
            return f"File updated: {path} ({len(content)} chars)"
        except Exception as e:
            logger.error("file_edit_failed", path=str(path), error=str(e))
            return f"Error editing file: {e}"

    def _move(self, source: Path, destination_raw: str, confirm: bool) -> str:
        if not source.exists():
            return f"Source not found: {source}"

        try:
            dest = self._resolve_and_validate(destination_raw)
        except PermissionError as e:
            return str(e)

        # If destination is a directory, move into it keeping the name
        if dest.is_dir():
            dest = dest / source.name

        if dest.exists():
            return f"Destination already exists: {dest}"

        if not confirm:
            return (
                f"[PREVIEW] Will move: {source.name}\n"
                f"  From: {source}\n"
                f"  To:   {dest}"
                f"{self._CONFIRM_HINT}"
            )
        try:
            shutil.move(str(source), str(dest))
            logger.info("file_moved", source=str(source), destination=str(dest))
            return f"Moved: {source.name} -> {dest}"
        except Exception as e:
            logger.error(
                "file_move_failed",
                source=str(source),
                destination=str(dest),
                error=str(e),
            )
            return f"Error moving: {e}"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _human_size(nbytes: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if abs(nbytes) < 1024:
                return f"{nbytes:.0f} {unit}" if unit == "B" else f"{nbytes:.1f} {unit}"
            nbytes /= 1024
        return f"{nbytes:.1f} TB"

    # ------------------------------------------------------------------
    # BaseTool interface
    # ------------------------------------------------------------------

    def _run(
        self,
        action: str = "list",
        path: str = "~/Desktop",
        pattern: str = "",
        content: str = "",
        destination: str = "",
        confirm: bool = False,
        max_results: int = 50,
    ) -> str:
        try:
            resolved = self._resolve_and_validate(path)
        except PermissionError as e:
            logger.warning("file_browser_access_denied", path=path, action=action)
            return str(e)

        if action == "list":
            return self._list_dir(resolved, max_results)
        elif action == "read":
            return self._read_file(resolved)
        elif action == "search":
            return self._search_files(resolved, pattern, max_results)
        elif action == "create_folder":
            return self._create_folder(resolved, confirm)
        elif action == "create_file":
            return self._create_file(resolved, content, confirm)
        elif action == "edit_file":
            return self._edit_file(resolved, content, confirm)
        elif action == "move":
            if not destination:
                return "Missing 'destination' parameter for move action."
            return self._move(resolved, destination, confirm)
        else:
            return (
                f"Unknown action '{action}'. "
                "Use: list, read, search, create_folder, create_file, edit_file, move."
            )

    async def _arun(
        self,
        action: str = "list",
        path: str = "~/Desktop",
        pattern: str = "",
        content: str = "",
        destination: str = "",
        confirm: bool = False,
        max_results: int = 50,
    ) -> str:
        return await asyncio.to_thread(
            self._run, action, path, pattern, content, destination, confirm, max_results
        )


__all__ = ["FileBrowserTool", "FileBrowserInput"]
