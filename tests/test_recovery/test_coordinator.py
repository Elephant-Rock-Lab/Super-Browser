"""Tests for RecoveryCoordinator — full pipeline orchestration."""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from super_browser.recovery.coordinator import RecoveryCoordinator
from super_browser.recovery.types import (
    ActionRecord,
    RecoveryStrategy,
    WatchdogEvent,
)


def _make_controller():
    controller = MagicMock()
    page = MagicMock()
    page.url = "https://example.com"
    page.title = AsyncMock(return_value="Test")
    page.cdp = MagicMock()
    page.cdp.evaluate = AsyncMock()
    controller._page = page
    controller._cdp = page.cdp
    controller.capture_ax_snapshot = AsyncMock()
    return controller


def _make_session():
    session = MagicMock()
    session.stop = AsyncMock()
    session.start = AsyncMock()
    new_page = MagicMock()
    new_page.url = "https://example.com"
    new_page.goto = AsyncMock()
    new_page.cdp = MagicMock()
    session.new_page = AsyncMock(return_value=new_page)
    return session


class TestCoordinatorLifecycle:
    def test_start_and_stop(self):
        async def _test():
            coord = RecoveryCoordinator(_make_session(), _make_controller())
            await coord.start()
            assert coord.event_bus is not None
            await coord.stop()
        asyncio.run(_test())

    def test_properties(self):
        coord = RecoveryCoordinator(_make_session(), _make_controller())
        assert coord.event_bus is not None
        assert coord.checkpoint_manager is not None
        assert coord.reflection is not None


class TestExecuteWithRecovery:
    def test_success_path(self):
        async def _test():
            coord = RecoveryCoordinator(_make_session(), _make_controller())
            await coord.start()

            async def action():
                r = MagicMock()
                r.ok = True
                return r

            result = await coord.execute_with_recovery(
                action, {"action_type": "click", "target": "#btn"},
            )
            assert result.ok
            await coord.stop()
        asyncio.run(_test())

    def test_failure_triggers_recovery(self):
        async def _test():
            coord = RecoveryCoordinator(
                _make_session(), _make_controller(), max_recovery_attempts=1,
            )
            await coord.start()
            call_count = 0

            async def action():
                nonlocal call_count
                call_count += 1
                r = MagicMock()
                r.ok = call_count > 2
                return r

            result = await coord.execute_with_recovery(
                action, {"action_type": "click", "target": "#btn"},
            )
            history = coord.get_recovery_history()
            assert len(history) >= 1
            await coord.stop()
        asyncio.run(_test())

    def test_exception_triggers_recovery(self):
        async def _test():
            coord = RecoveryCoordinator(
                _make_session(), _make_controller(), max_recovery_attempts=1,
            )
            await coord.start()

            async def fail_action():
                raise RuntimeError("stale element reference")

            try:
                await coord.execute_with_recovery(
                    fail_action, {"action_type": "click", "target": "#btn"},
                )
                assert False, "Should have raised"
            except RuntimeError:
                pass

            history = coord.get_recovery_history()
            assert len(history) >= 1
            await coord.stop()
        asyncio.run(_test())


class TestRecoveryHistory:
    def test_empty_initially(self):
        coord = RecoveryCoordinator(_make_session(), _make_controller())
        assert coord.get_recovery_history() == []


class TestEventEmission:
    def test_events_emitted_on_recovery(self):
        async def _test():
            coord = RecoveryCoordinator(
                _make_session(), _make_controller(), max_recovery_attempts=1,
            )
            await coord.start()
            events = []
            coord.event_bus.subscribe(
                [WatchdogEvent.RECOVERY_STARTED, WatchdogEvent.RECOVERY_COMPLETED],
                lambda e: events.append(e.event_type),
            )

            async def fail_action():
                r = MagicMock()
                r.ok = False
                return r

            await coord.execute_with_recovery(
                fail_action, {"action_type": "click", "target": "#btn"},
            )
            assert len(events) > 0
            await coord.stop()
        asyncio.run(_test())


class TestReflectionRecording:
    def test_record_reflection_step(self):
        coord = RecoveryCoordinator(_make_session(), _make_controller())
        coord.record_reflection_step("click #btn", "clicked", "page with button")
        assert len(coord.reflection._steps) == 1
