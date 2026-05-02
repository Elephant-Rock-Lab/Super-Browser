"""Tests for BrowserSession (mocked unit tests)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.browser import BrowserSession, SessionConfig, SessionMode


class TestBrowserSession:
    def test_context_manager(self):
        async def _test():
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.version = "1.0"
            mock_browser._impl_obj = MagicMock()
            mock_browser._impl_obj._browser_process = MagicMock()
            mock_browser._impl_obj._browser_process.pid = 1234
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_cdp = AsyncMock()
            mock_cdp.on = MagicMock()
            mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

            with patch(
                "super_browser.browser.session.async_playwright",
                return_value=mock_pw,
            ):
                mock_pw.start = AsyncMock(return_value=mock_pw)
                async with BrowserSession(SessionConfig(headless=True)) as session:
                    state = session.state()
                    assert state.connected is True

                assert session.state().connected is False
        asyncio.run(_test())

    def test_new_page_returns_page_handle(self):
        async def _test():
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.version = "1.0"
            mock_browser._impl_obj = MagicMock()
            mock_browser._impl_obj._browser_process = MagicMock()
            mock_browser._impl_obj._browser_process.pid = 1234
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_cdp = AsyncMock()
            mock_cdp.on = MagicMock()
            mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

            with patch(
                "super_browser.browser.session.async_playwright",
                return_value=mock_pw,
            ):
                mock_pw.start = AsyncMock(return_value=mock_pw)
                session = BrowserSession(SessionConfig(headless=True))
                await session.start()
                ph = await session.new_page()
                assert ph is not None
                assert ph.cdp is not None
                await session.stop()
        asyncio.run(_test())

    def test_state_snapshot(self):
        async def _test():
            session = BrowserSession()
            state = session.state()
            assert state.connected is False
            assert state.browser_pid is None
        asyncio.run(_test())


class TestBrowserState:
    def test_uptime_zero_when_not_connected(self):
        from super_browser.browser.session import BrowserState
        state = BrowserState()
        assert state.uptime() == 0.0
