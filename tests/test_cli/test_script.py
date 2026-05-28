"""Tests for BATCH-24/TASK-02 — Script Mode & Replay.

TEST-24-02-01: YAML script executes all steps
TEST-24-02-02: Script stops on error with stop_on_error flag
TEST-24-02-03: replay command loads recording
TEST-24-02-04: act command calls sb.act()
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser import SuperBrowser
from super_browser.cli.script import (
    _execute_step,
    run_act,
    run_replay,
    run_script,
)
from super_browser.results import ActionResult

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(**kwargs: object) -> ActionResult:
    return ActionResult(ok=True, **kwargs)


def _fail(error: Exception) -> ActionResult:
    return ActionResult(ok=False, error=error)


def _write_yaml(path: Path, data: dict) -> None:
    """Write a dict as YAML-like JSON (valid both YAML and JSON)."""
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# TEST-24-02-01: YAML script executes all steps
# ---------------------------------------------------------------------------


class TestScriptExecution:
    """TEST-24-02-01: YAML script mode executes all steps in order."""

    @pytest.mark.asyncio
    async def test_script_executes_all_steps(self, tmp_path: Path) -> None:
        script = {
            "steps": [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "click", "selector": "#btn"},
                {"action": "fill", "selector": "#email", "value": "test@example.com"},
            ],
            "stop_on_error": True,
        }
        script_file = tmp_path / "tasks.yaml"
        _write_yaml(script_file, script)

        with patch("super_browser.cli.script.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
            mock_sb.click = AsyncMock(return_value=_ok())
            mock_sb.fill = AsyncMock(return_value=_ok())
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            MockSB.return_value = mock_sb

            results = await run_script(str(script_file))

        assert len(results) == 3
        assert all(r["ok"] for r in results)
        assert results[0]["action"] == "navigate"
        assert results[1]["action"] == "click"
        assert results[2]["action"] == "fill"

        # Verify order
        mock_sb.navigate.assert_awaited_once_with("https://example.com")
        mock_sb.click.assert_awaited_once_with("#btn")
        mock_sb.fill.assert_awaited_once_with("#email", "test@example.com")

    @pytest.mark.asyncio
    async def test_script_writes_output_file(self, tmp_path: Path) -> None:
        script = {
            "steps": [
                {"action": "navigate", "url": "https://example.com"},
            ],
            "stop_on_error": True,
        }
        script_file = tmp_path / "tasks.yaml"
        output_file = tmp_path / "results.json"
        _write_yaml(script_file, script)

        with patch("super_browser.cli.script.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            MockSB.return_value = mock_sb

            results = await run_script(str(script_file), output_path=str(output_file))  # noqa: F841

        assert output_file.exists()
        written = json.loads(output_file.read_text())
        assert len(written) == 1


# ---------------------------------------------------------------------------
# TEST-24-02-02: Script stops on error with stop_on_error flag
# ---------------------------------------------------------------------------


class TestScriptStopOnError:
    """TEST-24-02-02: Script stops on error when stop_on_error is true."""

    @pytest.mark.asyncio
    async def test_stops_on_error(self, tmp_path: Path) -> None:
        script = {
            "steps": [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "click", "selector": "#nonexistent"},
                {"action": "fill", "selector": "#email", "value": "test@example.com"},
            ],
            "stop_on_error": True,
        }
        script_file = tmp_path / "tasks.yaml"
        _write_yaml(script_file, script)

        with patch("super_browser.cli.script.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
            # Second step fails
            mock_sb.click = AsyncMock(
                return_value=_fail(RuntimeError("Element not found"))
            )
            mock_sb.fill = AsyncMock(return_value=_ok())
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            MockSB.return_value = mock_sb

            results = await run_script(str(script_file))

        # Should stop after the failed second step
        assert len(results) == 2
        assert results[0]["ok"] is True
        assert results[1]["ok"] is False

        # Third step should NOT have been executed
        mock_sb.fill.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_continues_on_error_when_flag_false(self, tmp_path: Path) -> None:
        script = {
            "steps": [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "click", "selector": "#nonexistent"},
                {"action": "fill", "selector": "#email", "value": "test@example.com"},
            ],
            "stop_on_error": False,
        }
        script_file = tmp_path / "tasks.yaml"
        _write_yaml(script_file, script)

        with patch("super_browser.cli.script.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
            mock_sb.click = AsyncMock(
                return_value=_fail(RuntimeError("Element not found"))
            )
            mock_sb.fill = AsyncMock(return_value=_ok())
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            MockSB.return_value = mock_sb

            results = await run_script(str(script_file))

        # All 3 steps should be executed
        assert len(results) == 3
        assert results[0]["ok"] is True
        assert results[1]["ok"] is False
        assert results[2]["ok"] is True

        # All methods called
        mock_sb.fill.assert_awaited_once()


# ---------------------------------------------------------------------------
# TEST-24-02-03: replay command loads recording
# ---------------------------------------------------------------------------


class TestReplayCommand:
    """TEST-24-02-03: replay command replays a recording file."""

    @pytest.mark.asyncio
    async def test_replay_loads_and_replays_recording(self, tmp_path: Path) -> None:
        recording = {
            "session_id": "test-session",
            "schema_version": "1.0",
            "actions": [
                {
                    "index": 0,
                    "timestamp": 1000.0,
                    "action": "navigate",
                    "params": {"url": "https://example.com"},
                    "url": "https://example.com",
                    "ok": True,
                },
            ],
        }
        recording_file = tmp_path / "recording.json"
        recording_file.write_text(json.dumps(recording), encoding="utf-8")

        with patch("super_browser.cli.script.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()

            # Mock replay to return a report
            mock_report = MagicMock()
            mock_report.to_dict.return_value = {
                "total_actions": 1,
                "matched": 1,
                "mismatches": [],
                "duration_ms": 50.0,
            }
            mock_sb.replay = AsyncMock(
                return_value=_ok(data=mock_report)
            )
            MockSB.return_value = mock_sb

            result = await run_replay(str(recording_file), delay_ms=50)

        # Verify replay was called with the correct path
        mock_sb.replay.assert_awaited_once()
        call_args = mock_sb.replay.call_args
        assert call_args[0][0] == str(recording_file)
        assert call_args[1]["delay_ms"] == 50

        assert result["total_actions"] == 1
        assert result["matched"] == 1


# ---------------------------------------------------------------------------
# TEST-24-02-04: act command calls sb.act()
# ---------------------------------------------------------------------------


class TestActCommand:
    """TEST-24-02-04: act command runs a one-shot agent task."""

    @pytest.mark.asyncio
    async def test_act_calls_sb_act_with_instruction(self) -> None:
        with patch("super_browser.cli.script.SuperBrowser") as MockSB, \
             patch("super_browser.create_llm") as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            mock_sb.act = AsyncMock(
                return_value=_ok(data={"steps": 3})
            )
            MockSB.return_value = mock_sb

            result = await run_act("click the submit button", max_steps=10)

        assert result.ok is True
        mock_sb.act.assert_awaited_once_with("click the submit button", max_steps=10)

    @pytest.mark.asyncio
    async def test_act_with_url_navigates_first(self) -> None:
        with patch("super_browser.cli.script.SuperBrowser") as MockSB, \
             patch("super_browser.create_llm") as mock_create_llm:
            mock_llm = MagicMock()
            mock_create_llm.return_value = mock_llm

            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.start = AsyncMock()
            mock_sb.stop = AsyncMock()
            mock_sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
            mock_sb.act = AsyncMock(return_value=_ok(data={"steps": 1}))
            MockSB.return_value = mock_sb

            result = await run_act("extract text", url="https://example.com", max_steps=5)

        assert result.ok is True
        mock_sb.navigate.assert_awaited_once_with("https://example.com")
        mock_sb.act.assert_awaited_once_with("extract text", max_steps=5)

    @pytest.mark.asyncio
    async def test_act_handles_missing_llm(self) -> None:
        with patch("super_browser.create_llm") as mock_create_llm:
            mock_create_llm.side_effect = RuntimeError("No API key")

            result = await run_act("do something")

        assert result.ok is False


# ---------------------------------------------------------------------------
# Step executor unit tests
# ---------------------------------------------------------------------------


class TestExecuteStep:
    """Unit tests for individual step execution."""

    @pytest.mark.asyncio
    async def test_navigate_step(self) -> None:
        sb = AsyncMock(spec=SuperBrowser)
        sb.navigate = AsyncMock(return_value=_ok(data=MagicMock()))
        result = await _execute_step(sb, {"action": "navigate", "url": "https://example.com"})
        assert result.ok is True
        sb.navigate.assert_awaited_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_observe_step(self) -> None:
        sb = AsyncMock(spec=SuperBrowser)
        sb.observe = AsyncMock(return_value=_ok(data={"url": "https://example.com"}))
        result = await _execute_step(sb, {"action": "observe"})
        assert result.ok is True
        sb.observe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unknown_action_step(self) -> None:
        sb = AsyncMock(spec=SuperBrowser)
        result = await _execute_step(sb, {"action": "nonexistent"})
        assert result.ok is False
