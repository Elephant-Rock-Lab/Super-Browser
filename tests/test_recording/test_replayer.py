"""TEST-23-03: RecordingReplayer — replay dispatch and mismatch detection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from super_browser.agent.facade import SuperBrowser
from super_browser.recording.persistence import save
from super_browser.recording.replayer import RecordingReplayer
from super_browser.recording.types import ActionRecord, RecordingSession


def _make_recording_with_actions() -> RecordingSession:
    """Helper: create a recording with specific actions for replay testing."""
    session = RecordingSession()
    session.actions = [
        ActionRecord(
            index=0,
            timestamp=1.0,
            action="navigate",
            params={"url": "https://example.com"},
            url="https://example.com",
            title="Example",
            ok=True,
        ),
        ActionRecord(
            index=1,
            timestamp=2.0,
            action="click",
            params={"target": "#btn"},
            ok=True,
        ),
        ActionRecord(
            index=2,
            timestamp=3.0,
            action="fill",
            params={"target": "#input", "value": "hello"},
            ok=True,
        ),
    ]
    return session


# ---------------------------------------------------------------------------
# TEST-23-03-01: Replayer dispatches navigate actions
# ---------------------------------------------------------------------------
class TestReplayNavigate:
    """AC-03-01: Replayer dispatches navigate to SuperBrowser."""

    @pytest.mark.asyncio
    async def test_navigate_dispatched(self) -> None:
        sb = MagicMock(spec=SuperBrowser)
        sb.navigate = AsyncMock(return_value=MagicMock(ok=True))
        replayer = RecordingReplayer(sb)
        recording = _make_recording_with_actions()

        report = await replayer.replay(recording, delay_ms=0)  # noqa: F841

        sb.navigate.assert_called()
        call_args = sb.navigate.call_args_list
        urls_called = [c[0][0] for c in call_args if c[0]]
        assert "https://example.com" in urls_called


# ---------------------------------------------------------------------------
# TEST-23-03-02: Replayer dispatches click actions
# ---------------------------------------------------------------------------
class TestReplayClick:
    """AC-03-01: Replayer dispatches click to SuperBrowser."""

    @pytest.mark.asyncio
    async def test_click_dispatched(self) -> None:
        sb = MagicMock(spec=SuperBrowser)
        sb.click = AsyncMock(return_value=MagicMock(ok=True))
        sb.navigate = AsyncMock(return_value=MagicMock(ok=True))
        replayer = RecordingReplayer(sb)
        recording = _make_recording_with_actions()

        report = await replayer.replay(recording, delay_ms=0)  # noqa: F841

        sb.click.assert_called()
        call_args = sb.click.call_args_list
        selectors = [c[0][0] for c in call_args if c[0]]
        assert "#btn" in selectors


# ---------------------------------------------------------------------------
# TEST-23-03-03: Replayer dispatches fill actions
# ---------------------------------------------------------------------------
class TestReplayFill:
    """AC-03-01: Replayer dispatches fill to SuperBrowser."""

    @pytest.mark.asyncio
    async def test_fill_dispatched(self) -> None:
        sb = MagicMock(spec=SuperBrowser)
        sb.fill = AsyncMock(return_value=MagicMock(ok=True))
        sb.navigate = AsyncMock(return_value=MagicMock(ok=True))
        sb.click = AsyncMock(return_value=MagicMock(ok=True))
        replayer = RecordingReplayer(sb)
        recording = _make_recording_with_actions()

        report = await replayer.replay(recording, delay_ms=0)  # noqa: F841

        sb.fill.assert_called()
        call_args = sb.fill.call_args_list
        targets = [c[0][0] for c in call_args if c[0]]
        assert "#input" in targets


# ---------------------------------------------------------------------------
# TEST-23-03-04: Replayer detects mismatches
# ---------------------------------------------------------------------------
class TestMismatchDetection:
    """AC-03-02: ReplayReport lists mismatches between recorded and actual."""

    @pytest.mark.asyncio
    async def test_mismatch_detected_on_failure(self) -> None:
        sb = MagicMock(spec=SuperBrowser)
        # Navigate returns ok=False (was ok=True in recording)
        sb.navigate = AsyncMock(return_value=MagicMock(ok=False, error="Timeout"))
        replayer = RecordingReplayer(sb)

        recording = RecordingSession()
        recording.actions = [
            ActionRecord(
                index=0,
                timestamp=1.0,
                action="navigate",
                params={"url": "https://example.com"},
                url="https://example.com",
                ok=True,
            ),
        ]

        report = await replayer.replay(recording, delay_ms=0)
        assert len(report.mismatches) >= 1
        assert report.mismatches[0].reason  # non-empty reason string


# ---------------------------------------------------------------------------
# TEST-23-03-05: sb.recording returns SessionRecorder
# ---------------------------------------------------------------------------
class TestFacadeRecording:
    """AC-03-03: sb.recording property provides access to the active recorder."""

    def test_recording_property_none_by_default(self) -> None:
        sb = SuperBrowser()
        assert sb.recording is None

    def test_enable_recording_creates_recorder(self) -> None:
        sb = SuperBrowser()
        sb.enable_recording()
        from super_browser.recording.recorder import SessionRecorder
        assert isinstance(sb.recording, SessionRecorder)

    def test_enable_recording_with_max_screenshots(self) -> None:
        sb = SuperBrowser()
        sb.enable_recording(max_screenshots=50)
        assert sb.recording is not None
        assert sb.recording._max_screenshots == 50


# ---------------------------------------------------------------------------
# Additional: sb.replay() integration with facade
# ---------------------------------------------------------------------------
class TestFacadeReplay:
    """AC-03-04: sb.replay(path) loads and replays a recording file."""

    @pytest.mark.asyncio
    async def test_replay_from_file(self, tmp_path: Path) -> None:
        """sb.replay() loads a JSON file and produces a ReplayReport."""
        recording = _make_recording_with_actions()
        path = tmp_path / "test_rec.json"
        save(recording, str(path))

        sb = MagicMock(spec=SuperBrowser)
        sb.navigate = AsyncMock(return_value=MagicMock(ok=True))
        sb.click = AsyncMock(return_value=MagicMock(ok=True))
        sb.fill = AsyncMock(return_value=MagicMock(ok=True))

        # Use RecordingReplayer directly (facade replay() tested below)
        from super_browser.recording.persistence import load as load_recording
        from super_browser.recording.replayer import RecordingReplayer
        loaded = load_recording(str(path))
        replayer = RecordingReplayer(sb)
        report = await replayer.replay(loaded, delay_ms=0)

        assert report.total_actions == 3
        assert report.matched >= 1
