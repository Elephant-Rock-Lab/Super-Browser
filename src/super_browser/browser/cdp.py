"""CDP protocol bridge — direct Chrome DevTools Protocol access."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import time
from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Optional

from super_browser.browser.config import SessionConfig

logger = logging.getLogger(__name__)


class ForbiddenCdpMethodError(Exception):
    """Raised when a forbidden CDP method is called.

    Certain CDP methods (e.g. ``Runtime.enable``) must never be called
    because they expose the browser to detection.  The hard-ban is
    enforced at the :class:`CDPBridge` level.
    """

    def __init__(self, method: str) -> None:
        self.method = method
        super().__init__(
            f"CDP method {method!r} is forbidden — "
            "it would expose the browser to fingerprint detection"
        )

# Virtual key code mapping for CDP Input.dispatchKeyEvent
VIRTUAL_KEY_CODES: dict[str, str] = {
    "Enter": "\r", "Return": "\r",
    "Tab": "\t",
    "Escape": "\x1b",
    "Backspace": "\x08",
    "Delete": "\x7f",
    "Home": "\x01",
    "End": "\x04",
    "PageUp": "\x0b",
    "PageDown": "\x0c",
    "ArrowLeft": "\x1b[D",
    "ArrowRight": "\x1b[C",
    "ArrowUp": "\x1b[A",
    "ArrowDown": "\x1b[B",
    "F1": "\x1bOP", "F2": "\x1bOQ", "F3": "\x1bOR", "F4": "\x1bOS",
}


@dataclass(frozen=True)
class CDPResult:
    """Result from a CDP protocol call."""
    ok: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    method: Optional[str] = None
    duration_ms: float = 0.0
    screenshot_hash: Optional[str] = None


class CDPBridge:
    """Raw CDP protocol bridge over a Patchright CDPSession.

    Provides compositor-level operations (click, type, key press),
    screenshot capture, evaluate, event buffering, and stale session recovery.
    """

    _FORBIDDEN_METHODS: frozenset[str] = frozenset({
        "Runtime.enable",
        "Page.createIsolatedWorld",
    })

    def __init__(self, cdp_session: Any, config: SessionConfig) -> None:
        self._session = cdp_session
        self._config = config
        self._events: deque[dict] = deque(maxlen=config.event_buffer_size)
        self._handlers: dict[str, list[Callable]] = {}
        self._reattach_fn: Optional[Callable] = None

        # Tap into CDP events for buffering
        try:
            cdp_session.on("*", self._buffer_event)
        except Exception:
            pass  # Patchright CDPSession may not support wildcard

    def set_reattach_fn(self, fn: Callable) -> None:
        """Register a callback to re-create the CDP session on stale recovery."""
        self._reattach_fn = fn

    def _buffer_event(self, params: Any = None, **kwargs: Any) -> None:
        if isinstance(params, dict):
            self._events.append(params)
            method = params.get("method", "")
            if method and method in self._handlers:
                for handler in self._handlers[method]:
                    try:
                        handler(params)
                    except Exception:
                        pass

    # -- Core CDP --

    async def send(self, method: str, params: Optional[dict] = None) -> CDPResult:
        """Send a CDP command with timing and stale recovery."""
        if method in self._FORBIDDEN_METHODS:
            raise ForbiddenCdpMethodError(method)
        start = time.monotonic()
        try:
            result = await self._session.send(method, params or {})
            elapsed = (time.monotonic() - start) * 1000
            return CDPResult(ok=True, data=result, method=method, duration_ms=elapsed)
        except Exception as e:
            if self._config.stale_recovery and "Session with given id not found" in str(e):
                if self._reattach_fn:
                    logger.info("Stale CDP session, reattaching...")
                    self._session = await self._reattach_fn()
                    try:
                        result = await self._session.send(method, params or {})
                        elapsed = (time.monotonic() - start) * 1000
                        return CDPResult(ok=True, data=result, method=method, duration_ms=elapsed)
                    except Exception as retry_err:
                        elapsed = (time.monotonic() - start) * 1000
                        return CDPResult(ok=False, error=str(retry_err), method=method, duration_ms=elapsed)
            elapsed = (time.monotonic() - start) * 1000
            return CDPResult(ok=False, error=str(e), method=method, duration_ms=elapsed)

    # -- Compositor Operations --

    async def compositor_click(
        self,
        x: float,
        y: float,
        button: str = "left",
        click_count: int = 1,
    ) -> CDPResult:
        """Dispatch mousePressed + mouseReleased at viewport coordinates."""
        r1 = await self.send("Input.dispatchMouseEvent", {
            "type": "mousePressed",
            "x": x, "y": y,
            "button": button,
            "clickCount": click_count,
        })
        if not r1.ok:
            return r1
        r2 = await self.send("Input.dispatchMouseEvent", {
            "type": "mouseReleased",
            "x": x, "y": y,
            "button": button,
            "clickCount": click_count,
        })
        return r2

    async def compositor_type(self, text: str, delay_ms: float = 0) -> CDPResult:
        """Type text character-by-character via CDP key events."""
        for ch in text:
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyDown", "text": ch,
            })
            await self.send("Input.dispatchKeyEvent", {
                "type": "char", "text": ch,
            })
            await self.send("Input.dispatchKeyEvent", {
                "type": "keyUp", "text": ch,
            })
            if delay_ms > 0:
                await asyncio.sleep(delay_ms / 1000)
        return CDPResult(ok=True, method="compositor_type")

    async def compositor_key_press(self, key: str, modifiers: int = 0) -> CDPResult:
        """Press a key with optional modifier bitmask (1=Alt,2=Ctrl,4=Shift,8=Meta)."""
        text = VIRTUAL_KEY_CODES.get(key, key)
        params: dict[str, Any] = {
            "type": "keyDown",
            "key": key,
            "text": text,
            "modifiers": modifiers,
        }
        r1 = await self.send("Input.dispatchKeyEvent", params)
        if not r1.ok:
            return r1
        params["type"] = "keyUp"
        return await self.send("Input.dispatchKeyEvent", params)

    # -- Screenshot --

    async def capture_screenshot(
        self,
        format: str = "png",
        quality: Optional[int] = None,
        clip: Optional[dict] = None,
        full_page: bool = False,
    ) -> CDPResult:
        """Capture screenshot via Page.captureScreenshot."""
        params: dict[str, Any] = {"format": format}
        if quality is not None:
            params["quality"] = quality
        if clip:
            params["clip"] = clip
        params["captureBeyondViewport"] = full_page

        result = await self.send("Page.captureScreenshot", params)
        if result.ok and result.data and "data" in result.data:
            raw = base64.b64decode(result.data["data"])
            sha = hashlib.sha256(raw).hexdigest()
            return CDPResult(
                ok=True, data=result.data, method="captureScreenshot",
                duration_ms=result.duration_ms, screenshot_hash=sha,
            )
        return result

    # -- Evaluate --

    async def evaluate(self, expression: str, return_by_value: bool = True) -> CDPResult:
        """Evaluate JavaScript via Runtime.evaluate."""
        return await self.send("Runtime.evaluate", {
            "expression": expression,
            "returnByValue": return_by_value,
        })

    # -- Events --

    def on_event(self, pattern: str, handler: Callable) -> None:
        """Register an event handler for a CDP event pattern."""
        self._handlers.setdefault(pattern, []).append(handler)

    def drain_events(self) -> list[dict]:
        """Return and clear all buffered CDP events."""
        events = list(self._events)
        self._events.clear()
        return events

    @property
    def session_id(self) -> Optional[str]:
        try:
            return self._session.id  # type: ignore[attr-defined]
        except AttributeError:
            return None
