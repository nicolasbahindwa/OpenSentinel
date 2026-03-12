"""Proactive task scheduler for OpenSentinel.

Runs scheduled tasks (daily briefing, periodic checks) by sending
messages to the agent via the LangGraph SDK on a timer.

Usage:
    # Standalone
    python -m gateway.scheduler

    # From CLI
    /schedule              — show scheduled tasks and status
    /schedule on           — enable all tasks and start
    /schedule off          — disable all and stop
    /schedule on  <name>   — enable a single task
    /schedule off <name>   — disable a single task
    /schedule set <name> interval=<mins>
    /schedule set <name> at=<HH:MM>
    /schedule history      — show recent task outputs
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from gateway.config import GatewayConfig
from gateway.terminal import (
    RESET, BOLD, DIM, CYAN, RED, MAGENTA, GREEN,
    fmt_table, print_error,
)

# ---------------------------------------------------------------------------
# Task definition
# ---------------------------------------------------------------------------

MAX_HISTORY = 50  # keep last N task results in memory


@dataclass
class ScheduledTask:
    """A recurring task sent to the agent."""

    name: str
    prompt: str
    interval_minutes: int = 0   # run every N minutes (0 = time-based only)
    at_time: str = ""           # run at HH:MM daily   (empty = interval only)
    enabled: bool = True
    last_run: float = 0.0       # unix timestamp of last execution

    def should_run(self, now: float) -> bool:
        if not self.enabled:
            return False

        if self.interval_minutes > 0:
            if now - self.last_run >= self.interval_minutes * 60:
                return True

        if self.at_time:
            try:
                hh, mm = map(int, self.at_time.split(":"))
                current = datetime.now()
                target = current.replace(hour=hh, minute=mm, second=0, microsecond=0)
                target_ts = target.timestamp()
                if now >= target_ts and self.last_run < target_ts:
                    return True
            except (ValueError, AttributeError):
                pass

        return False

    def schedule_label(self) -> str:
        if self.at_time and self.interval_minutes:
            return f"daily {self.at_time} + every {self.interval_minutes}m"
        if self.at_time:
            return f"daily at {self.at_time}"
        if self.interval_minutes:
            return f"every {self.interval_minutes}m"
        return "—"


@dataclass
class TaskResult:
    """One historical output from a scheduled task."""
    task_name: str
    response: str
    timestamp: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M"))
    error: bool = False


# ---------------------------------------------------------------------------
# Default tasks
# ---------------------------------------------------------------------------

def _default_tasks() -> list[ScheduledTask]:
    import os
    return [
        ScheduledTask(
            name="daily_briefing",
            prompt=(
                "Give me my daily briefing. Include weather for my location, "
                "market updates for my watchlist, and top news. "
                "Read /memories/user_prefs.txt for my preferences."
            ),
            at_time=os.getenv("OPENSENTINEL_BRIEFING_TIME", "08:00"),
            enabled=False,
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
            interval_minutes=int(os.getenv("OPENSENTINEL_NEWS_INTERVAL", "60")),
            enabled=False,
        ),
    ]


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    """Background scheduler — tasks run concurrently via ThreadPoolExecutor."""

    TICK_SECONDS = 15

    def __init__(
        self,
        config: Optional[GatewayConfig] = None,
        on_result: Optional[Callable[[TaskResult], None]] = None,
    ) -> None:
        self.config = config or GatewayConfig()
        self.tasks: list[ScheduledTask] = _default_tasks()
        self.history: list[TaskResult] = []

        self._thread_id: Optional[str] = None   # shared with CLI
        self._client: Any = None
        self._loop_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="sched_task")
        self._lock = threading.Lock()

        self._on_result: Callable[[TaskResult], None] = on_result or self._default_print

        # Restore persisted state (enabled flags + last_run)
        self._load_state()

    # ------------------------------------------------------------------
    # Thread-id (shared with the CLI's active conversation)
    # ------------------------------------------------------------------

    def set_thread(self, thread_id: str) -> None:
        """Point the scheduler at the CLI's active thread."""
        with self._lock:
            self._thread_id = thread_id

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._loop_thread and self._loop_thread.is_alive():
            return
        self._stop_event.clear()
        self._loop_thread = threading.Thread(
            target=self._loop, daemon=True, name="scheduler-loop"
        )
        self._loop_thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._loop_thread:
            self._loop_thread.join(timeout=5)
            self._loop_thread = None
        self._save_state()

    @property
    def running(self) -> bool:
        return self._loop_thread is not None and self._loop_thread.is_alive()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _ensure_client(self) -> bool:
        if self._client is not None:
            return True
        try:
            from langgraph_sdk import get_sync_client
            self._client = get_sync_client(url=self.config.url)
            self._client.assistants.search(limit=1)
            # Only create a dedicated thread if the CLI hasn't shared one
            if not self._thread_id:
                t = self._client.threads.create()
                self._thread_id = t["thread_id"]
            return True
        except Exception as e:
            print_error(f"Scheduler: cannot connect — {e}")
            self._client = None
            return False

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        if not self._ensure_client():
            return

        while not self._stop_event.is_set():
            now = time.time()
            for task in self.tasks:
                if task.should_run(now):
                    task.last_run = now
                    # Non-blocking: submit to thread pool
                    self._executor.submit(self._run_task, task)

            self._stop_event.wait(self.TICK_SECONDS)

    # ------------------------------------------------------------------
    # Task execution
    # ------------------------------------------------------------------

    def _run_task(self, task: ScheduledTask) -> None:
        try:
            with self._lock:
                tid = self._thread_id

            result = self._client.runs.wait(
                thread_id=tid,
                assistant_id=self.config.assistant_id,
                input={"messages": [{"role": "user", "content": task.prompt}]},
            )

            messages = result.get("messages", []) if isinstance(result, dict) else []
            response = "(no response)"
            for msg in reversed(messages):
                if msg.get("type") == "ai" and msg.get("content"):
                    response = msg["content"]
                    break

            record = TaskResult(task_name=task.name, response=response)

        except Exception as e:
            record = TaskResult(task_name=task.name, response=str(e), error=True)

        with self._lock:
            self.history.append(record)
            if len(self.history) > MAX_HISTORY:
                self.history.pop(0)

        self._on_result(record)
        self._save_state()

    # ------------------------------------------------------------------
    # Default output handler
    # ------------------------------------------------------------------

    @staticmethod
    def _default_print(result: TaskResult) -> None:
        colour = RED if result.error else CYAN
        now = result.timestamp
        print(f"\n{MAGENTA}{BOLD}[{now} — scheduled: {result.task_name}]{RESET}")
        print(f"{colour}{result.response}{RESET}\n")

    # ------------------------------------------------------------------
    # Task management
    # ------------------------------------------------------------------

    def get_task(self, name: str) -> Optional[ScheduledTask]:
        for t in self.tasks:
            if t.name == name:
                return t
        return None

    def enable(self, name: Optional[str] = None) -> list[str]:
        """Enable one task by name, or all if name is None. Returns changed names."""
        changed = []
        for t in self.tasks:
            if name is None or t.name == name:
                t.enabled = True
                changed.append(t.name)
        self._save_state()
        return changed

    def disable(self, name: Optional[str] = None) -> list[str]:
        """Disable one task by name, or all if name is None. Returns changed names."""
        changed = []
        for t in self.tasks:
            if name is None or t.name == name:
                t.enabled = False
                changed.append(t.name)
        self._save_state()
        return changed

    def set_interval(self, name: str, minutes: int) -> bool:
        t = self.get_task(name)
        if not t:
            return False
        t.interval_minutes = minutes
        t.at_time = ""
        self._save_state()
        return True

    def set_time(self, name: str, at: str) -> bool:
        t = self.get_task(name)
        if not t:
            return False
        # Validate HH:MM
        try:
            hh, mm = map(int, at.split(":"))
            assert 0 <= hh <= 23 and 0 <= mm <= 59
        except Exception:
            return False
        t.at_time = f"{hh:02d}:{mm:02d}"
        t.interval_minutes = 0
        self._save_state()
        return True

    def run_now(self, name: str) -> bool:
        """Trigger a task immediately (non-blocking)."""
        t = self.get_task(name)
        if not t or not self._ensure_client():
            return False
        t.last_run = time.time()
        self._executor.submit(self._run_task, t)
        return True

    # ------------------------------------------------------------------
    # Status display
    # ------------------------------------------------------------------

    def status_table(self) -> str:
        rows = []
        for t in self.tasks:
            last = (
                datetime.fromtimestamp(t.last_run).strftime("%H:%M")
                if t.last_run else "never"
            )
            enabled = f"{GREEN}ON{RESET}" if t.enabled else f"{DIM}OFF{RESET}"
            rows.append((t.name, t.schedule_label(), enabled, last))
        return fmt_table(rows, ("Task", "Schedule", "Enabled", "Last run"))

    def history_table(self, limit: int = 10) -> str:
        recent = self.history[-limit:]
        if not recent:
            return f"  {DIM}No history yet.{RESET}"
        rows = []
        for r in reversed(recent):
            status = f"{RED}ERR{RESET}" if r.error else f"{GREEN}OK{RESET}"
            preview = r.response[:60].replace("\n", " ") + ("…" if len(r.response) > 60 else "")
            rows.append((r.timestamp, r.task_name, status, preview))
        return fmt_table(rows, ("Time", "Task", "Status", "Preview"))

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _state_path(self) -> Path:
        return self.config.state_dir / "scheduler_state.json"

    def _save_state(self) -> None:
        try:
            path = self._state_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                t.name: {"enabled": t.enabled, "last_run": t.last_run}
                for t in self.tasks
            }
            path.write_text(json.dumps(state, indent=2))
        except Exception:
            pass  # persistence is best-effort

    def _load_state(self) -> None:
        try:
            path = self._state_path()
            if not path.exists():
                return
            state: dict = json.loads(path.read_text())
            for t in self.tasks:
                if t.name in state:
                    t.enabled = state[t.name].get("enabled", t.enabled)
                    t.last_run = state[t.name].get("last_run", 0.0)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

def main() -> None:
    from gateway.terminal import banner
    print(banner("OpenSentinel Scheduler", MAGENTA))
    scheduler = Scheduler()
    scheduler.enable()
    print(f"\n{scheduler.status_table()}\n")
    print(f"{DIM}Scheduler running. Press Ctrl+C to stop.{RESET}\n")
    scheduler.start()
    try:
        while scheduler.running:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n{DIM}Stopping...{RESET}")
        scheduler.stop()


if __name__ == "__main__":
    main()
