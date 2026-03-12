"""Interactive CLI gateway for OpenSentinel.

Usage:
    python -m gateway
    python -m gateway.cli
"""

from __future__ import annotations

import itertools
import sys
import threading
import time

from gateway.config import GatewayConfig
from gateway.scheduler import Scheduler
from gateway.terminal import (
    RESET, BOLD, DIM, GREEN, CYAN, YELLOW, RED, MAGENTA,
    banner, print_error, print_warn, print_ok, print_dim,
)

# ---------------------------------------------------------------------------
# Tool name → friendly status label
# ---------------------------------------------------------------------------

_TOOL_LABELS: dict[str, str] = {
    "web_browser":      "Browsing the web",
    "internet_search":  "Searching the web",
    "crypto":           "Fetching crypto data",
    "currency":         "Fetching exchange rates",
    "yahoo_finance":    "Fetching market data",
    "gmail":            "Accessing Gmail",
    "file_manager":     "Reading files",
    "code_executor":    "Running code",
    "system_monitor":   "Checking system",
    "memory":           "Accessing memory",
    "calculator":       "Calculating",
}

_SPINNER = itertools.cycle(["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"])


# ---------------------------------------------------------------------------
# Animated status line (used during blocking wait)
# ---------------------------------------------------------------------------

class _StatusLine:
    """Prints an animated spinner with a status message while the agent runs."""

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._label = "Thinking"
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None

    def set_label(self, label: str) -> None:
        with self._lock:
            self._label = label

    def start(self) -> None:
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2)
        # Erase spinner line
        print("\r" + " " * 60 + "\r", end="", flush=True)

    def _run(self) -> None:
        start = time.monotonic()
        while not self._stop.is_set():
            elapsed = int(time.monotonic() - start)
            with self._lock:
                label = self._label
            spin = next(_SPINNER)
            print(
                f"\r{DIM}{spin} {label}… ({elapsed}s){RESET}   ",
                end="", flush=True,
            )
            time.sleep(0.1)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MAX_RECONNECT_ATTEMPTS = 5
_RECONNECT_DELAY_SECONDS = 3


def _extract_ai_response(result: object) -> str | None:
    """Pull the last AI message content out of a LangGraph run result."""
    messages = result.get("messages", []) if isinstance(result, dict) else []
    for msg in reversed(messages):
        if msg.get("type") == "ai" and msg.get("content"):
            return msg["content"]
    return None


# ---------------------------------------------------------------------------
# Chat REPL
# ---------------------------------------------------------------------------


class ChatREPL:
    """Terminal REPL that communicates with the LangGraph dev server."""

    COMMANDS = {
        "/quit, /exit":         "Exit the CLI",
        "/new":                 "Start a new conversation thread",
        "/history":             "Show message history for the current thread",
        "/schedule":            "Show scheduler status",
        "/schedule on [name]":  "Enable all tasks (or one by name) and start",
        "/schedule off [name]": "Disable all tasks (or one by name) and stop",
        "/schedule run <name>": "Trigger a task immediately",
        "/schedule set <name> interval=<mins> | at=<HH:MM>": "Change a task's schedule",
        "/schedule history":    "Show recent scheduled task outputs",
        "/help":                "Show this help",
    }

    def __init__(self) -> None:
        self.config = GatewayConfig()
        self.client = None
        self.thread_id: str | None = None
        self._streaming_supported = True   # set False after first streaming failure
        self.scheduler = Scheduler(
            config=self.config,
            on_result=self._on_scheduled_result,
        )
        self._connect()

    # ------------------------------------------------------------------
    # Scheduled task output — printed with a clear separator so it
    # doesn't look like a response to the user's current input.
    # ------------------------------------------------------------------

    def _on_scheduled_result(self, result) -> None:
        colour = RED if result.error else CYAN
        print(f"\n{MAGENTA}{BOLD}[{result.timestamp} · scheduled: {result.task_name}]{RESET}")
        print(f"{colour}{result.response}{RESET}")
        # Re-print the prompt so the user knows where to type
        print(f"{GREEN}{BOLD}You > {RESET}", end="", flush=True)

    # ------------------------------------------------------------------
    # Connection & reconnect
    # ------------------------------------------------------------------

    def _connect(self, quiet: bool = False) -> bool:
        """Connect (or reconnect) to the LangGraph server."""
        for attempt in range(1, _MAX_RECONNECT_ATTEMPTS + 1):
            try:
                from langgraph_sdk import get_sync_client
                self.client = get_sync_client(url=self.config.url)
                self.client.assistants.search(limit=1)
                if not self.thread_id:
                    self._new_thread(announce=not quiet)
                if not quiet:
                    print_ok(f"Connected to {self.config.url}")
                return True
            except Exception as e:
                err = str(e)
                if attempt == _MAX_RECONNECT_ATTEMPTS:
                    if "Connect" in err or "refused" in err or "Failed" in err:
                        print_error(
                            f"Cannot connect to LangGraph server at {self.config.url}\n"
                            f"Is 'langgraph dev' running?"
                        )
                    else:
                        print_error(f"Connection error: {e}")
                    return False
                print_warn(f"Connection attempt {attempt} failed — retrying in {_RECONNECT_DELAY_SECONDS}s…")
                time.sleep(_RECONNECT_DELAY_SECONDS)
        return False

    def _new_thread(self, announce: bool = True) -> None:
        """Create a fresh conversation thread and share it with the scheduler."""
        thread = self.client.threads.create()
        self.thread_id = thread["thread_id"]
        self.scheduler.set_thread(self.thread_id)
        if announce:
            print_dim(f"Thread: {self.thread_id}")

    # ------------------------------------------------------------------
    # Sending messages
    # ------------------------------------------------------------------

    def _send(self, user_input: str) -> None:
        """Send a message, streaming events for live status, fallback to wait."""
        if not self._streaming_supported:
            self._send_blocking(user_input)
            return
        try:
            self._send_streaming(user_input)
        except Exception as e:
            # Streaming failed — switch permanently to blocking mode.
            self._streaming_supported = False
            print_dim(f"(streaming unavailable: {e})")
            self._send_blocking(user_input)

    def _send_streaming(self, user_input: str) -> None:
        """Stream the run and display tool calls + response as they arrive.

        Any exception raised here (including stream setup failures) propagates
        to _send(), which immediately falls back to _send_blocking().
        """
        status = _StatusLine()
        response_lines: list[str] = []
        response_started = False

        stream = self.client.runs.stream(
            thread_id=self.thread_id,
            assistant_id=self.config.assistant_id,
            input={"messages": [{"role": "user", "content": user_input}]},
            stream_mode="messages",
        )

        status.start()
        try:
            for part in stream:
                # ── Tool / node events ─────────────────────────────
                if part.event == "events":
                    data = part.data or {}
                    ev = data.get("event", "")
                    name = data.get("name", "")

                    if ev == "on_tool_start":
                        label = _TOOL_LABELS.get(name, f"Using {name}")
                        status.set_label(label)

                    elif ev == "on_tool_end":
                        status.set_label("Processing result")

                    elif ev == "on_chat_model_start":
                        status.set_label("Composing response")

                    elif ev == "on_chain_start" and name:
                        status.set_label(f"Running {name}")

                # ── Streaming text chunks ──────────────────────────
                elif part.event == "messages":
                    chunks = part.data if isinstance(part.data, list) else [part.data]
                    for chunk in chunks:
                        if not isinstance(chunk, dict):
                            continue
                        content = chunk.get("content", "")
                        if not content:
                            continue
                        if not response_started:
                            status.stop()
                            response_started = True
                        print(content, end="", flush=True)
                        response_lines.append(content)

        finally:
            status.stop()

        if response_lines:
            print()  # final newline after streamed text
        else:
            # Streaming worked but no text chunks — extract from final state
            try:
                state = self.client.threads.get_state(self.thread_id)
                msgs = state.get("values", {}).get("messages", [])
                for msg in reversed(msgs):
                    if msg.get("type") == "ai" and msg.get("content"):
                        print(msg["content"])
                        return
            except Exception:
                pass
            print_dim("(no response)")

    def _send_blocking(self, user_input: str) -> None:
        """Blocking wait with animated spinner — fallback when streaming fails."""
        status = _StatusLine()
        try:
            status.start()
            result = self.client.runs.wait(
                thread_id=self.thread_id,
                assistant_id=self.config.assistant_id,
                input={"messages": [{"role": "user", "content": user_input}]},
            )
            status.stop()

            response = _extract_ai_response(result)
            print(response if response else f"{DIM}(no response){RESET}")

        except KeyboardInterrupt:
            status.stop()
            print(f"\n{DIM}(interrupted){RESET}")
        except Exception as e:
            status.stop()
            err = str(e)
            if "timeout" in err.lower():
                print_warn("Response timed out. The agent may still be processing.")
            elif "Connect" in err or "refused" in err:
                print_warn("Lost connection. Attempting to reconnect…")
                if self._connect(quiet=True):
                    print_ok("Reconnected. Please resend your message.")
                else:
                    print_error("Could not reconnect. Is 'langgraph dev' still running?")
            else:
                print_error(f"Error: {e}")

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

    def _show_history(self) -> None:
        try:
            state = self.client.threads.get_state(self.thread_id)
            messages = state.get("values", {}).get("messages", [])
            if not messages:
                print_dim("(no messages yet)")
                return

            print(f"\n{BOLD}── Conversation History ──────────────────{RESET}")
            for msg in messages:
                role = msg.get("type", "unknown")
                content = msg.get("content", "")
                if role == "human":
                    print(f"  {GREEN}You:{RESET}   {content}")
                elif role == "ai":
                    if content:
                        preview = content[:200] + ("…" if len(content) > 200 else "")
                        print(f"  {CYAN}Agent:{RESET} {preview}")
                    for tc in msg.get("tool_calls", []):
                        print(f"  {DIM}         [tool: {tc.get('name', '?')}]{RESET}")
                elif role == "tool":
                    print(f"  {DIM}         [{msg.get('name', 'tool')} result]{RESET}")
            print(f"{BOLD}──────────────────────────────────────────{RESET}\n")
        except Exception as e:
            print_error(f"Could not fetch history: {e}")

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    def _handle_command(self, cmd: str) -> bool:
        """Handle a slash command. Returns False to exit."""
        parts = cmd.strip().split()
        root = parts[0].lower()

        if root in ("/quit", "/exit"):
            return False

        if root == "/new":
            self._new_thread()
            print_ok("New conversation started.")
            return True

        if root == "/history":
            self._show_history()
            return True

        if root == "/schedule":
            self._handle_schedule(parts[1:])
            return True

        if root == "/help":
            print(f"\n{BOLD}Commands:{RESET}")
            for name, desc in self.COMMANDS.items():
                print(f"  {YELLOW}{name}{RESET}")
                print(f"      {DIM}{desc}{RESET}")
            print()
            return True

        print_dim(f"Unknown command: {root}. Type /help for options.")
        return True

    # ------------------------------------------------------------------
    # /schedule subcommands
    # ------------------------------------------------------------------

    def _handle_schedule(self, args: list[str]) -> None:
        sub = args[0].lower() if args else ""

        # ── /schedule on [name] ──────────────────────────────────────
        if sub == "on":
            name = args[1] if len(args) > 1 else None
            changed = self.scheduler.enable(name)
            if not changed:
                print_warn(f"Task '{name}' not found. Run /schedule to list tasks.")
                return
            if not self.scheduler.running:
                self.scheduler.start()
            print_ok(f"Enabled: {', '.join(changed)}")
            print(self.scheduler.status_table())
            return

        # ── /schedule off [name] ─────────────────────────────────────
        if sub == "off":
            name = args[1] if len(args) > 1 else None
            changed = self.scheduler.disable(name)
            if not changed:
                print_warn(f"Task '{name}' not found.")
                return
            # Stop the background loop only if all tasks are now disabled
            if not any(t.enabled for t in self.scheduler.tasks):
                self.scheduler.stop()
                print_warn("All tasks disabled — scheduler stopped.")
            else:
                print_warn(f"Disabled: {', '.join(changed)}")
            print(self.scheduler.status_table())
            return

        # ── /schedule run <name> ──────────────────────────────────────
        if sub == "run":
            if len(args) < 2:
                print_warn("Usage: /schedule run <task_name>")
                return
            name = args[1]
            if not self.scheduler.running:
                self.scheduler.start()
            ok = self.scheduler.run_now(name)
            if ok:
                print_ok(f"Task '{name}' triggered — response will appear shortly.")
            else:
                print_error(f"Task '{name}' not found or scheduler cannot connect.")
            return

        # ── /schedule set <name> interval=<N> | at=<HH:MM> ──────────
        if sub == "set":
            # e.g.  /schedule set news_check interval=30
            #        /schedule set daily_briefing at=09:00
            if len(args) < 3:
                print_warn("Usage: /schedule set <name> interval=<mins>  OR  at=<HH:MM>")
                return
            name, setting = args[1], args[2]
            if "=" not in setting:
                print_warn("Setting must be  interval=<mins>  or  at=<HH:MM>")
                return
            key, val = setting.split("=", 1)
            if key == "interval":
                try:
                    mins = int(val)
                except ValueError:
                    print_warn(f"interval must be an integer, got {val!r}")
                    return
                if self.scheduler.set_interval(name, mins):
                    print_ok(f"'{name}' → every {mins}m")
                else:
                    print_error(f"Task '{name}' not found.")
            elif key == "at":
                if self.scheduler.set_time(name, val):
                    print_ok(f"'{name}' → daily at {val}")
                else:
                    print_error(f"Invalid time '{val}' or task not found. Use HH:MM format.")
            else:
                print_warn(f"Unknown setting '{key}'. Use 'interval' or 'at'.")
            return

        # ── /schedule history ─────────────────────────────────────────
        if sub == "history":
            print(f"\n{BOLD}── Scheduled Task History ────────────────{RESET}")
            print(self.scheduler.history_table())
            print()
            return

        # ── /schedule  (status) ───────────────────────────────────────
        state = f"{GREEN}RUNNING{RESET}" if self.scheduler.running else f"{DIM}STOPPED{RESET}"
        print(f"\n{BOLD}Scheduler:{RESET} {state}")
        print(self.scheduler.status_table())
        print(
            f"\n{DIM}"
            f"/schedule on [name]  /schedule off [name]  "
            f"/schedule run <name>  /schedule set <name> interval=<N> | at=<HH:MM>"
            f"{RESET}\n"
        )

    # ------------------------------------------------------------------
    # Main REPL loop
    # ------------------------------------------------------------------

    def run(self) -> None:
        print(f"\n{banner('OpenSentinel CLI', CYAN)}")
        print_dim(f"Connected to {self.config.url}  ·  Type /help for commands\n")

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
                    print_dim("Goodbye!")
                    break
                continue

            print(f"{CYAN}{BOLD}Agent > {RESET}", end="", flush=True)
            self._send(user_input)

        if self.scheduler.running:
            self.scheduler.stop()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    if sys.version_info < (3, 11):
        print_error("Python 3.11+ required.")
        sys.exit(1)
    repl = ChatREPL()
    repl.run()


if __name__ == "__main__":
    main()
