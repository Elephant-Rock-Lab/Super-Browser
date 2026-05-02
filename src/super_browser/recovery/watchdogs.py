"""Watchdogs — BaseWatchdog ABC and 5 concrete watchdog implementations."""

from __future__ import annotations

import asyncio
import fnmatch
import logging
import time
from abc import ABC, abstractmethod
from collections import deque
from typing import Any, Optional

from super_browser.agent.loop_detector import ActionLoopDetector
from super_browser.agent.types import LoopNudge
from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import (
    ActionFingerprint,
    NudgePayload,
    WatchdogEvent,
    WatchdogEventData,
)

logger = logging.getLogger(__name__)


class BaseWatchdog(ABC):
    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = []

    def __init__(self, event_bus: WatchdogEventBus) -> None:
        self._event_bus = event_bus
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._monitoring_loop())

    async def stop(self) -> None:
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _emit(
        self, event_type: WatchdogEvent, detail: str,
        severity: str = "warning", data: Optional[dict] = None,
    ) -> None:
        event = WatchdogEventData(
            event_type=event_type, source=self.name,
            detail=detail, severity=severity, data=data,
        )
        await self._event_bus.emit(event)

    @abstractmethod
    async def _monitoring_loop(self) -> None:
        ...

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def name(self) -> str:
        return type(self).__name__


class CrashWatchdog(BaseWatchdog):
    LISTENS_TO: list[WatchdogEvent] = []
    EMITS = [WatchdogEvent.CRASH_DETECTED, WatchdogEvent.SESSION_STALE]

    def __init__(
        self,
        event_bus: WatchdogEventBus,
        cdp: Any,
        check_interval: float = 5.0,
        network_timeout: float = 10.0,
    ) -> None:
        super().__init__(event_bus)
        self._cdp = cdp
        self._check_interval = check_interval
        self._network_timeout = network_timeout

    async def _monitoring_loop(self) -> None:
        while self._running:
            try:
                crashed = await self._check_liveness()
                if crashed:
                    await self._emit(
                        WatchdogEvent.CRASH_DETECTED, "Browser liveness check failed",
                        severity="critical",
                    )
                    return
            except Exception:
                await self._emit(
                    WatchdogEvent.SESSION_STALE, "CDP session unreachable",
                    severity="critical",
                )
                return
            await asyncio.sleep(self._check_interval)

    async def _check_liveness(self) -> bool:
        try:
            result = await asyncio.wait_for(
                self._cdp.evaluate("1+1"), timeout=self._network_timeout,
            )
            return not result.ok
        except asyncio.TimeoutError:
            return True
        except Exception:
            return True


class LoopWatchdog(BaseWatchdog):
    LISTENS_TO: list[WatchdogEvent] = []
    EMITS = [WatchdogEvent.LOOP_DETECTED, WatchdogEvent.NUDGE_INJECT]

    def __init__(self, event_bus: WatchdogEventBus, window_size: int = 20) -> None:
        super().__init__(event_bus)
        self._detector = ActionLoopDetector(window_size=window_size)

    def record_action(self, fingerprint: ActionFingerprint) -> Optional[NudgePayload]:
        action_dict = {
            "action_type": fingerprint.action_type,
            "target": fingerprint.target,
            "value": fingerprint.value,
        }
        nudge = self._detector.record_and_check(action_dict)
        if nudge is None:
            return None
        return NudgePayload(
            level=nudge.level,
            message=nudge.message,
            repetition_count=nudge.repetition_count,
            action_hash=fingerprint.hash,
        )

    async def _monitoring_loop(self) -> None:
        while self._running:
            await asyncio.sleep(1.0)


class NavigationWatchdog(BaseWatchdog):
    EMITS = [WatchdogEvent.NAVIGATION_TIMEOUT]

    def __init__(
        self,
        event_bus: WatchdogEventBus,
        cdp: Any = None,
        nav_timeout: float = 30.0,
    ) -> None:
        super().__init__(event_bus)
        self._cdp = cdp
        self._nav_timeout = nav_timeout
        self._nav_start: Optional[float] = None

    def mark_navigation_start(self) -> None:
        self._nav_start = time.monotonic()

    async def _monitoring_loop(self) -> None:
        while self._running:
            if self._nav_start is not None:
                elapsed = time.monotonic() - self._nav_start
                if elapsed > self._nav_timeout:
                    await self._emit(
                        WatchdogEvent.NAVIGATION_TIMEOUT,
                        f"Navigation exceeded {self._nav_timeout}s",
                        severity="warning",
                    )
                    self._nav_start = None
            await asyncio.sleep(1.0)


class StaleElementWatchdog(BaseWatchdog):
    EMITS = [WatchdogEvent.STALE_ELEMENT]

    def __init__(
        self,
        event_bus: WatchdogEventBus,
        cdp: Any = None,
        check_interval: float = 5.0,
    ) -> None:
        super().__init__(event_bus)
        self._cdp = cdp
        self._check_interval = check_interval
        self._last_count: Optional[int] = None

    async def _monitoring_loop(self) -> None:
        while self._running:
            if self._cdp:
                try:
                    result = await self._cdp.evaluate(
                        "document.querySelectorAll('*').length"
                    )
                    if result.ok and result.data:
                        count = result.data.get("result", {}).get("value", 0)
                        if self._last_count is not None and count != self._last_count:
                            self._last_count = count
                    elif self._last_count is not None:
                        await self._emit(
                            WatchdogEvent.STALE_ELEMENT,
                            "DOM element count check failed",
                        )
                except Exception:
                    pass
            await asyncio.sleep(self._check_interval)


class SecurityWatchdog(BaseWatchdog):
    EMITS = [WatchdogEvent.SECURITY_VIOLATION]

    def __init__(
        self,
        event_bus: WatchdogEventBus,
        allowed_domains: tuple[str, ...] = ("*",),
        blocked_domains: tuple[str, ...] = (),
        page: Any = None,
        check_interval: float = 5.0,
    ) -> None:
        super().__init__(event_bus)
        self._allowed = allowed_domains
        self._blocked = blocked_domains
        self._page = page
        self._check_interval = check_interval

    def is_allowed(self, url: str) -> bool:
        if "*" in self._allowed:
            pass
        else:
            matched = any(fnmatch.fnmatch(url, p) for p in self._allowed)
            if not matched:
                return False

        if self._blocked:
            matched = any(fnmatch.fnmatch(url, p) for p in self._blocked)
            if matched:
                return False
        return True

    async def _monitoring_loop(self) -> None:
        while self._running:
            if self._page:
                url = getattr(self._page, "url", "")
                if url and not self.is_allowed(url):
                    await self._emit(
                        WatchdogEvent.SECURITY_VIOLATION,
                        f"Blocked domain: {url}",
                        severity="critical",
                    )
            await asyncio.sleep(self._check_interval)
