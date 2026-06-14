"""Wave 6 tests — Security on file and tab facade actions.

Extends Wave 5 security facade coverage to:
- open_tab(url)
- upload_file(selector, file_path)
- download(url_or_selector, save_path)

Each method enforces _check_facade_security() before side effects.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.agent.facade import SuperBrowser
from super_browser.results import action_result

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_fake_security_manager(blocked: bool = False, blocked_by: str = "test policy"):
    """Create a fake async security manager for testing."""
    mgr = MagicMock()
    result = MagicMock()
    result.passed = not blocked
    result.blocked_by = blocked_by if blocked else ""
    mgr.check_action = AsyncMock(return_value=result)
    return mgr, result


def _make_browser_with_mocks(*, security_manager=None) -> SuperBrowser:
    """Create a SuperBrowser with mocked browser internals."""
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._controller = MagicMock()
    for name, doc in [
        ("click", "Click"), ("fill", "Fill"), ("select", "Select"),
        ("hover", "Hover"), ("drag", "Drag"), ("scroll", "Scroll"),
        ("keypress", "Keypress"),
    ]:
        m = AsyncMock(return_value=action_result(ok=True))
        m.__name__ = name
        m.__doc__ = doc
        setattr(browser._controller, name, m)
    browser._controller.capture_ax_snapshot = AsyncMock()
    browser._running = True
    browser._security_manager = security_manager

    # Mock engine context for tab operations
    browser._engine = MagicMock()
    browser._engine.context = MagicMock()
    return browser


# ---------------------------------------------------------------------------
# open_tab() security
# ---------------------------------------------------------------------------

class TestOpenTabSecurity:

    def test_calls_security_before_open(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._tab_manager = MagicMock()
            browser._tab_manager.open_tab = AsyncMock(return_value=MagicMock(tab_id=1))
            browser._tab_manager.get_page = MagicMock(return_value=MagicMock())
            browser._attach_page = AsyncMock()
            await browser.open_tab("https://example.com")
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "open_tab"
            assert mgr.check_action.call_args[0][1] == {"url": "https://example.com"}
        asyncio.run(_test())

    def test_blocked_does_not_open_tab(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="domain blocklist")
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._tab_manager = MagicMock()
            browser._tab_manager.open_tab = AsyncMock()
            result = await browser.open_tab("https://malicious.com")
            assert not result.ok
            assert result.error.category.value == "security"
            browser._tab_manager.open_tab.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows_open_tab(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            browser._tab_manager = MagicMock()
            browser._tab_manager.open_tab = AsyncMock(return_value=MagicMock(tab_id=1))
            browser._tab_manager.get_page = MagicMock(return_value=MagicMock())
            browser._attach_page = AsyncMock()
            result = await browser.open_tab("https://example.com")
            assert result.ok
        asyncio.run(_test())

    def test_open_tab_without_url_passes_empty(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._tab_manager = MagicMock()
            browser._tab_manager.open_tab = AsyncMock(return_value=MagicMock(tab_id=1))
            browser._tab_manager.get_page = MagicMock(return_value=MagicMock())
            browser._attach_page = AsyncMock()
            await browser.open_tab()
            assert mgr.check_action.call_args[0][1] == {"url": ""}
        asyncio.run(_test())

    def test_redacted_url_consumed(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            async def redacting_check(action, params, url, level):
                if action == "open_tab" and "url" in params:
                    params["url"] = "https://sanitized.example.com"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._tab_manager = MagicMock()
            browser._tab_manager.open_tab = AsyncMock(return_value=MagicMock(tab_id=1))
            browser._tab_manager.get_page = MagicMock(return_value=MagicMock())
            browser._attach_page = AsyncMock()
            await browser.open_tab("https://malicious.com")
            # Tab manager should receive redacted URL
            assert browser._tab_manager.open_tab.call_args[0][0] == "https://sanitized.example.com"
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# upload_file() security
# ---------------------------------------------------------------------------

class TestUploadFileSecurity:

    def test_calls_security_before_upload(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._page.engine_page.set_input_files = AsyncMock()
            await browser.upload_file("#file", "/path/to/file.txt")
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "upload_file"
            assert mgr.check_action.call_args[0][1] == {"selector": "#file", "file_path": "/path/to/file.txt"}
            # Dangerous level
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.DANGEROUS
        asyncio.run(_test())

    def test_blocked_does_not_upload(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="file access denied")
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._page.engine_page.set_input_files = AsyncMock()
            result = await browser.upload_file("#file", "/path/to/secret.txt")
            assert not result.ok
            assert result.error.category.value == "security"
            browser._page.engine_page.set_input_files.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows_upload(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            browser._page.engine_page.set_input_files = AsyncMock()
            result = await browser.upload_file("#file", "/path/to/file.txt")
            assert result.ok
            browser._page.engine_page.set_input_files.assert_called_once()
        asyncio.run(_test())

    def test_redacted_file_path_consumed(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            async def redacting_check(action, params, url, level):
                if action == "upload_file" and "file_path" in params:
                    params["file_path"] = "/safe/allowed.txt"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._page.engine_page.set_input_files = AsyncMock()
            await browser.upload_file("#file", "/etc/passwd")
            # Should use redacted path
            call = browser._page.engine_page.set_input_files.call_args
            assert call[0][0] == "#file"
            assert call[0][1] == "/safe/allowed.txt"
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# download() security
# ---------------------------------------------------------------------------

class TestDownloadSecurity:

    def test_calls_security_before_download(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)

            # Mock the context manager for expect_download
            mock_download = MagicMock()
            mock_download.suggested_filename = "file.zip"
            mock_download.save_as = AsyncMock()
            mock_download.path = AsyncMock(return_value="/tmp/file.zip")

            cm = MagicMock()
            class FakeDI:
                @property
                def value(self):
                    async def _get():
                        return mock_download
                    return _get()
            cm.__aenter__ = AsyncMock(return_value=FakeDI())
            cm.__aexit__ = AsyncMock(return_value=None)
            browser._page.engine_page.expect_download = MagicMock(return_value=cm)
            browser._page.engine_page.evaluate = AsyncMock()

            await browser.download("https://example.com/file.zip")
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "download"
        asyncio.run(_test())

    def test_blocked_does_not_download(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="network policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            browser._page.engine_page.expect_download = MagicMock()
            result = await browser.download("https://malicious.com/file.exe")
            assert not result.ok
            assert result.error.category.value == "security"
            browser._page.engine_page.expect_download.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows_download(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)

            mock_download = MagicMock()
            mock_download.suggested_filename = "file.zip"
            mock_download.save_as = AsyncMock()
            mock_download.path = AsyncMock(return_value="/tmp/file.zip")

            class FakeDownloadInfo:
                @property
                def value(self):
                    async def _get():
                        return mock_download
                    return _get()

            cm = MagicMock()
            cm.__aenter__ = AsyncMock(return_value=FakeDownloadInfo())
            cm.__aexit__ = AsyncMock(return_value=None)
            browser._page.engine_page.expect_download = MagicMock(return_value=cm)
            browser._page.engine_page.evaluate = AsyncMock()

            result = await browser.download("https://example.com/file.zip")
            assert result.ok
        asyncio.run(_test())

    def test_redacted_url_consumed(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            async def redacting_check(action, params, url, level):
                if action == "download" and "url_or_selector" in params:
                    params["url_or_selector"] = "https://safe.example.com/file.zip"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)

            browser = _make_browser_with_mocks(security_manager=mgr)

            mock_download = MagicMock()
            mock_download.suggested_filename = "file.zip"
            mock_download.save_as = AsyncMock()
            mock_download.path = AsyncMock(return_value="/tmp/file.zip")

            cm = MagicMock()
            class FakeDI:
                @property
                def value(self):
                    async def _get():
                        return mock_download
                    return _get()
            cm.__aenter__ = AsyncMock(return_value=FakeDI())
            cm.__aexit__ = AsyncMock(return_value=None)
            browser._page.engine_page.expect_download = MagicMock(return_value=cm)
            browser._page.engine_page.evaluate = AsyncMock()

            await browser.download("https://malicious.com/file.exe")
            # Should use redacted URL
            assert browser._page.engine_page.evaluate.call_args[0][1] == "https://safe.example.com/file.zip"
        asyncio.run(_test())
