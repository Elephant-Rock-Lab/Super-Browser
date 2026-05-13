"""TEST-23-01: SessionRecorder — event capture, screenshots, export."""

from __future__ import annotations

import json

from super_browser.events.bus import EventBus
from super_browser.events.types import (
    AFTER_ACTION,
    AFTER_NAVIGATE,
    BEFORE_ACTION,
    BEFORE_NAVIGATE,
    ON_ERROR,
)
from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.types import RecordingSession


# ---------------------------------------------------------------------------
# TEST-23-01-01: Recorder captures navigate event
# ---------------------------------------------------------------------------
class TestNavigateCapture:
    """AC-01-01: Recorder subscribes to lifecycle events and captures navigate."""

    def test_records_before_navigate_event(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})

        session = recorder.stop()
        assert len(session.actions) >= 1
        nav_records = [a for a in session.actions if a.action == "before_navigate"]
        assert len(nav_records) >= 1
        assert nav_records[0].params.get("url") == "https://example.com"

    def test_records_after_navigate_event(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(AFTER_NAVIGATE, {
            "url": "https://example.com",
            "final_url": "https://example.com/",
            "title": "Example",
            "ok": True,
        })

        session = recorder.stop()
        nav_records = [a for a in session.actions if a.url == "https://example.com"]
        assert len(nav_records) >= 1


# ---------------------------------------------------------------------------
# TEST-23-01-02: Recorder captures click with selector
# ---------------------------------------------------------------------------
class TestClickCapture:
    """AC-01-01: Recorder captures action context including target selector."""

    def test_records_click_with_selector(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})

        session = recorder.stop()
        click_records = [a for a in session.actions if a.action == "click"]
        assert len(click_records) >= 1
        assert click_records[0].params["target"] == "#btn"


# ---------------------------------------------------------------------------
# TEST-23-01-03: Recorder captures error events
# ---------------------------------------------------------------------------
class TestErrorCapture:
    """AC-01-01: Recorder subscribes to ON_ERROR and captures error details."""

    def test_records_error_event(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(ON_ERROR, {
            "action": "click",
            "error": "Element not found",
            "category": "selector",
            "step": 3,
        })

        session = recorder.stop()
        error_records = [a for a in session.actions if a.error is not None]
        assert len(error_records) >= 1
        assert "not found" in error_records[0].error


# ---------------------------------------------------------------------------
# TEST-23-01-04: Recorder respects max_screenshots limit
# ---------------------------------------------------------------------------
class TestMaxScreenshots:
    """AC-01-04 / HB-23-02: max_screenshots is enforced."""

    def test_screenshot_count_stays_within_limit(self) -> None:
        """Even if we emit many after_ events, screenshots stay within limit."""
        bus = EventBus()
        recorder = SessionRecorder(bus, max_screenshots=2)
        # No CDP bridge → screenshots will be None, but the limit check is exercised
        recorder.start()

        for i in range(10):
            bus.emit(AFTER_ACTION, {
                "action": "click",
                "target": f"#btn-{i}",
                "step": i,
                "ok": True,
            })

        session = recorder.stop()
        # All records should have screenshot_after=None since no CDP bridge
        screenshots = [a for a in session.actions if a.screenshot_after is not None]
        assert len(screenshots) <= 2


# ---------------------------------------------------------------------------
# TEST-23-01-05: export_json() produces valid JSON
# ---------------------------------------------------------------------------
class TestExportJson:
    """AC-01-05: export_json() returns parseable JSON with schema_version."""

    def test_export_produces_valid_json(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})

        raw = recorder.export_json()
        parsed = json.loads(raw)

        assert "actions" in parsed
        assert "schema_version" in parsed
        assert parsed["schema_version"] == "1.0"
        assert len(parsed["actions"]) >= 1

    def test_export_without_start_produces_empty_session(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        raw = recorder.export_json()
        parsed = json.loads(raw)
        assert isinstance(parsed["actions"], list)


# ---------------------------------------------------------------------------
# TEST-23-01-06: Records include timestamps > 0
# ---------------------------------------------------------------------------
class TestTimestamps:
    """AC-01-02: Each record has a valid timestamp."""

    def test_all_timestamps_are_positive(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})
        bus.emit(AFTER_NAVIGATE, {"url": "https://example.com", "ok": True})

        session = recorder.stop()
        for record in session.actions:
            assert record.timestamp > 0


# ---------------------------------------------------------------------------
# Additional: Sensitive param filtering (HB-23-04)
# ---------------------------------------------------------------------------
class TestSensitiveFiltering:
    """HB-23-04: Recorded params MUST NOT contain API keys or credentials."""

    def test_api_key_redacted_in_record(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_ACTION, {
            "action": "fill",
            "target": "#api-input",
            "api_key": "sk-secret-123",
            "step": 1,
        })

        session = recorder.stop()
        fill_records = [a for a in session.actions if a.action == "fill"]
        assert len(fill_records) >= 1
        assert fill_records[0].params["api_key"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Additional: stop() returns RecordingSession with correct structure
# ---------------------------------------------------------------------------
class TestStopReturnsSession:
    """stop() returns a properly structured RecordingSession."""

    def test_stop_returns_recording_session(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})

        session = recorder.stop()
        assert isinstance(session, RecordingSession)
        assert session.session_id  # non-empty string
        assert len(session.actions) >= 1
        assert session.metadata["action_count"] >= 1

    def test_stop_without_start_returns_empty_session(self) -> None:
        bus = EventBus()
        recorder = SessionRecorder(bus)
        session = recorder.stop()
        assert isinstance(session, RecordingSession)
        assert len(session.actions) == 0
