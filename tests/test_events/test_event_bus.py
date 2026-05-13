"""TEST-22-01: EventBus core — sync/async handlers, error isolation, unsubscribe."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from super_browser.events.bus import EventBus
from super_browser.events.types import BEFORE_ACTION, BEFORE_NAVIGATE


# ---------------------------------------------------------------------------
# TEST-22-01-01: EventBus registers and calls sync handler
# ---------------------------------------------------------------------------
class TestSyncHandlerCalled:
    """AC-01-01: EventBus.emit() calls all registered handlers for the event type."""

    def test_sync_handler_called_on_emit(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(BEFORE_NAVIGATE, handler)
        ctx = {"url": "https://example.com"}
        bus.emit(BEFORE_NAVIGATE, ctx)
        assert handler.call_count == 1
        handler.assert_called_once()
        # Verify context dict passed
        args = handler.call_args[0]
        assert args[0]["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# TEST-22-01-02: EventBus registers and calls async handler
# ---------------------------------------------------------------------------
class TestAsyncHandlerCalled:
    """AC-01-04: Both sync and async handlers are supported."""

    @pytest.mark.asyncio
    async def test_async_handler_called_on_emit_async(self) -> None:
        bus = EventBus()
        handler = AsyncMock()
        bus.subscribe(BEFORE_NAVIGATE, handler)
        ctx = {"url": "https://example.com"}
        await bus.emit_async(BEFORE_NAVIGATE, ctx)
        assert handler.call_count == 1
        args = handler.call_args[0][0]
        assert args["url"] == "https://example.com"

    @pytest.mark.asyncio
    async def test_sync_handler_called_via_emit_async(self) -> None:
        """Sync handlers also fire when emit_async is used."""
        bus = EventBus()
        sync_handler = MagicMock()
        bus.subscribe(BEFORE_ACTION, sync_handler)
        ctx = {"action": "click", "target": "#btn", "step": 1}
        await bus.emit_async(BEFORE_ACTION, ctx)
        assert sync_handler.call_count == 1


# ---------------------------------------------------------------------------
# TEST-22-01-03: One failing handler does not block others
# ---------------------------------------------------------------------------
class TestErrorIsolation:
    """AC-01-02: Handler errors are caught, logged, and do not propagate."""

    def test_failing_handler_does_not_block_others(self) -> None:
        bus = EventBus()
        failing = MagicMock(side_effect=RuntimeError("boom"))
        ok_handler = MagicMock()
        bus.subscribe(BEFORE_NAVIGATE, failing)
        bus.subscribe(BEFORE_NAVIGATE, ok_handler)

        # emit must NOT raise
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})

        assert failing.call_count == 1
        assert ok_handler.call_count == 1

    def test_emit_never_propagates_handler_exception(self) -> None:
        bus = EventBus()
        bus.subscribe(BEFORE_NAVIGATE, lambda ctx: (_ for _ in ()).throw(RuntimeError("boom")))
        # Must not raise
        bus.emit(BEFORE_NAVIGATE, {"url": "https://x.com"})

    @pytest.mark.asyncio
    async def test_async_failing_handler_does_not_block_others(self) -> None:
        bus = EventBus()
        failing = AsyncMock(side_effect=RuntimeError("async boom"))
        ok_handler = AsyncMock()
        bus.subscribe(BEFORE_NAVIGATE, failing)
        bus.subscribe(BEFORE_NAVIGATE, ok_handler)

        await bus.emit_async(BEFORE_NAVIGATE, {"url": "https://example.com"})

        assert failing.call_count == 1
        assert ok_handler.call_count == 1


# ---------------------------------------------------------------------------
# TEST-22-01-04: Unsubscribe stops handler from being called
# ---------------------------------------------------------------------------
class TestUnsubscribe:
    """AC-01-03: Handlers can be unsubscribed via subscription_id."""

    def test_handler_not_called_after_unsubscribe(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        sub_id = bus.subscribe(BEFORE_NAVIGATE, handler)
        bus.unsubscribe(sub_id)
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
        assert handler.call_count == 0

    def test_unsubscribe_invalid_id_is_noop(self) -> None:
        bus = EventBus()
        # Must not raise
        bus.unsubscribe("nonexistent-id")

    def test_other_handlers_still_fire_after_unsubscribe(self) -> None:
        bus = EventBus()
        h1 = MagicMock()
        h2 = MagicMock()
        sid = bus.subscribe(BEFORE_NAVIGATE, h1)
        bus.subscribe(BEFORE_NAVIGATE, h2)
        bus.unsubscribe(sid)
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
        assert h1.call_count == 0
        assert h2.call_count == 1


# ---------------------------------------------------------------------------
# TEST-22-01-05: Typed events only reach matching subscribers
# ---------------------------------------------------------------------------
class TestEventTypeFiltering:
    """AC-01-01 (extended): Only matching event type handlers fire."""

    def test_wrong_event_type_handler_not_called(self) -> None:
        bus = EventBus()
        nav_handler = MagicMock()
        action_handler = MagicMock()
        bus.subscribe(BEFORE_NAVIGATE, nav_handler)
        bus.subscribe(BEFORE_ACTION, action_handler)

        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})

        assert nav_handler.call_count == 1
        assert action_handler.call_count == 0

    def test_emit_with_no_subscribers_is_noop(self) -> None:
        bus = EventBus()
        # Must not raise
        bus.emit("nonexistent_event", {"key": "value"})


# ---------------------------------------------------------------------------
# TEST-22-01-06: emit() overhead is <1ms
# ---------------------------------------------------------------------------
class TestPerformance:
    """AC-01-05: emit() overhead is <1ms per action (HB-22-04)."""

    def test_emit_overhead_under_1ms(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(BEFORE_NAVIGATE, handler)
        ctx = {"url": "https://example.com"}

        # Warm up
        bus.emit(BEFORE_NAVIGATE, ctx)

        iterations = 100
        start = time.monotonic()
        for _ in range(iterations):
            bus.emit(BEFORE_NAVIGATE, ctx)
        elapsed_ms = (time.monotonic() - start) * 1000

        avg_ms = elapsed_ms / iterations
        assert avg_ms < 1.0, f"emit() overhead {avg_ms:.3f}ms exceeds 1ms limit"
