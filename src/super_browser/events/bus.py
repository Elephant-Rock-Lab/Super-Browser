"""EventBus — typed pub/sub with sync and async handler support.

Hard Boundary HB-22-01: ``emit()`` MUST never raise — handler errors are
caught, logged, and MUST NOT propagate to the caller.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from types import MappingProxyType
from typing import Any

from super_browser.events.types import Handler

logger = logging.getLogger(__name__)


class EventBus:
    """Synchronous-first event bus with optional async emission.

    Usage::

        bus = EventBus()
        sid = bus.subscribe("before_navigate", lambda ctx: print(ctx["url"]))
        bus.emit("before_navigate", {"url": "https://example.com"})
        bus.unsubscribe(sid)
    """

    def __init__(self) -> None:
        # event_type → list[handler]
        self._handlers: dict[str, list[Handler]] = {}
        # subscription_id → (event_type, handler)
        self._subscriptions: dict[str, tuple[str, Handler]] = {}

    # -- Registration --

    def subscribe(self, event_type: str, handler: Handler) -> str:
        """Register *handler* for *event_type*. Returns a subscription ID."""
        sub_id = uuid.uuid4().hex
        self._handlers.setdefault(event_type, []).append(handler)
        self._subscriptions[sub_id] = (event_type, handler)
        return sub_id

    def unsubscribe(self, subscription_id: str) -> None:
        """Remove a previously registered handler by its subscription ID."""
        entry = self._subscriptions.pop(subscription_id, None)
        if entry is None:
            return
        event_type, handler = entry
        handler_list = self._handlers.get(event_type)
        if handler_list is None:
            return
        try:
            handler_list.remove(handler)
        except ValueError:
            pass  # already removed or list mutated
        if not handler_list:
            self._handlers.pop(event_type, None)

    # -- Sync emission --

    def emit(self, event_type: str, context: dict[str, Any]) -> None:
        """Emit *event_type* synchronously.  **Never raises.**

        Handler errors are caught and logged.  The *context* dict is passed
        as read-only (``MappingProxyType``) to prevent handlers from
        mutating it (HB-22-03).
        """
        handlers = self._handlers.get(event_type)
        if not handlers:
            return
        frozen = MappingProxyType(context)
        for handler in handlers:
            try:
                result = handler(frozen)
                # If the handler is a coroutine (async def), warn but don't await
                if asyncio.iscoroutine(result):
                    logger.warning(
                        "Async handler registered for sync emit of %r — "
                        "use emit_async() instead. Handler will NOT be awaited.",
                        event_type,
                    )
            except Exception:
                logger.exception(
                    "EventBus handler error for event %r", event_type,
                )

    # -- Async emission --

    async def emit_async(self, event_type: str, context: dict[str, Any]) -> None:
        """Emit *event_type* asynchronously.  **Never raises.**

        Both sync and async handlers are supported.  Sync handlers are
        called directly; async handlers are ``await``-ed.
        """
        handlers = self._handlers.get(event_type)
        if not handlers:
            return
        frozen = MappingProxyType(context)
        for handler in handlers:
            try:
                result = handler(frozen)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception(
                    "EventBus async handler error for event %r", event_type,
                )
