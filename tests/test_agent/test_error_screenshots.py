"""Tests for BATCH-11 error screenshot/DOM capture (M32).

TEST-11-01-03: Screenshot captured on error when debug=True
TEST-11-01-04: DOM snapshot captured alongside screenshot
TEST-11-01-06: Screenshot saved to configured directory
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.debug import InteractiveDebugSession
from super_browser.agent.types import DebugConfig


# -- Helpers ----------------------------------------------------------------

def _make_page(tmp_dir: str):
    """Create a mock page that writes to *tmp_dir*."""
    page = MagicMock()
    page.url = "https://example.com/error-page"
    page.title = AsyncMock(return_value="Error Page")
    page.evaluate = AsyncMock(return_value="Error body text")

    async def fake_screenshot(path=None):
        Path(path).write_bytes(b"PNG_DATA")

    page.screenshot = fake_screenshot
    page.content = AsyncMock(return_value="<html><body>Error Page Content</body></html>")
    return page


# -- Tests ------------------------------------------------------------------


class TestErrorScreenshots:
    """TEST-11-01-03: Screenshot captured on error when debug=True."""

    def test_screenshot_captured_on_error(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                cfg = DebugConfig(enabled=True, screenshot_dir=tmp, capture_dom=False)
                session = InteractiveDebugSession(cfg, interactive=False)
                page = _make_page(tmp)
                snapshot = await session.capture_error_artifacts(
                    page, RuntimeError("page crashed"), cfg,
                )
                assert snapshot.screenshot_path != ""
                assert os.path.exists(snapshot.screenshot_path)
        asyncio.run(_test())

    def test_screenshot_captured_even_when_dom_disabled(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                cfg = DebugConfig(enabled=True, screenshot_dir=tmp, capture_dom=False)
                session = InteractiveDebugSession(cfg, interactive=False)
                page = _make_page(tmp)
                snapshot = await session.capture_error_artifacts(
                    page, RuntimeError("err"), cfg,
                )
                assert snapshot.screenshot_path
                assert snapshot.dom_path == ""
        asyncio.run(_test())


class TestDOMSnapshot:
    """TEST-11-01-04: DOM snapshot captured alongside screenshot."""

    def test_dom_captured_when_enabled(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                cfg = DebugConfig(enabled=True, screenshot_dir=tmp, capture_dom=True)
                session = InteractiveDebugSession(cfg, interactive=False)
                page = _make_page(tmp)
                snapshot = await session.capture_error_artifacts(
                    page, RuntimeError("err"), cfg,
                )
                assert snapshot.dom_path != ""
                assert os.path.exists(snapshot.dom_path)
                content = Path(snapshot.dom_path).read_text()
                assert "Error Page Content" in content
        asyncio.run(_test())

    def test_both_screenshot_and_dom_captured(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                cfg = DebugConfig(enabled=True, screenshot_dir=tmp, capture_dom=True)
                session = InteractiveDebugSession(cfg, interactive=False)
                page = _make_page(tmp)
                snapshot = await session.capture_error_artifacts(
                    page, RuntimeError("err"), cfg,
                )
                assert snapshot.screenshot_path != ""
                assert snapshot.dom_path != ""
                assert os.path.exists(snapshot.screenshot_path)
                assert os.path.exists(snapshot.dom_path)
        asyncio.run(_test())


class TestScreenshotDirectory:
    """TEST-11-01-06: Screenshot saved to configured directory."""

    def test_screenshot_uses_configured_directory(self):
        async def _test():
            with tempfile.TemporaryDirectory() as tmp:
                custom_dir = os.path.join(tmp, "my_debug_output")
                cfg = DebugConfig(enabled=True, screenshot_dir=custom_dir, capture_dom=True)
                session = InteractiveDebugSession(cfg, interactive=False)
                page = _make_page(tmp)
                snapshot = await session.capture_error_artifacts(
                    page, RuntimeError("err"), cfg,
                )
                # Directory should have been auto-created
                assert os.path.isdir(custom_dir)
                # Screenshot should be inside that directory
                assert snapshot.screenshot_path.startswith(custom_dir)
                assert os.path.exists(snapshot.screenshot_path)
        asyncio.run(_test())

    def test_default_directory_is_dot_debug_artifacts(self):
        cfg = DebugConfig()
        assert cfg.screenshot_dir == "./debug_artifacts"
