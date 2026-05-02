"""Tests for SessionRecovery — 5 recovery strategies."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.interaction.types import AXNode, AXSnapshot
from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.session_recovery import SessionRecovery
from super_browser.recovery.types import (
    ActionRecord,
    ClassifiedError,
    ErrorType,
    RecoveryHint,
    RecoveryStrategy,
    WatchdogEvent,
)


def _make_hint(strategy: RecoveryStrategy = RecoveryStrategy.RETRY) -> RecoveryHint:
    return RecoveryHint(strategy=strategy, retryable=True, max_attempts=3)


def _make_classified(strategy: RecoveryStrategy = RecoveryStrategy.RETRY) -> ClassifiedError:
    return ClassifiedError(
        error_type=ErrorType.TIMEOUT,
        hint=_make_hint(strategy),
    )


def _make_controller(snap_nodes=None):
    controller = MagicMock()
    if snap_nodes is None:
        snap_nodes = {
            "e0": AXNode(ref="e0", role="button", name="Submit"),
            "e1": AXNode(ref="e1", role="link", name="Next"),
        }
    snap = AXSnapshot(url="https://example.com", title="Test", nodes=snap_nodes)
    controller.capture_ax_snapshot = AsyncMock(return_value=snap)
    page = MagicMock()
    page.url = "https://example.com"
    page.goto = AsyncMock()
    page.cdp = MagicMock()
    page.cdp.send = AsyncMock()
    controller._page = page
    controller._cdp = page.cdp
    return controller


def _make_session():
    session = MagicMock()
    session.stop = AsyncMock()
    session.start = AsyncMock()
    new_page = MagicMock()
    new_page.url = "https://example.com"
    new_page.goto = AsyncMock()
    new_page.cdp = MagicMock()
    new_page.cdp.send = AsyncMock()
    session.new_page = AsyncMock(return_value=new_page)
    return session


class TestSessionRecovery:
    def test_record_and_get_last(self):
        bus = WatchdogEventBus()
        sr = SessionRecovery(_make_session(), _make_controller(), bus)
        sr.record_action(ActionRecord(
            action_type="click", target="#btn", url="https://example.com",
            succeeded=True,
        ))
        last = sr.get_last_successful_action()
        assert last is not None
        assert last.target == "#btn"

    def test_get_last_none_when_empty(self):
        bus = WatchdogEventBus()
        sr = SessionRecovery(_make_session(), _make_controller(), bus)
        assert sr.get_last_successful_action() is None

    def test_get_last_skips_failures(self):
        bus = WatchdogEventBus()
        sr = SessionRecovery(_make_session(), _make_controller(), bus)
        sr.record_action(ActionRecord(action_type="click", target="#a", succeeded=False))
        sr.record_action(ActionRecord(action_type="click", target="#b", succeeded=True))
        sr.record_action(ActionRecord(action_type="click", target="#c", succeeded=False))
        last = sr.get_last_successful_action()
        assert last.target == "#b"


class TestRecoverLoop:
    def test_retry_success(self):
        async def _test():
            bus = WatchdogEventBus()
            controller = _make_controller()
            call_count = 0

            async def action_fn():
                nonlocal call_count
                call_count += 1
                r = MagicMock()
                r.ok = call_count > 1
                return r

            sr = SessionRecovery(_make_session(), controller, bus)
            error = _make_classified(RecoveryStrategy.RETRY)
            ctx = {"action_fn": action_fn, "target": "#btn"}
            event = await sr.recover(error, ctx)
            assert event.outcome == "success"
        asyncio.run(_test())

    def test_max_attempts_exhausted(self):
        async def _test():
            bus = WatchdogEventBus()
            controller = _make_controller()
            controller._cdp.send = AsyncMock(side_effect=RuntimeError("no session"))

            # Make session fail on respawn too
            session = MagicMock()
            session.stop = AsyncMock()
            session.start = AsyncMock(side_effect=RuntimeError("cannot start"))
            session.new_page = AsyncMock(side_effect=RuntimeError("no page"))

            async def fail_fn():
                r = MagicMock()
                r.ok = False
                return r

            sr = SessionRecovery(session, controller, bus, max_attempts=3)
            error = _make_classified(RecoveryStrategy.RETRY)
            ctx = {"action_fn": fail_fn, "target": "#btn"}
            event = await sr.recover(error, ctx)
            assert event.outcome == "escalated"
            assert event.strategy == RecoveryStrategy.ABORT
        asyncio.run(_test())


class TestHandleStaleElement:
    def test_finds_by_role(self):
        async def _test():
            bus = WatchdogEventBus()
            sr = SessionRecovery(_make_session(), _make_controller(), bus)
            ctx = {"element_role": "button", "element_name": "Submit"}
            result = await sr.handle_stale_element(ctx)
            assert result is True
        asyncio.run(_test())

    def test_no_match(self):
        async def _test():
            bus = WatchdogEventBus()
            nodes = {"e0": AXNode(ref="e0", role="heading", name="Title")}
            sr = SessionRecovery(_make_session(), _make_controller(nodes), bus)
            ctx = {"element_role": "button", "element_name": "Missing"}
            result = await sr.handle_stale_element(ctx)
            assert result is False
        asyncio.run(_test())


class TestHandleSelectorNotFound:
    def test_finds_similar(self):
        async def _test():
            bus = WatchdogEventBus()
            sr = SessionRecovery(_make_session(), _make_controller(), bus)
            ctx = {"target": "Submit"}
            result = await sr.handle_selector_not_found(ctx)
            assert result is True
        asyncio.run(_test())


class TestHandleBrowserCrash:
    def test_respawn(self):
        async def _test():
            bus = WatchdogEventBus()
            session = _make_session()
            controller = _make_controller()
            sr = SessionRecovery(session, controller, bus)
            sr.record_action(ActionRecord(
                action_type="navigate", target="", url="https://example.com", succeeded=True,
            ))
            ctx = {"target": "#btn"}
            result = await sr.handle_browser_crash(ctx)
            assert result is True
            session.stop.assert_called_once()
            session.start.assert_called_once()
        asyncio.run(_test())


class TestHandleCdpSessionStale:
    def test_reattach(self):
        async def _test():
            bus = WatchdogEventBus()
            controller = _make_controller()
            targets_result = MagicMock()
            targets_result.ok = True
            targets_result.data = {"targetInfos": [{"targetId": "abc123", "type": "page"}]}
            attach_result = MagicMock()
            attach_result.ok = True
            controller._cdp.send = AsyncMock(side_effect=[targets_result, attach_result])
            sr = SessionRecovery(_make_session(), controller, bus)
            ctx = {}
            result = await sr.handle_cdp_session_stale(ctx)
            assert result is True
        asyncio.run(_test())


class TestEventEmission:
    def test_recovery_events_emitted(self):
        async def _test():
            bus = WatchdogEventBus()
            events = []
            bus.subscribe(
                [WatchdogEvent.RECOVERY_STARTED, WatchdogEvent.RECOVERY_COMPLETED,
                 WatchdogEvent.RECOVERY_FAILED],
                lambda e: events.append(e.event_type),
            )
            controller = _make_controller()

            async def succeed():
                r = MagicMock()
                r.ok = True
                return r

            sr = SessionRecovery(_make_session(), controller, bus)
            error = _make_classified(RecoveryStrategy.RETRY)
            await sr.recover(error, {"action_fn": succeed})
            assert WatchdogEvent.RECOVERY_STARTED in events
            assert WatchdogEvent.RECOVERY_COMPLETED in events
        asyncio.run(_test())
