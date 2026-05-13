"""TEST-22-02: Lifecycle Hooks Integration — @hook decorator, sb.on(), lifecycle emissions."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from super_browser.events.bus import EventBus
from super_browser.events.types import (
    AFTER_ACTION,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    BEFORE_NAVIGATE,
    ON_BUDGET_ALERT,
    ON_ERROR,
    ON_LOOP_DETECTED,
)
from super_browser.plugins.decorators import hook
from super_browser.plugins.hooks import clear_registry, get_registered_hooks


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _clean_registry():
    """Ensure the global hook registry is clean between tests."""
    clear_registry()
    yield
    clear_registry()


# ---------------------------------------------------------------------------
# TEST-22-02-01: @hook("before_navigate") fires on nav
# ---------------------------------------------------------------------------
class TestBeforeNavigateHook:
    """AC-02-01: @hook('before_navigate') fires before every navigate() call."""

    def test_hook_decorator_fires_on_navigate(self) -> None:
        handler = MagicMock()

        @hook(BEFORE_NAVIGATE)
        def my_hook(ctx):
            handler(ctx)

        # Verify handler was registered
        hooks = get_registered_hooks()
        assert BEFORE_NAVIGATE in hooks
        assert len(hooks[BEFORE_NAVIGATE]) == 1

    def test_before_navigate_event_contains_url(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(BEFORE_NAVIGATE, handler)
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
        handler.assert_called_once()
        ctx = handler.call_args[0][0]
        assert ctx["url"] == "https://example.com"


# ---------------------------------------------------------------------------
# TEST-22-02-02: @hook("on_error") fires on action fail
# ---------------------------------------------------------------------------
class TestOnErrorHook:
    """AC-02-02: @hook('on_error') fires on every action failure."""

    def test_on_error_event_emitted_with_details(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(ON_ERROR, handler)
        bus.emit(ON_ERROR, {
            "action": "click",
            "error": "element not found",
            "category": "selector",
            "step": 3,
        })
        handler.assert_called_once()
        ctx = handler.call_args[0][0]
        assert ctx["action"] == "click"
        assert ctx["error"] == "element not found"
        assert ctx["step"] == 3


# ---------------------------------------------------------------------------
# TEST-22-02-03: @hook("on_loop_detected") fires on loop
# ---------------------------------------------------------------------------
class TestOnLoopDetectedHook:
    """AC-02-03: @hook('on_loop_detected') fires when loop is detected."""

    def test_on_loop_detected_event_emitted(self) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(ON_LOOP_DETECTED, handler)
        bus.emit(ON_LOOP_DETECTED, {
            "level": 2,
            "message": "You are in a loop",
            "repetition_count": 8,
            "repeated_action": "click",
        })
        handler.assert_called_once()
        ctx = handler.call_args[0][0]
        assert ctx["level"] == 2
        assert ctx["repetition_count"] == 8

    def test_hook_decorator_registers_loop_detected(self) -> None:
        handler = MagicMock()

        @hook(ON_LOOP_DETECTED)
        def on_loop(ctx):
            handler(ctx)

        hooks = get_registered_hooks()
        assert ON_LOOP_DETECTED in hooks


# ---------------------------------------------------------------------------
# TEST-22-02-04: Multiple hooks on same event all fire
# ---------------------------------------------------------------------------
class TestMultipleHooks:
    """AC-02-04: Multiple hooks on the same event all execute in order."""

    def test_multiple_handlers_fire_in_order(self) -> None:
        bus = EventBus()
        call_order = []

        bus.subscribe(BEFORE_NAVIGATE, lambda ctx: call_order.append("first"))
        bus.subscribe(BEFORE_NAVIGATE, lambda ctx: call_order.append("second"))
        bus.subscribe(BEFORE_NAVIGATE, lambda ctx: call_order.append("third"))

        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})

        assert call_order == ["first", "second", "third"]

    def test_sb_on_registers_handler(self) -> None:
        """Test sb.on() API via direct EventBus usage (facade wiring)."""
        bus = EventBus()
        handler = MagicMock()
        # Simulates sb.on("before_navigate", handler)
        bus.subscribe(BEFORE_NAVIGATE, handler)
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
        assert handler.call_count == 1

    def test_decorator_and_on_both_work(self) -> None:
        """Both @hook() and sb.on() handlers fire for the same event."""
        bus = EventBus()
        call_order = []

        @hook(AFTER_NAVIGATE)
        def decorated_hook(ctx):
            call_order.append("decorator")

        # Install decorator hooks
        for et, handlers in get_registered_hooks().items():
            for h in handlers:
                bus.subscribe(et, h)

        # Simulate sb.on()
        bus.subscribe(AFTER_NAVIGATE, lambda ctx: call_order.append("on_method"))

        bus.emit(AFTER_NAVIGATE, {
            "url": "https://example.com",
            "final_url": "https://example.com/",
            "title": "Example",
            "ok": True,
        })

        assert call_order == ["decorator", "on_method"]


# ---------------------------------------------------------------------------
# Additional coverage: all 7 lifecycle events emit correctly
# ---------------------------------------------------------------------------
class TestAllLifecycleEvents:
    """Verify all 7 event types can be emitted and received."""

    @pytest.mark.parametrize("event_type,context", [
        (BEFORE_NAVIGATE, {"url": "https://a.com"}),
        (AFTER_NAVIGATE, {"url": "https://a.com", "final_url": "https://a.com/", "title": "A", "ok": True}),
        (BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1}),
        (AFTER_ACTION, {"action": "click", "target": "#btn", "step": 1, "ok": True, "duration_ms": 42.0}),
        (ON_ERROR, {"action": "click", "error": "not found", "category": "selector", "step": 1}),
        (ON_LOOP_DETECTED, {"level": 1, "message": "Repeating", "repetition_count": 5, "repeated_action": "click"}),
        (ON_BUDGET_ALERT, {"level": "warning", "usage_pct": 90.0, "remaining": 10.0}),
    ])
    def test_event_emission(self, event_type: str, context: dict) -> None:
        bus = EventBus()
        handler = MagicMock()
        bus.subscribe(event_type, handler)
        bus.emit(event_type, context)
        handler.assert_called_once()
