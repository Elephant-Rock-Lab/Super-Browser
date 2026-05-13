"""Tests for CDPBridge (mocked unit tests)."""

import asyncio
from unittest.mock import AsyncMock

import pytest
from super_browser.browser import SessionConfig
from super_browser.browser.cdp import CDPBridge, CDPResult


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.send = AsyncMock(return_value={"result": "ok"})
    session.id = "test-session-123"
    return session


@pytest.fixture
def bridge(mock_session):
    return CDPBridge(mock_session, SessionConfig())


class TestSend:
    def test_returns_cdp_result(self, bridge):
        async def _test():
            r = await bridge.send("Runtime.evaluate", {"expression": "1+1"})
            assert isinstance(r, CDPResult)
            assert r.ok is True
            assert r.method == "Runtime.evaluate"
            assert r.duration_ms >= 0
        asyncio.run(_test())

    def test_error_on_failure(self, bridge, mock_session):
        mock_session.send = AsyncMock(side_effect=RuntimeError("boom"))
        async def _test():
            r = await bridge.send("Bad.method")
            assert r.ok is False
            assert r.error == "boom"
        asyncio.run(_test())


class TestCompositorClick:
    def test_dispatches_two_events(self, bridge, mock_session):
        async def _test():
            await bridge.compositor_click(100.0, 200.0)
            assert mock_session.send.call_count == 2
            calls = mock_session.send.call_args_list
            first_method = calls[0][0][0]
            assert first_method == "Input.dispatchMouseEvent"
            first_params = calls[0][0][1]
            assert first_params["type"] == "mousePressed"
            assert first_params["x"] == 100.0
            second_params = calls[1][0][1]
            assert second_params["type"] == "mouseReleased"
        asyncio.run(_test())


class TestCompositorKeypress:
    def test_dispatches_keydown_keyup(self, bridge, mock_session):
        async def _test():
            await bridge.compositor_key_press("Enter")
            assert mock_session.send.call_count == 2
        asyncio.run(_test())


class TestEvaluate:
    def test_wraps_result(self, bridge):
        async def _test():
            r = await bridge.evaluate("1+1")
            assert r.ok is True
        asyncio.run(_test())


class TestEventBuffer:
    def test_drain_returns_buffer(self, bridge):
        bridge._events.append({"method": "Page.loadEventFired"})
        bridge._events.append({"method": "Page.domContentEventFired"})
        events = bridge.drain_events()
        assert len(events) == 2
        assert len(bridge._events) == 0

    def test_buffer_bounded(self, bridge):
        for i in range(600):
            bridge._events.append({"i": i})
        assert len(bridge._events) == 500  # maxlen from config


class TestSessionId:
    def test_returns_id(self, bridge):
        assert bridge.session_id == "test-session-123"
