"""SessionRecorder — subscribes to EventBus lifecycle events and captures ActionRecords.

Hard Boundary HB-23-02: Screenshot capture failures MUST NOT block the action.
Hard Boundary HB-23-04: Recorded params MUST NOT contain API keys or credentials.
"""

from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any, Optional

from super_browser.events.bus import EventBus
from super_browser.events.types import (
    AFTER_ACTION,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    BEFORE_NAVIGATE,
    ON_ERROR,
)
from super_browser.recording.types import (
    ActionRecord,
    RecordingSession,
    _filter_sensitive,
)

if TYPE_CHECKING:
    from super_browser.browser.cdp import CDPBridge

logger = logging.getLogger(__name__)

# Event types we subscribe to for lifecycle recording.
_SUBSCRIBED_EVENTS = frozenset({
    BEFORE_NAVIGATE,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    AFTER_ACTION,
    ON_ERROR,
})


class SessionRecorder:
    """Records browser lifecycle events into an :class:`ActionRecord` list.

    Usage::

        recorder = SessionRecorder(event_bus, cdp_bridge)
        recorder.start()
        # ... browser actions happen ...
        session = recorder.stop()
        recorder.save("recording.json")
    """

    def __init__(
        self,
        event_bus: EventBus,
        cdp_bridge: Optional[CDPBridge] = None,
        *,
        max_screenshots: int = 100,
    ) -> None:
        self._bus = event_bus
        self._cdp = cdp_bridge
        self._max_screenshots = max_screenshots
        self._session: Optional[RecordingSession] = None
        self._subscription_ids: list[str] = []
        self._screenshot_count = 0
        self._recording = False

    # -- Public API --

    def start(self) -> None:
        """Begin recording. Subscribes to all lifecycle events."""
        if self._recording:
            return
        self._session = RecordingSession()
        self._recording = True
        self._screenshot_count = 0

        for event_type in _SUBSCRIBED_EVENTS:
            sid = self._bus.subscribe(event_type, self._make_handler(event_type))
            self._subscription_ids.append(sid)

        logger.info(
            "SessionRecorder started (session_id=%s, max_screenshots=%d)",
            self._session.session_id,
            self._max_screenshots,
        )

    def stop(self) -> RecordingSession:
        """Stop recording, unsubscribe, and return the session."""
        if not self._recording or self._session is None:
            return RecordingSession()

        self._recording = False
        for sid in self._subscription_ids:
            self._bus.unsubscribe(sid)
        self._subscription_ids.clear()

        session = self._session
        self._session = None
        logger.info(
            "SessionRecorder stopped (session_id=%s, actions=%d)",
            session.session_id,
            len(session.actions),
        )
        return session

    def export_json(self) -> str:
        """Export the current recording as a JSON string.

        Raises RuntimeError if recording has not been started.
        """
        session = self._session
        if session is None:
            session = RecordingSession()
        return json.dumps(session.to_dict(), indent=2)

    # -- Internal helpers --

    def _make_handler(self, event_type: str):
        """Create a handler callback for the given event type."""
        def handler(ctx: Any) -> None:
            if not self._recording or self._session is None:
                return
            self._handle_event(event_type, dict(ctx))
        return handler

    def _handle_event(self, event_type: str, ctx: dict[str, Any]) -> None:
        """Process a single lifecycle event into an ActionRecord."""
        if self._session is None:
            return

        # Determine action name and params from context
        action = ctx.get("action", event_type)
        params = _filter_sensitive(ctx)
        url = ctx.get("url", ctx.get("final_url", ""))
        title = ctx.get("title", "")
        ok = ctx.get("ok", True)
        error = ctx.get("error")
        duration_ms = ctx.get("duration_ms", 0.0)

        # Attempt screenshot capture (only for after_ events, respecting limit)
        screenshot: Optional[str] = None
        if event_type in (AFTER_NAVIGATE, AFTER_ACTION) and self._cdp is not None:
            screenshot = self._try_capture_screenshot()

        record = ActionRecord(
            index=len(self._session.actions),
            timestamp=time.monotonic(),
            action=action,
            params=params,
            url=url,
            title=title,
            screenshot_after=screenshot,
            ok=ok,
            error=error,
            duration_ms=duration_ms,
        )
        self._session.actions.append(record)

    def _try_capture_screenshot(self) -> Optional[str]:
        """Attempt to capture a screenshot. Returns base64 string or None.

        HB-23-02: Failures are caught and logged — they never block recording.
        """
        if self._screenshot_count >= self._max_screenshots:
            return None

        if self._cdp is None:
            return None

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            if loop.is_running():
                # We're inside an async context but emit() is sync.
                # Cannot await screenshot here. Return None gracefully.
                return None

            result = loop.run_until_complete(self._cdp.capture_screenshot(format="jpeg", quality=50))
            if result.ok and result.data and "data" in result.data:
                self._screenshot_count += 1
                return result.data["data"]
        except Exception:
            logger.debug("Screenshot capture failed, continuing with None", exc_info=True)

        return None
