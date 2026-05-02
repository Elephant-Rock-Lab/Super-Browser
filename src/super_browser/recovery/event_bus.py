"""WatchdogEventBus — bounded async event bus for watchdog communication."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from super_browser.recovery.types import WatchdogEvent, WatchdogEventData

logger = logging.getLogger(__name__)


class WatchdogEventBus:
    def __init__(self, max_queue_size: int = 100) -> None:
        self._queues: dict[WatchdogEvent, list[asyncio.Queue]] = {}
        self._handlers: list[tuple[list[WatchdogEvent], Callable]] = []
        self._max_size = max_queue_size
        self._history: list[WatchdogEventData] = []

    async def emit(self, event: WatchdogEventData) -> None:
        self._history.append(event)
        queues = self._queues.get(event.event_type, [])
        for q in queues:
            if q.full():
                try:
                    q.get_nowait()
                except asyncio.QueueEmpty:
                    pass
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass

        for event_types, handler in self._handlers:
            if event.event_type in event_types:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception as exc:
                    logger.debug("Event handler error: %s", exc)

    def listen(self, event_type: WatchdogEvent) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=self._max_size)
        if event_type not in self._queues:
            self._queues[event_type] = []
        self._queues[event_type].append(q)
        return q

    def subscribe(self, event_types: list[WatchdogEvent], handler: Callable) -> None:
        self._handlers.append((event_types, handler))

    def drain(self) -> list[WatchdogEventData]:
        events = list(self._history)
        return events

    def clear(self) -> None:
        self._history.clear()
        for ql in self._queues.values():
            for q in ql:
                while not q.empty():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        break
