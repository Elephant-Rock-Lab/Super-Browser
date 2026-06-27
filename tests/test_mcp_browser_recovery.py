"""Tests for MCP browser auto-recovery.

When the browser page/context dies (TargetClosedError), the MCPBrowserRuntime
should detect the stale handle, clean it up, and lazily relaunch on the next
tool call instead of returning a dead handle forever.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


def _make_fake_sb(*, page_alive=True):
    """Build a mock SuperBrowser with a page whose is_alive state is controllable."""
    fake_page = MagicMock()
    fake_page.url = "https://example.com"

    # PageHandle exposes is_alive; simulate dead page.
    page_handle = MagicMock()
    page_handle.url = "https://example.com"
    page_handle.is_alive = page_alive

    sb = MagicMock()
    sb._page = page_handle
    # SuperBrowser.is_alive delegates to page_handle.is_alive — set it
    # explicitly so _is_alive() sees the right value (MagicMock auto-creates
    # attributes as truthy MagicMock objects, masking our intent).
    sb.is_alive = page_alive
    sb.start = AsyncMock()
    sb.stop = AsyncMock()
    return sb


class TestGetBrowserRecovery:
    """MCPBrowserRuntime.get_browser() should recover from dead browser state."""

    @pytest.mark.asyncio
    async def test_lazy_start_when_none(self):
        """First call lazily starts the browser."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        fake_sb = _make_fake_sb(page_alive=True)

        # The import is lazy inside get_browser; we patch the module-level import.
        import super_browser

        orig_init = super_browser.SuperBrowser

        def _factory(*args, **kwargs):
            return fake_sb

        super_browser.SuperBrowser = _factory
        try:
            result = await runtime.get_browser()
            assert result is fake_sb
            fake_sb.start.assert_awaited_once()
        finally:
            super_browser.SuperBrowser = orig_init

    @pytest.mark.asyncio
    async def test_returns_cached_when_alive(self):
        """Cached browser is returned without restart when healthy."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        fake_sb = _make_fake_sb(page_alive=True)
        runtime._sb = fake_sb

        result = await runtime.get_browser()
        assert result is fake_sb
        fake_sb.start.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_recovers_when_page_dead(self):
        """When the page is dead (is_alive=False), runtime tears down and relaunches."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb

        fresh_sb = _make_fake_sb(page_alive=True)

        import super_browser

        orig_init = super_browser.SuperBrowser

        call_count = 0

        def _factory(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return fresh_sb

        super_browser.SuperBrowser = _factory
        try:
            result = await runtime.get_browser()
            # Dead instance was stopped
            dead_sb.stop.assert_awaited_once()
            # Fresh instance was started
            fresh_sb.start.assert_awaited_once()
            # We got the fresh instance
            assert result is fresh_sb
        finally:
            super_browser.SuperBrowser = orig_init

    @pytest.mark.asyncio
    async def test_recovery_clears_stale_handle(self):
        """After recovery, the stale _sb reference is replaced."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb

        fresh_sb = _make_fake_sb(page_alive=True)

        import super_browser

        orig_init = super_browser.SuperBrowser
        super_browser.SuperBrowser = lambda *a, **kw: fresh_sb
        try:
            await runtime.get_browser()
            assert runtime._sb is fresh_sb
            assert runtime._sb is not dead_sb
        finally:
            super_browser.SuperBrowser = orig_init

    @pytest.mark.asyncio
    async def test_no_recovery_loop_when_both_dead(self):
        """If the fresh launch is also dead, we don't loop forever — return it
        and let the next tool call surface the actual error."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb

        also_dead_sb = _make_fake_sb(page_alive=False)

        import super_browser

        orig_init = super_browser.SuperBrowser
        super_browser.SuperBrowser = lambda *a, **kw: also_dead_sb
        try:
            result = await runtime.get_browser()
            # Recovery happened once (dead → relaunch), but fresh is also dead.
            # Don't loop — return it and let the actual tool call fail naturally.
            dead_sb.stop.assert_awaited_once()
            also_dead_sb.start.assert_awaited_once()
            assert result is also_dead_sb
        finally:
            super_browser.SuperBrowser = orig_init


class TestStatusAfterRecovery:
    """status() should reflect recovery state correctly."""

    @pytest.mark.asyncio
    async def test_status_reports_running_after_recovery(self):
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb
        runtime._backend_name = "PatchrightEngine"

        fresh_sb = _make_fake_sb(page_alive=True)

        import super_browser

        orig_init = super_browser.SuperBrowser
        super_browser.SuperBrowser = lambda *a, **kw: fresh_sb
        try:
            await runtime.get_browser()
            status = await runtime.status()
            assert status["running"] is True
        finally:
            super_browser.SuperBrowser = orig_init

    @pytest.mark.asyncio
    async def test_status_reports_dead_before_recovery(self):
        """status() detects dead browser even before a get_browser() call."""
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb
        runtime._backend_name = "PatchrightEngine"

        status = await runtime.status()
        # A dead browser should not report "running: True"
        assert status["running"] is False


class TestCurrentUrlAfterDeath:
    """current_url() should not crash on a dead page."""

    @pytest.mark.asyncio
    async def test_current_url_on_dead_browser(self):
        from super_browser.mcp_server import MCPBrowserRuntime

        runtime = MCPBrowserRuntime()
        dead_sb = _make_fake_sb(page_alive=False)
        runtime._sb = dead_sb

        url_info = await runtime.current_url()
        assert url_info["started"] is False


class TestPageHandleIsAlive:
    """PageHandle.is_alive reflects underlying page state."""

    def test_is_alive_true_when_page_open(self):
        from super_browser.browser.page import PageHandle

        mock_page = MagicMock()
        mock_page.is_closed = MagicMock(return_value=False)
        ph = PageHandle(mock_page, MagicMock())
        assert ph.is_alive is True

    def test_is_alive_false_when_page_closed(self):
        from super_browser.browser.page import PageHandle

        mock_page = MagicMock()
        mock_page.is_closed = MagicMock(return_value=True)
        ph = PageHandle(mock_page, MagicMock())
        assert ph.is_alive is False

    def test_is_alive_false_when_page_none(self):
        from super_browser.browser.page import PageHandle

        ph = PageHandle.__new__(PageHandle)
        ph._page = None
        assert ph.is_alive is False

    def test_is_alive_false_when_is_closed_missing(self):
        """If the backend doesn't expose is_closed(), treat as alive (don't
        break backends that lack the method)."""
        from super_browser.browser.page import PageHandle

        mock_page = MagicMock(spec=[])  # no methods
        ph = PageHandle(mock_page, MagicMock())
        # Missing is_closed → assume alive (don't falsely kill working backends)
        assert ph.is_alive is True
