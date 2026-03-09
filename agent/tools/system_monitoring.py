"""System status monitoring tool using direct Python APIs (psutil).

NO CLI commands used for monitoring. Safer and more reliable.
"""

import platform
import psutil  # ← Direct API library
from datetime import datetime
from typing import Type

from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from agent.logger import get_logger

logger = get_logger("agent.tools.system_status", component="system_status")


class SystemStatusInput(BaseModel):
    category: str = Field(
        default="all",
        description="Category: 'all', 'cpu', 'memory', 'disk', 'network', 'processes', 'os'.",
    )
    limit: int = Field(default=10, ge=1, le=100, description="Max items for processes.")


class SystemStatusTool(BaseTool):
    """Read-only system status using direct Python APIs (NO CLI)."""
    
    name: str = "system_status"
    description: str = (
        "Check system status (CPU, RAM, disk, network, processes). "
        "All operations are read-only and use direct Python APIs (no shell commands)."
    )
    args_schema: Type[BaseModel] = SystemStatusInput
    handle_tool_error: bool = True

    # ------------------------------------------------------------------
    # Direct API Implementations (NO CLI)
    # ------------------------------------------------------------------

    def _check_cpu(self) -> str:
        """Get CPU info using psutil (NO CLI)."""
        try:
            count = psutil.cpu_count(logical=True)
            usage = psutil.cpu_percent(interval=1)  # Blocks for 1s to get accurate usage
            freq = psutil.cpu_freq()
            load = psutil.getloadavg() if hasattr(psutil, "getloadavg") else (0, 0, 0)
            
            return (
                f"CPU Cores: {count} | "
                f"Usage: {usage}% | "
                f"Frequency: {freq.current:.0f}MHz | "
                f"Load: {load[0]:.2f}, {load[1]:.2f}, {load[2]:.2f}"
            )
        except Exception as e:
            return f"Error getting CPU info: {e}"

    def _check_memory(self) -> str:
        """Get RAM info using psutil (NO CLI)."""
        try:
            mem = psutil.virtual_memory()
            status = "✅ Healthy"
            if mem.percent > 90:
                status = "🔴 Critical"
            elif mem.percent > 80:
                status = "⚠️ Warning"
            
            return (
                f"{status} | "
                f"Total: {mem.total / 1024**3:.1f}GB | "
                f"Used: {mem.used / 1024**3:.1f}GB ({mem.percent}%) | "
                f"Available: {mem.available / 1024**3:.1f}GB"
            )
        except Exception as e:
            return f"Error getting memory info: {e}"

    def _check_disk(self) -> str:
        """Get disk info using psutil (NO CLI)."""
        try:
            partitions = psutil.disk_partitions()
            lines = []
            for partition in partitions[:5]:  # Limit to first 5
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    lines.append(
                        f"{partition.device} ({partition.mountpoint}): "
                        f"{usage.percent}% used ({usage.free / 1024**3:.1f}GB free)"
                    )
                except PermissionError:
                    continue
            
            return "\n".join(lines) if lines else "No accessible disks found."
        except Exception as e:
            return f"Error getting disk info: {e}"

    def _check_network(self) -> str:
        """Get network info using psutil (NO CLI)."""
        try:
            interfaces = psutil.net_if_stats()
            active_ifaces = sum(1 for i in interfaces.values() if i.isup)

            # net_connections requires root/admin on some systems
            try:
                connections = psutil.net_connections(kind='inet')
                active_conns = len([c for c in connections if c.status == 'ESTABLISHED'])
                conn_info = f"Connections: {active_conns} established | "
            except (psutil.AccessDenied, PermissionError):
                conn_info = "Connections: N/A (requires elevated privileges) | "

            return (
                f"Interfaces: {active_ifaces} active | "
                f"{conn_info}"
                f"Total Interfaces: {len(interfaces)}"
            )
        except Exception as e:
            return f"Error getting network info: {e}"

    def _check_processes(self, limit: int = 10) -> str:
        """Get top processes using psutil (NO CLI)."""
        try:
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    if pinfo['memory_percent'] is not None:
                        processes.append(pinfo)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Sort by memory usage
            processes.sort(key=lambda x: x['memory_percent'] or 0, reverse=True)
            
            lines = [f"{'PID':<8} {'Name':<30} {'Memory%':<10} {'CPU%':<10}"]
            for p in processes[:limit]:
                lines.append(
                    f"{p['pid']:<8} {p['name'][:28]:<30} {p['memory_percent'] or 0:<10.1f} {p['cpu_percent'] or 0:<10.1f}"
                )
            
            return "\n".join(lines)
        except Exception as e:
            return f"Error getting process info: {e}"

    def _check_os(self) -> str:
        """Get OS info using platform module (NO CLI)."""
        try:
            return (
                f"System: {platform.system()} {platform.release()} | "
                f"Machine: {platform.machine()} | "
                f"Python: {platform.python_version()} | "
                f"Hostname: {platform.node()}"
            )
        except Exception as e:
            return f"Error getting OS info: {e}"

    # ------------------------------------------------------------------
    # Tool Interface
    # ------------------------------------------------------------------

    def _run(self, category: str = "all", limit: int = 10) -> str:
        """Execute system status check using direct APIs."""
        logger.info("system_status_check", category=category)
        
        try:
            if category == "all":
                return "\n\n".join([
                    "=== SYSTEM STATUS ===",
                    f"🖥️  OS: {self._check_os()}",
                    f"⚡ CPU: {self._check_cpu()}",
                    f"💾 Memory: {self._check_memory()}",
                    f"💿 Disk: {self._check_disk()}",
                    f"🌐 Network: {self._check_network()}",
                    f"📋 Top Processes:\n{self._check_processes(limit)}",
                ])
            elif category == "cpu":
                return self._check_cpu()
            elif category == "memory":
                return self._check_memory()
            elif category == "disk":
                return self._check_disk()
            elif category == "network":
                return self._check_network()
            elif category == "processes":
                return self._check_processes(limit)
            elif category == "os":
                return self._check_os()
            else:
                return f"Unknown category: {category}"
                
        except Exception as e:
            logger.error("system_status_failed", error=str(e))
            return f"Error checking system status: {e}"

    async def _arun(self, category: str = "all", limit: int = 10) -> str:
        """Async wrapper (runs in thread to avoid blocking)."""
        import asyncio
        return await asyncio.to_thread(self._run, category, limit)


__all__ = ["SystemStatusTool"]