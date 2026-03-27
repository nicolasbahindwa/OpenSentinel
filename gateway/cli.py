"""Interactive CLI gateway for OpenSentinel.

Usage:
    python -m gateway.cli
"""

from __future__ import annotations

import os
import sys

from gateway.config import GatewayConfig
from gateway.scheduler import Scheduler
from gateway.terminal import safe_print

# ---------------------------------------------------------------------------
# ANSI colours (no extra deps)
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[32m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"

# Enable ANSI on Windows cmd.exe
if sys.platform == "win32":
    os.system("")


# ---------------------------------------------------------------------------
# Chat REPL
# ---------------------------------------------------------------------------


class ChatREPL:
    """Terminal REPL that streams responses from the LangGraph dev server."""

    COMMANDS = {
        "/quit": "Exit the CLI",
        "/exit": "Exit the CLI",
        "/new": "Start a new conversation thread",
        "/history": "Show message history for the current thread",
        "/schedule": "Manage scheduled tasks (on/off/status)",
        "/help": "Show available commands",
    }

    def __init__(self) -> None:
        self.config = GatewayConfig()
        self.client = None
        self.thread_id: str | None = None
        self.scheduler = Scheduler(config=self.config)
        self._connect()

    # ------------------------------------------------------------------
    # Connection & thread management
    # ------------------------------------------------------------------

    def _connect(self) -> None:
        """Connect to the LangGraph dev server."""
        try:
            from langgraph_sdk import get_sync_client

            self.client = get_sync_client(url=self.config.url)
            # Quick health check — list assistants
            self.client.assistants.search(limit=1)
            self._new_thread()
        except Exception as e:
            err = str(e)
            if "Connect" in err or "refused" in err or "Failed" in err:
                print(
                    f"\n{RED}Cannot connect to LangGraph server at {self.config.url}{RESET}"
                    f"\n{DIM}Is 'langgraph dev' running?{RESET}"
                    f"\n{YELLOW}Tip: Use 'python -m gateway.cli_standalone' to run without server{RESET}\n"
                )
            else:
                print(f"\n{RED}Connection error: {e}{RESET}\n")
            sys.exit(1)

    def _new_thread(self) -> None:
        """Create a fresh conversation thread."""
        thread = self.client.threads.create()
        self.thread_id = thread["thread_id"]
        safe_print(f"{DIM}Thread: {self.thread_id}{RESET}")

    # ------------------------------------------------------------------
    # Sending messages & streaming
    # ------------------------------------------------------------------

    def _send(self, user_input: str) -> None:
        """Send a message and wait for the response.

        Uses runs.wait() because langgraph dev (in-memory mode) does not
        support streaming reliably (BlockingError).  When deployed to
        LangGraph Cloud, this can be swapped to runs.stream().
        """
        try:
            safe_print(f"{DIM}(thinking...){RESET}", end="\r", flush=True)
            result = self.client.runs.wait(
                thread_id=self.thread_id,
                assistant_id=self.config.assistant_id,
                input={"messages": [{"role": "user", "content": user_input}]},
                timeout=180.0,  # 3 minute timeout (reduced from 5 to catch issues faster)
            )
            # Clear the "thinking..." line
            safe_print(" " * 30, end="\r", flush=True)

            # Extract the last AI message from the result
            messages = result.get("messages", []) if isinstance(result, dict) else []
            for msg in reversed(messages):
                if msg.get("type") == "ai" and msg.get("content"):
                    safe_print(msg["content"])
                    return
            safe_print(f"{DIM}(no response){RESET}")
        except KeyboardInterrupt:
            safe_print(f"\n{DIM}(interrupted){RESET}")
        except Exception as e:
            err = str(e)
            if "timeout" in err.lower():
                safe_print(f"\n{YELLOW}Response timed out. The agent may still be processing.{RESET}")
            else:
                safe_print(f"\n{RED}Error: {e}{RESET}")

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _show_history(self) -> None:
        """Print the conversation history for the current thread."""
        try:
            state = self.client.threads.get_state(self.thread_id)
            messages = state.get("values", {}).get("messages", [])
            if not messages:
                safe_print(f"{DIM}(no messages yet){RESET}")
                return

            safe_print(f"\n{BOLD}--- Conversation History ---{RESET}")
            for msg in messages:
                role = msg.get("type", "unknown")
                content = msg.get("content", "")
                if role == "human":
                    safe_print(f"  {GREEN}You:{RESET} {content}")
                elif role == "ai":
                    if content:
                        safe_print(f"  {CYAN}Agent:{RESET} {content[:200]}{'...' if len(content) > 200 else ''}")
                    tool_calls = msg.get("tool_calls", [])
                    for tc in tool_calls:
                        safe_print(f"  {DIM}  [tool: {tc.get('name', '?')}]{RESET}")
                elif role == "tool":
                    name = msg.get("name", "tool")
                    safe_print(f"  {DIM}  [{name} result]{RESET}")
            safe_print(f"{BOLD}----------------------------{RESET}\n")
        except Exception as e:
            safe_print(f"{RED}Could not fetch history: {e}{RESET}")

    # ------------------------------------------------------------------
    # Command handling
    # ------------------------------------------------------------------

    def _handle_command(self, cmd: str) -> bool:
        """Handle a slash command. Returns False to signal exit."""
        cmd = cmd.strip().lower()

        if cmd in ("/quit", "/exit"):
            return False

        if cmd == "/new":
            self._new_thread()
            print(f"{GREEN}New conversation started.{RESET}")
            return True

        if cmd == "/history":
            self._show_history()
            return True

        if cmd.startswith("/schedule"):
            self._handle_schedule(cmd)
            return True

        if cmd == "/help":
            print(f"\n{BOLD}Commands:{RESET}")
            for name, desc in self.COMMANDS.items():
                print(f"  {YELLOW}{name:12}{RESET} {desc}")
            print()
            return True

        print(f"{DIM}Unknown command: {cmd}. Type /help for options.{RESET}")
        return True

    # ------------------------------------------------------------------
    # Scheduler
    # ------------------------------------------------------------------

    def _handle_schedule(self, cmd: str) -> None:
        """Handle /schedule subcommands."""
        parts = cmd.strip().split()
        sub = parts[1] if len(parts) > 1 else ""

        if sub == "on":
            self.scheduler.enable_all()
            self.scheduler.start()
            print(f"{YELLOW}Scheduler started.{RESET}")
            print(self.scheduler.status_table())
        elif sub == "off":
            self.scheduler.disable_all()
            self.scheduler.stop()
            print(f"{YELLOW}Scheduler stopped.{RESET}")
        else:
            # Show status
            state = "RUNNING" if self.scheduler.running else "STOPPED"
            print(f"\n{BOLD}Scheduler: {state}{RESET}")
            print(self.scheduler.status_table())
            print(f"\n{DIM}Usage: /schedule on | /schedule off{RESET}\n")

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        """Start the interactive REPL."""
        print(f"\n{BOLD}{CYAN}OpenSentinel CLI{RESET}")
        print(f"{DIM}Connected to {self.config.url} | Type /help for commands{RESET}\n")

        while True:
            try:
                user_input = input(f"{GREEN}{BOLD}You > {RESET}").strip()
            except (KeyboardInterrupt, EOFError):
                print(f"\n{DIM}Goodbye!{RESET}")
                break

            if not user_input:
                continue

            if user_input.startswith("/"):
                if not self._handle_command(user_input):
                    print(f"{DIM}Goodbye!{RESET}")
                    break
                continue

            print(f"{CYAN}{BOLD}Agent > {RESET}", end="", flush=True)
            self._send(user_input)

        # Cleanup
        if self.scheduler.running:
            self.scheduler.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    repl = ChatREPL()
    repl.run()


if __name__ == "__main__":
    main()
