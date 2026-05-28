"""TEST-23-02: Persistence & HTML Export — save/load JSON, HTML report generation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from super_browser.events.bus import EventBus
from super_browser.events.types import BEFORE_ACTION, BEFORE_NAVIGATE, ON_ERROR
from super_browser.recording.persistence import load, save
from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.report import export_html, save_html
from super_browser.recording.types import RecordingSession


def _make_session_with_actions() -> RecordingSession:
    """Helper: create a session with some recorded actions."""
    bus = EventBus()
    recorder = SessionRecorder(bus)
    recorder.start()

    bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
    bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})
    bus.emit(ON_ERROR, {"action": "fill", "error": "Element not found", "category": "selector", "step": 2})

    return recorder.stop()


# ---------------------------------------------------------------------------
# TEST-23-02-01: save() writes JSON file to disk
# ---------------------------------------------------------------------------
class TestSaveJson:
    """AC-02-01: save() writes a valid JSON file that load() can reconstruct."""

    def test_save_creates_file(self, tmp_path: Path) -> None:
        session = _make_session_with_actions()
        path = tmp_path / "recording.json"
        save(session, str(path))

        assert path.exists()

    def test_save_creates_parent_dirs(self, tmp_path: Path) -> None:
        session = RecordingSession()
        path = tmp_path / "nested" / "dir" / "rec.json"
        save(session, str(path))
        assert path.exists()


# ---------------------------------------------------------------------------
# TEST-23-02-02: load() reconstructs full recording
# ---------------------------------------------------------------------------
class TestLoadJson:
    """AC-02-01: load() reconstructs a RecordingSession identical to saved."""

    def test_load_roundtrip_preserves_actions(self, tmp_path: Path) -> None:
        original = _make_session_with_actions()
        path = tmp_path / "rec.json"
        save(original, str(path))

        loaded = load(str(path))

        assert len(loaded.actions) == len(original.actions)
        for orig, load_a in zip(original.actions, loaded.actions):
            assert orig.action == load_a.action
            assert orig.params == load_a.params
            assert orig.ok == load_a.ok
            assert orig.error == load_a.error

    def test_load_preserves_session_id(self, tmp_path: Path) -> None:
        original = _make_session_with_actions()
        path = tmp_path / "rec.json"
        save(original, str(path))

        loaded = load(str(path))
        assert loaded.session_id == original.session_id

    def test_load_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            load(str(tmp_path / "nonexistent.json"))

    def test_load_invalid_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            load(str(path))

    def test_load_missing_actions_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "no_actions.json"
        path.write_text('{"session_id": "abc"}', encoding="utf-8")
        with pytest.raises(ValueError, match="missing 'actions'"):
            load(str(path))


# ---------------------------------------------------------------------------
# TEST-23-02-03: export_html() produces valid HTML
# ---------------------------------------------------------------------------
class TestExportHtml:
    """AC-02-02: export_html() produces a human-readable audit report."""

    def test_html_contains_basic_structure(self) -> None:
        session = _make_session_with_actions()
        html = export_html(session)

        assert "<html" in html
        assert "</html>" in html
        assert "<table" in html
        assert "click" in html

    def test_html_contains_session_id(self) -> None:
        session = _make_session_with_actions()
        html = export_html(session)
        assert session.session_id in html

    def test_html_contains_error_info(self) -> None:
        session = _make_session_with_actions()
        html = export_html(session)
        assert "Element not found" in html

    def test_save_html_creates_file(self, tmp_path: Path) -> None:
        session = _make_session_with_actions()
        path = tmp_path / "report.html"
        save_html(session, str(path))
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "<html" in content


# ---------------------------------------------------------------------------
# TEST-23-02-04: Metadata includes action_count
# ---------------------------------------------------------------------------
class TestMetadata:
    """AC-02-03: Metadata includes action_count, error_count, duration_ms, schema_version."""

    def test_metadata_action_count(self) -> None:
        session = _make_session_with_actions()
        assert session.metadata["action_count"] == len(session.actions)

    def test_metadata_error_count(self) -> None:
        session = _make_session_with_actions()
        expected_errors = sum(1 for a in session.actions if not a.ok)
        assert session.metadata["error_count"] == expected_errors

    def test_metadata_has_schema_version(self) -> None:
        session = _make_session_with_actions()
        assert session.metadata["schema_version"] == "1.0"

    def test_metadata_has_duration_ms(self) -> None:
        session = _make_session_with_actions()
        assert "duration_ms" in session.metadata
        assert isinstance(session.metadata["duration_ms"], float)
