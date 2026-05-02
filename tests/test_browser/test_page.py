"""Tests for PageHandle."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.browser import PageHandle
from super_browser.browser.cdp import CDPBridge
from super_browser.browser.config import SessionConfig


def _make_page_handle(page_mock=None, cdp=None):
    page = page_mock or AsyncMock()
    if cdp is None:
        cdp = CDPBridge(AsyncMock(), SessionConfig())
    return PageHandle(page, cdp)


class TestPageHandle:
    def test_goto_delegates(self):
        async def _test():
            page = AsyncMock()
            ph = _make_page_handle(page)
            await ph.goto("https://example.com")
            page.goto.assert_called_once()
        asyncio.run(_test())

    def test_title_delegates(self):
        async def _test():
            page = AsyncMock()
            page.title = AsyncMock(return_value="Test Page")
            ph = _make_page_handle(page)
            title = await ph.title()
            assert title == "Test Page"
        asyncio.run(_test())

    def test_url_property(self):
        page = MagicMock()
        page.url = "https://example.com"
        ph = _make_page_handle(page)
        result = ph.url
        assert result == "https://example.com"

    def test_cdp_property(self):
        cdp = CDPBridge(AsyncMock(), SessionConfig())
        ph = _make_page_handle(cdp=cdp)
        assert ph.cdp is cdp

    def test_raw_page_exposes_page(self):
        page = AsyncMock()
        ph = _make_page_handle(page)
        assert ph.raw_page is page
