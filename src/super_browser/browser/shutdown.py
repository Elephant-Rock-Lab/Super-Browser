"""Shutdown supervisor — two-phase browser process cleanup."""

from __future__ import annotations

import asyncio
import logging
import os
import signal
from typing import Optional

logger = logging.getLogger(__name__)


class ShutdownSupervisor:
    """Monitors a browser process and performs two-phase cleanup.

    Phase 1: Graceful shutdown (SIGTERM / terminate).
    Phase 2: Force kill after grace period.

    Ported from Stagehand supervisor.ts pattern.
    """

    def __init__(
        self,
        browser_pid: int,
        grace_period: float = 7.0,
    ) -> None:
        self._pid = browser_pid
        self._grace_period = grace_period
        self._monitor_task: Optional[asyncio.Task] = None

    async def start(self, lifeline: asyncio.Event) -> None:
        """Start monitoring. Initiates shutdown when lifeline is cleared."""
        self._monitor_task = asyncio.create_task(self._monitor(lifeline))

    async def _monitor(self, lifeline: asyncio.Event) -> None:
        await lifeline.wait()
        await self.graceful_shutdown()

    async def graceful_shutdown(self) -> None:
        """Phase 1: SIGTERM, wait grace period, Phase 2: SIGKILL if alive."""
        try:
            import psutil
            if not psutil.pid_exists(self._pid):
                return
            proc = psutil.Process(self._pid)
            proc.terminate()
            try:
                proc.wait(timeout=self._grace_period)
            except psutil.TimeoutExpired:
                proc.kill()
                logger.warning("Force-killed browser PID %d after grace period", self._pid)
        except ImportError:
            # Fallback without psutil
            try:
                os.kill(self._pid, signal.SIGTERM)
            except (ProcessLookupError, OSError):
                return

    async def force_shutdown(self) -> None:
        """Immediate SIGKILL / kill."""
        try:
            import psutil
            if psutil.pid_exists(self._pid):
                psutil.Process(self._pid).kill()
        except ImportError:
            try:
                os.kill(self._pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass

    async def stop(self) -> None:
        """Cancel the monitor task (normal shutdown path)."""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
