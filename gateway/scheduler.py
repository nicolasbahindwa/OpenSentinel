"""Proactive task scheduler for OpenSentinel.

Runs scheduled tasks (daily briefing, periodic checks) by sending
messages to the agent via the LangGraph SDK on a timer.

Usage:
    # Standalone
    python -m gateway.scheduler

    # From CLI
    /schedule        — show scheduled tasks
    /schedule on     — start scheduler
    /schedule off    — stop scheduler
"""

from __future__ import annotations

import os
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from gateway.config import GatewayConfig

# ---------------------------------------------------------------------------
# ANSI colours
# ---------------------------------------------------------------------------
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"

if sys.platform == "win32":
    os.system("")


# ---------------------------------------------------------------------------
# Task definitions
# ---------------------------------------------------------------------------

@dataclass
class ScheduledTask:
    """A recurring task to send to the agent."""

    name: str
    prompt: str                          # message sent to the agent
    interval_minutes: int = 0            # run every N minutes (0 = disabled)
    at_time: str = ""                    # run at HH:MM daily (empty = disabled)
    enabled: bool = True
    last_run: float = 0.0               # timestamp of last execution
    _next_run: float = field(default=0.0, repr=False)

    def should_run(self, now: float) -> bool:
        if not self.enabled:
            return False

        # Interval-based
        if self.interval_minutes > 0:
            if now - self.last_run >= self.interval_minutes * 60:
                return True

        # Time-of-day based
        if self.at_time:
            try:
                hh, mm = map(int, self.at_time.split(":"))
                current = datetime.now()
                target_today = current.replace(hour=hh, minute=mm, second=0, microsecond=0)
                target_ts = target_today.timestamp()
                # Run if we're past the target time and haven't run today
                if now >= target_ts and self.last_run < target_ts:
                    return True
            except (ValueError, AttributeError):
                pass

        return False


# Default tasks — users can customise via env vars or /schedule command
def _default_tasks() -> list[ScheduledTask]:
    return [
        ScheduledTask(
            name="daily_briefing",
            prompt=(
                "Give me my daily briefing. Include weather for my location, "
                "market updates for my watchlist, and top news. "
                "Read /memories/user_prefs.txt for my preferences."
            ),
            at_time=os.getenv("OPENSENTINEL_BRIEFING_TIME", "08:00"),
            enabled=False,  # off by default — user enables with /schedule on
        ),
        ScheduledTask(
            name="system_health",
            prompt="Quick system health check — CPU, memory, disk. Only alert if something is critical.",
            interval_minutes=int(os.getenv("OPENSENTINEL_HEALTH_INTERVAL", "60")),
            enabled=False,
        ),
        ScheduledTask(
            name="news_check",
            prompt="Any breaking or important news in tech and finance in the last hour? Brief summary only.",
            interval_minutes=int(os.getenv("OPENSENTINEL_NEWS_INTERVAL", "120")),
            enabled=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class Scheduler:
    """Background scheduler that sends proactive messages to the agent."""

    TICK_SECONDS = 15  # check every 15 seconds

    def __init__(
        self,
        config: GatewayConfig | None = None,
        on_result: Callable[[str, str], None] | None = None,
    ) -> None:
        self.config = config or GatewayConfig()
        self.tasks = _default_tasks()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._client: Any = None
        self._thread_id: str | None = None
        # Callback for when a scheduled task produces output
        # signature: on_result(task_name, agent_response)
        self._on_result = on_result or self._default_print

    @staticmethod
    def _default_print(task_name: str, response: str) -> None:
        """Default output handler — prints to terminal."""
        now = datetime.now().strftime("%H:%M")
        print(f"\n{MAGENTA}{BOLD}[{now} scheduled: {task_name}]{RESET}")
        print(f"{CYAN}{response}{RESET}")
        print()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the scheduler in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="scheduler")
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _ensure_client(self) -> bool:
        """Ensure SDK client and thread are ready."""
        if self._client is not None:
            return True
        try:
            from langgraph_sdk import get_sync_client

            self._client = get_sync_client(url=self.config.url)
            self._client.assistants.search(limit=1)
            thread = self._client.threads.create()
            self._thread_id = thread["thread_id"]
            return True
        except Exception as e:
            print(f"{RED}Scheduler: cannot connect to agent — {e}{RESET}")
            self._client = None
            return False

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _run_task(self, task: ScheduledTask) -> None:
        """Send the task's prompt to the agent and handle the response."""
        try:
            result = self._client.runs.wait(
                thread_id=self._thread_id,
                assistant_id=self.config.assistant_id,
                input={"messages": [{"role": "user", "content": task.prompt}]},
            )
            messages = result.get("messages", []) if isinstance(result, dict) else []
            response = "(no response)"
            for msg in reversed(messages):
                if msg.get("type") == "ai" and msg.get("content"):
                    response = msg["content"]
                    break
            self._on_result(task.name, response)
        except Exception as e:
            self._on_result(task.name, f"Error: {e}")

    def _loop(self) -> None:
        """Main scheduler loop — runs in background thread."""
        if not self._ensure_client():
            return

        while not self._stop_event.is_set():
            now = time.time()
            for task in self.tasks:
                if task.should_run(now):
                    task.last_run = now
                    self._run_task(task)
            self._stop_event.wait(self.TICK_SECONDS)

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def get_task(self, name: str) -> ScheduledTask | None:
        for t in self.tasks:
            if t.name == name:
                return t
        return None

    def enable_all(self) -> None:
        for t in self.tasks:
            t.enabled = True

    def disable_all(self) -> None:
        for t in self.tasks:
            t.enabled = False

    def status_table(self) -> str:
        """Return a formatted status table."""
        lines = [f"  {'Task':<20} {'Schedule':<20} {'Enabled':<10}"]
        lines.append(f"  {'─' * 20} {'─' * 20} {'─' * 10}")
        for t in self.tasks:
            schedule = ""
            if t.at_time:
                schedule = f"daily at {t.at_time}"
            elif t.interval_minutes > 0:
                schedule = f"every {t.interval_minutes}m"
            enabled = "ON" if t.enabled else "OFF"
            lines.append(f"  {t.name:<20} {schedule:<20} {enabled:<10}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the scheduler standalone (without the CLI REPL)."""
    print(f"{BOLD}{MAGENTA}OpenSentinel Scheduler{RESET}")
    scheduler = Scheduler()
    scheduler.enable_all()
    print(f"\n{scheduler.status_table()}\n")
    print(f"{DIM}Scheduler running. Press Ctrl+C to stop.{RESET}\n")
    scheduler.start()

    try:
        while scheduler.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{DIM}Stopping scheduler...{RESET}")
        scheduler.stop()


if __name__ == "__main__":
    main()
