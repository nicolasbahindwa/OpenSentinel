"""Shared terminal utilities — ANSI colours and print helpers."""

from __future__ import annotations

import os
import sys

# ---------------------------------------------------------------------------
# ANSI colour codes
# ---------------------------------------------------------------------------

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
GREEN   = "\033[32m"
CYAN    = "\033[36m"
YELLOW  = "\033[33m"
RED     = "\033[31m"
MAGENTA = "\033[35m"
BLUE    = "\033[34m"
WHITE   = "\033[37m"

# Enable ANSI on Windows cmd.exe / PowerShell
if sys.platform == "win32":
    os.system("")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def safe_print(*parts: object, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
    text = sep.join(str(part) for part in parts)
    try:
        print(text, end=end, flush=flush)
    except UnicodeEncodeError:
        encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
        safe_text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
        print(safe_text, end=end, flush=flush)


def print_error(msg: str) -> None:
    safe_print(f"{RED}{msg}{RESET}")


def print_warn(msg: str) -> None:
    safe_print(f"{YELLOW}{msg}{RESET}")


def print_ok(msg: str) -> None:
    safe_print(f"{GREEN}{msg}{RESET}")


def print_dim(msg: str) -> None:
    safe_print(f"{DIM}{msg}{RESET}")


def print_section(title: str) -> None:
    safe_print(f"\n{BOLD}{title}{RESET}")


def banner(text: str, colour: str = CYAN) -> str:
    return f"{colour}{BOLD}{text}{RESET}"


def fmt_table(rows: list[tuple[str, ...]], headers: tuple[str, ...]) -> str:
    """Simple fixed-width text table."""
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            col_widths[i] = max(col_widths[i], len(str(cell)))

    sep = "  ".join("─" * w for w in col_widths)
    header_line = "  ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    lines = [f"  {BOLD}{header_line}{RESET}", f"  {DIM}{sep}{RESET}"]
    for row in rows:
        lines.append("  " + "  ".join(f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row)))
    return "\n".join(lines)
