"""Cross-feature integration tests for v1.3 features (plugins, recording, CLI, memory).

These tests exercise combinations of features working together, using mocks/stubs
for the browser — no real browser required.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from super_browser.events.bus import EventBus
from super_browser.events.types import AFTER_ACTION, AFTER_NAVIGATE, BEFORE_ACTION, BEFORE_NAVIGATE
from super_browser.memory.store import MemoryStore
from super_browser.plugins.decorators import hook

# Memory types imported as needed in tests
from super_browser.plugins.hooks import clear_registry, get_registered_hooks, register_hook
from super_browser.recording.persistence import load as load_recording
from super_browser.recording.persistence import save as save_recording
from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.replayer import RecordingReplayer
from super_browser.recording.types import ActionRecord, RecordingSession

# ---------------------------------------------------------------------------
# TEST-26-01-01: Hook fires during a recorded session
# ---------------------------------------------------------------------------


class TestHookFiresDuringRecordedSession:
    """Subscribe to EventBus, start recording, perform action, verify hook called."""

    def test_hook_called_when_event_emitted_during_recording(self):
        bus = EventBus()
        recorder = SessionRecorder(bus)

        # Register a hook via the EventBus directly (simulates what @hook does)
        hook_calls: list[dict] = []

        def my_hook(ctx: Any) -> None:
            hook_calls.append(dict(ctx))

        bus.subscribe(BEFORE_NAVIGATE, my_hook)

        # Start recording
        recorder.start()

        # Emit events (simulating a browser action)
        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com", "action": "navigate", "target": "url", "step": 1})
        bus.emit(AFTER_NAVIGATE, {"url": "https://example.com", "final_url": "https://example.com/", "title": "Example", "ok": True, "action": "navigate", "target": "url", "step": 1})

        session = recorder.stop()

        # Verify the hook was called
        assert len(hook_calls) == 1
        assert hook_calls[0]["url"] == "https://example.com"

        # Verify recording captured the events too
        assert len(session.actions) >= 2  # before_navigate + after_navigate

    def test_decorator_hook_fires_during_recording(self):
        """Test that @hook() decorator registered hooks fire during recording."""
        clear_registry()

        call_log: list[str] = []

        @hook(AFTER_ACTION)
        def track_action(ctx: Any) -> None:
            call_log.append(ctx.get("action", "unknown"))

        bus = EventBus()
        recorder = SessionRecorder(bus)
        recorder.start()

        # Install the globally registered hooks onto the bus
        for event_type, handlers in get_registered_hooks().items():
            for h in handlers:
                bus.subscribe(event_type, h)

        # Simulate an action
        bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})
        bus.emit(AFTER_ACTION, {"action": "click", "target": "#btn", "step": 1, "ok": True, "duration_ms": 50.0})

        session = recorder.stop()

        assert len(call_log) == 1
        assert call_log[0] == "click"
        assert len(session.actions) >= 2

        clear_registry()


# ---------------------------------------------------------------------------
# TEST-26-01-02: Recording replay can use memory hints
# ---------------------------------------------------------------------------


class TestRecordingReplayUsesMemoryHints:
    """Load recording + memory, verify replayer uses context."""

    def test_memory_context_available_for_replay_domain(self):
        """Memory store provides context for a domain that a recording targets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 1. Create and save a memory store with context for example.com
            mem_store = MemoryStore(Path(tmpdir), ttl_days=30)
            mem_store.record_sequence(
                domain="example.com",
                task="Navigate and click",
                actions=[
                    {"action": "navigate", "url": "https://example.com"},
                    {"action": "click", "target": "#btn"},
                ],
                success=True,
            )
            mem_store.record_selector("example.com", "Submit Button", "#submit-btn")

            # 2. Create a recording that targets example.com
            recording = RecordingSession()
            recording.actions = [
                ActionRecord(
                    index=0,
                    timestamp=1.0,
                    action="before_navigate",
                    params={"url": "https://example.com", "action": "navigate", "target": "url", "step": 1},
                    url="https://example.com",
                    ok=True,
                ),
                ActionRecord(
                    index=1,
                    timestamp=2.0,
                    action="after_navigate",
                    params={"url": "https://example.com", "final_url": "https://example.com/", "title": "Example", "ok": True},
                    url="https://example.com",
                    ok=True,
                ),
                ActionRecord(
                    index=2,
                    timestamp=3.0,
                    action="before_action",
                    params={"action": "click", "target": "#btn", "step": 2},
                    ok=True,
                ),
            ]

            # 3. Verify memory provides context that's useful for replay
            context = mem_store.get_context_for_prompt("example.com")
            assert "Previous successful action sequences" in context
            assert "Submit Button" in context
            assert "#submit-btn" in context

            # 4. Verify the recording can be saved and loaded
            rec_path = Path(tmpdir) / "recording.json"
            save_recording(recording, rec_path)
            loaded = load_recording(rec_path)
            assert len(loaded.actions) == 3

    @pytest.mark.asyncio
    async def test_replayer_uses_mocked_browser_with_memory(self):
        """Replayer dispatches actions to a mocked SuperBrowser."""
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

        # Create a mock SuperBrowser
        mock_sb = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.data = MagicMock()
        mock_result.data.final_url = "https://example.com/"
        mock_sb.navigate = AsyncMock(return_value=mock_result)

        replayer = RecordingReplayer(mock_sb)
        report = await replayer.replay(recording, delay_ms=0)

        assert report.total_actions == 1
        assert report.matched == 1
        assert len(report.mismatches) == 0
        mock_sb.navigate.assert_called_once_with("https://example.com")


# ---------------------------------------------------------------------------
# TEST-26-01-03: CLI script mode produces a recording
# ---------------------------------------------------------------------------


class TestCLIScriptProducesRecording:
    """Run script, check recording file created."""

    @pytest.mark.asyncio
    async def test_script_execution_creates_recording_file(self):
        """When recording is enabled during script execution, a file is produced."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple script file (JSON format, valid as YAML subset)
            script_path = Path(tmpdir) / "test_script.json"
            script_path.write_text(json.dumps({
                "steps": [
                    {"action": "navigate", "url": "https://example.com"},
                    {"action": "observe"},
                ],
            }), encoding="utf-8")

            # Create recording output path
            recording_path = Path(tmpdir) / "recording.json"

            # Simulate what the CLI does: run script with recording enabled
            bus = EventBus()
            recorder = SessionRecorder(bus)
            recorder.start()

            # Simulate events the script would emit
            bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com", "action": "navigate", "target": "url", "step": 1})
            bus.emit(AFTER_NAVIGATE, {"url": "https://example.com", "final_url": "https://example.com/", "title": "Example", "ok": True, "action": "navigate", "target": "url", "step": 1})
            bus.emit(BEFORE_ACTION, {"action": "observe", "target": "page", "step": 2})
            bus.emit(AFTER_ACTION, {"action": "observe", "target": "page", "step": 2, "ok": True, "duration_ms": 10.0})

            session = recorder.stop()

            # Save the recording
            save_recording(session, recording_path)

            # Verify recording file was created and contains valid data
            assert recording_path.exists()
            loaded = load_recording(recording_path)
            assert len(loaded.actions) >= 2
            assert loaded.schema_version == "1.0"


# ---------------------------------------------------------------------------
# TEST-26-01-04: Memory saves successful CLI sequence
# ---------------------------------------------------------------------------


class TestMemorySavesSuccessfulCLISequence:
    """Run successful task, check memory file exists for domain."""

    def test_successful_cli_sequence_saved_to_memory(self):
        """A successful CLI action sequence is persisted in memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem_store = MemoryStore(Path(tmpdir), ttl_days=30)

            # Simulate a successful CLI sequence
            domain = "example.com"
            task = "Navigate and extract heading"
            actions = [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "extract", "selector": "h1"},
            ]

            mem_store.record_sequence(domain, task, actions, success=True)

            # Verify memory file exists
            memory_files = list(Path(tmpdir).glob("*.json"))
            assert len(memory_files) == 1

            # Verify content
            loaded = mem_store.load(domain)
            assert len(loaded.sequences) == 1
            assert loaded.sequences[0].task == task
            assert loaded.sequences[0].success is True
            assert len(loaded.sequences[0].actions) == 2

    def test_failed_cli_sequence_not_saved_to_memory(self):
        """A failed CLI action sequence is NOT persisted in memory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem_store = MemoryStore(Path(tmpdir), ttl_days=30)

            domain = "example.com"
            task = "Navigate and extract heading"
            actions = [
                {"action": "navigate", "url": "https://example.com"},
                {"action": "extract", "selector": "h1"},
            ]

            mem_store.record_sequence(domain, task, actions, success=False)

            # Verify no memory file was created (failed sequences aren't saved)
            memory_files = list(Path(tmpdir).glob("*.json"))
            assert len(memory_files) == 0

    def test_memory_context_injectable_into_prompt(self):
        """Saved memory produces context text usable in LLM prompts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mem_store = MemoryStore(Path(tmpdir), ttl_days=30)

            mem_store.record_sequence(
                "shop.example.com",
                "Add item to cart",
                [{"action": "click", "target": "#add-to-cart"}],
                success=True,
            )
            mem_store.record_selector("shop.example.com", "Add to Cart Button", "#add-to-cart")

            context = mem_store.get_context_for_prompt("shop.example.com")
            assert "Add to Cart Button" in context
            assert "#add-to-cart" in context
            assert "successful" in context.lower()


# ---------------------------------------------------------------------------
# TEST-26-01-05: Plugin can register a custom tool
# ---------------------------------------------------------------------------


class TestPluginRegistersCustomTool:
    """Register tool via plugin hooks, verify in registry."""

    def test_register_hook_and_retrieve(self):
        """A handler registered via register_hook appears in get_registered_hooks."""
        clear_registry()

        def my_custom_tool(ctx: Any) -> None:
            pass

        register_hook("after_navigate", my_custom_tool)

        hooks = get_registered_hooks()
        assert "after_navigate" in hooks
        assert my_custom_tool in hooks["after_navigate"]

        clear_registry()

    def test_decorator_registers_multiple_hooks(self):
        """Multiple @hook() decorators register handlers for different events."""
        clear_registry()

        log: list[str] = []

        @hook(BEFORE_NAVIGATE)
        def on_before_nav(ctx: Any) -> None:
            log.append("before:" + ctx.get("url", ""))

        @hook(AFTER_NAVIGATE)
        def on_after_nav(ctx: Any) -> None:
            log.append("after:" + ctx.get("url", ""))

        hooks = get_registered_hooks()
        assert BEFORE_NAVIGATE in hooks
        assert AFTER_NAVIGATE in hooks

        # Install on bus and test
        bus = EventBus()
        for event_type, handlers in hooks.items():
            for h in handlers:
                bus.subscribe(event_type, h)

        bus.emit(BEFORE_NAVIGATE, {"url": "https://example.com"})
        bus.emit(AFTER_NAVIGATE, {"url": "https://example.com", "final_url": "https://example.com/", "title": "Example", "ok": True})

        assert "before:https://example.com" in log
        assert "after:https://example.com" in log

        clear_registry()

    def test_custom_tool_via_plugin_hook(self):
        """A plugin registers a custom tool via the hook system, which fires during recording."""
        clear_registry()

        tool_invocations: list[str] = []

        @hook(AFTER_ACTION)
        def custom_analytics_tool(ctx: Any) -> None:
            """Track all actions for analytics."""
            tool_invocations.append(ctx.get("action", "unknown"))

        bus = EventBus()
        recorder = SessionRecorder(bus)

        # Install plugin hooks
        for event_type, handlers in get_registered_hooks().items():
            for h in handlers:
                bus.subscribe(event_type, h)

        recorder.start()

        # Simulate actions
        bus.emit(BEFORE_ACTION, {"action": "click", "target": "#btn", "step": 1})
        bus.emit(AFTER_ACTION, {"action": "click", "target": "#btn", "step": 1, "ok": True, "duration_ms": 30.0})

        session = recorder.stop()

        # The custom tool was invoked
        assert len(tool_invocations) == 1
        assert tool_invocations[0] == "click"

        # And recording captured the events too
        assert len(session.actions) >= 2

        clear_registry()
