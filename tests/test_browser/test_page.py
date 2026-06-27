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

    def test_screenshot_default_png(self):
        async def _test():
            page = AsyncMock()
            page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n")
            ph = _make_page_handle(page)
            await ph.screenshot()
            # Default must forward type=png (Playwright spelling), no format=.
            page.screenshot.assert_awaited_once_with(full_page=False, type="png")
        asyncio.run(_test())

    def test_screenshot_jpeg_forwards_type_not_format(self):
        async def _test():
            page = AsyncMock()
            # Return JPEG magic so no re-encode path triggers.
            page.screenshot = AsyncMock(return_value=b"\xff\xd8\xff\xe0")
            ph = _make_page_handle(page)
            await ph.screenshot(format="jpeg", quality=70)
            # Must use type= (Playwright), NOT format= (CDP-only).
            call_kwargs = page.screenshot.await_args.kwargs
            assert call_kwargs.get("type") == "jpeg"
            assert "format" not in call_kwargs
            assert call_kwargs.get("quality") == 70
        asyncio.run(_test())

    def test_screenshot_jpeg_png_fallback_reencodes_or_returns_png(self):
        async def _test():
            page = AsyncMock()
            # Backend returns PNG despite jpeg request (Selenium path).
            page.screenshot = AsyncMock(return_value=b"\x89PNG\r\n\x1a\n")
            ph = _make_page_handle(page)
            raw = await ph.screenshot(format="jpeg", quality=80)
            # Result is either re-encoded JPEG (if Pillow installed) or
            # original PNG — either way, it should not raise.
            assert isinstance(raw, (bytes, bytearray))
        asyncio.run(_test())
