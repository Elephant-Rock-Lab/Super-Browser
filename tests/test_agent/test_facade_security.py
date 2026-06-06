"""Wave 5 tests — Security Facade Enforcement.

Ensures direct facade calls (navigate, click, fill) enforce the configured
SecurityManager, and that security-disabled calls preserve existing behavior.
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
    """Create a fake async security manager for testing.

    Returns a MagicMock whose check_action is an AsyncMock that returns
    a SecurityCheckResult-like object.
    """
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
    browser._controller.click = AsyncMock(return_value=action_result(ok=True))
    browser._controller.fill = AsyncMock(return_value=action_result(ok=True))
    browser._running = True
    browser._security_manager = security_manager
    return browser


# ---------------------------------------------------------------------------
# navigate() security
# ---------------------------------------------------------------------------

class TestNavigateSecurity:

    def test_calls_security_before_goto(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.navigate("https://example.com")
            mgr.check_action.assert_called_once()
            call_args = mgr.check_action.call_args
            assert call_args[0][0] == "navigate"
            assert call_args[0][1] == {"url": "https://example.com"}
            browser._page.goto.assert_called_once()
        asyncio.run(_test())

    def test_blocked_does_not_call_goto(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="domain blocklist")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.navigate("https://malicious.com")
            assert not result.ok
            assert result.error.category.value == "security"
            assert "domain blocklist" in result.error.message
            browser._page.goto.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows_navigation(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.navigate("https://example.com")
            assert result.ok
            browser._page.goto.assert_called_once()
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# click() security
# ---------------------------------------------------------------------------

class TestClickSecurity:

    def test_calls_security_before_controller_click(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.click("#btn")
            mgr.check_action.assert_called_once()
            call_args = mgr.check_action.call_args
            assert call_args[0][0] == "click"
            assert call_args[0][1] == {"target": "#btn"}
            browser._controller.click.assert_called_once()
        asyncio.run(_test())

    def test_blocked_does_not_call_controller_click(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="action policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.click("#btn")
            assert not result.ok
            assert result.error.category.value == "security"
            assert "action policy" in result.error.message
            browser._controller.click.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows_click(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.click("#btn")
            assert result.ok
            browser._controller.click.assert_called_once()
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# fill() security
# ---------------------------------------------------------------------------

class TestFillSecurity:

    def test_calls_security_before_controller_fill(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.fill("#email", "test@test.com")
            mgr.check_action.assert_called_once()
            call_args = mgr.check_action.call_args
            assert call_args[0][0] == "fill"
            assert call_args[0][1] == {"target": "#email", "value": "test@test.com"}
            browser._controller.fill.assert_called_once()
        asyncio.run(_test())

    def test_blocked_does_not_call_controller_fill(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="injection detected")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.fill("#email", "<script>alert(1)</script>")
            assert not result.ok
            assert result.error.category.value == "security"
            assert "injection detected" in result.error.message
            browser._controller.fill.assert_not_called()
        asyncio.run(_test())

    def test_redacted_params_passed_onward(self) -> None:
        """fill() uses potentially redacted params after security check."""
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            # Simulate redaction: security manager mutates params in-place
            original_check = mgr.check_action

            async def redacting_check(action, params, url, level):
                if action == "fill" and "value" in params:
                    params["value"] = "[REDACTED]"
                return await original_check(action, params, url, level)

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            # Keep passed=True
            result_obj = MagicMock()
            result_obj.passed = True
            result_obj.blocked_by = ""
            original_check.return_value = result_obj

            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.fill("#email", "secret-password")

            # Controller.fill should receive the redacted value
            call_args = browser._controller.fill.call_args
            assert call_args[0][0] == "#email"
            assert call_args[0][1] == "[REDACTED]"
        asyncio.run(_test())

    def test_no_security_manager_allows_fill(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.fill("#email", "test@test.com")
            assert result.ok
            browser._controller.fill.assert_called_once()
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Security returns correct error category
# ---------------------------------------------------------------------------

class TestSecurityErrorCategory:

    def test_blocked_returns_security_error_category(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            for method_name, call in [
                ("navigate", lambda: browser.navigate("https://evil.com")),
                ("click", lambda: browser.click("#btn")),
                ("fill", lambda: browser.fill("#inp", "val")),
            ]:
                result = await call()
                assert not result.ok, f"{method_name} should fail"
                assert result.error.category.value == "security", f"{method_name} should be SECURITY"
        asyncio.run(_test())
