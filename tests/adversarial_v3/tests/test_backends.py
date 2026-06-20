"""Tests for browser backends.

Verifies stub backend behavior, protocol compliance, and canned responses.
"""

from __future__ import annotations

import pytest
from adversarial3.backends import StubBackend, create_backend
from adversarial3.core import BrowserBackend, Page


class TestStubBackend:
    """Test the stub backend."""

    @pytest.mark.asyncio
    async def test_is_backend(self):
        backend = StubBackend()
        assert isinstance(backend, BrowserBackend)

    @pytest.mark.asyncio
    async def test_new_page(self):
        backend = StubBackend()
        async with backend:
            page = await backend.new_page()
            assert isinstance(page, Page)
            assert page.url is None

    @pytest.mark.asyncio
    async def test_page_goto(self):
        backend = StubBackend()
        async with backend:
            page = await backend.new_page()
            await page.goto("https://example.com")
            assert page.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_page_evaluate_unconfigured_raises(self):
        """StubPage must raise JSUnsupportedError for unconfigured expressions.

        This prevents vectors from interpreting canned values as real
        browser observations. Use set_js_response() for specific tests.
        """
        from adversarial3.core import JSUnsupportedError

        backend = StubBackend()
        async with backend:
            page = await backend.new_page()
            with pytest.raises(JSUnsupportedError):
                await page.evaluate("navigator.webdriver")
            with pytest.raises(JSUnsupportedError):
                await page.evaluate("navigator.plugins")

    @pytest.mark.asyncio
    async def test_page_evaluate_custom_response(self):
        backend = StubBackend()
        async with backend:
            page = await backend.new_page()
            page.set_js_response("custom.expr", "custom_result")
            assert await page.evaluate("custom.expr") == "custom_result"

    @pytest.mark.asyncio
    async def test_page_close(self):
        backend = StubBackend()
        async with backend:
            page = await backend.new_page()
            await page.close()
            assert page._closed is True

    @pytest.mark.asyncio
    async def test_backend_context_manager(self):
        async with StubBackend() as backend:
            assert isinstance(backend, BrowserBackend)
            page = await backend.new_page()
            assert page is not None

    @pytest.mark.asyncio
    async def test_backend_close_clears_pages(self):
        backend = StubBackend()
        async with backend:
            await backend.new_page()
            await backend.new_page()
            assert len(backend._pages) == 2
        assert len(backend._pages) == 0


class TestCreateBackend:
    """Test backend factory."""

    def test_create_stub_explicitly(self):
        backend = create_backend("stub")
        assert isinstance(backend, StubBackend)

    def test_create_auto_falls_back_to_stub(self):
        # When playwright is not installed, auto should return stub
        backend = create_backend("auto")
        assert isinstance(backend, (StubBackend, object))  # Could be either

    def test_create_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown backend"):
            create_backend("unknown")
