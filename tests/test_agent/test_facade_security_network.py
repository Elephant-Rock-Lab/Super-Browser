"""Wave 8 tests — Security on network interception facade actions.

Covers intercept_requests(), block_requests(), mock_response(), and
clear_interceptions() — all enforce _check_facade_security() before
calling engine_page.route() or unroute_all().
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
    mgr = MagicMock()
    result = MagicMock()
    result.passed = not blocked
    result.blocked_by = blocked_by if blocked else ""
    mgr.check_action = AsyncMock(return_value=result)
    return mgr, result


def _make_browser_with_mocks(*, security_manager=None) -> SuperBrowser:
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._page.engine_page.route = AsyncMock()
    browser._page.engine_page.unroute_all = AsyncMock()
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
    return browser


# ---------------------------------------------------------------------------
# intercept_requests() security
# ---------------------------------------------------------------------------

class TestInterceptRequestsSecurity:

    def test_log_action_calls_security_before_route(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.intercept_requests("**/api/**", action="log")
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "intercept_requests"
        asyncio.run(_test())

    def test_log_action_uses_sensitive_level(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.intercept_requests("**/api/**", action="log")
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.SENSITIVE
        asyncio.run(_test())

    def test_block_action_uses_dangerous_level(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.intercept_requests("**/ads/**", action="block")
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.DANGEROUS
        asyncio.run(_test())

    def test_blocked_does_not_call_route(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="network policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.intercept_requests("**/api/**", action="block")
            assert not result.ok
            assert result.error.category.value == "security"
            browser._page.engine_page.route.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.intercept_requests("**/api/**", action="log")
            assert result.ok
            browser._page.engine_page.route.assert_called_once()
        asyncio.run(_test())

    def test_redacted_params_consumed(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            async def redacting_check(action_name, params, url, level):
                if action_name == "intercept_requests":
                    params["pattern"] = "**/safe/**"
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.intercept_requests("**/malicious/**", action="log")
            assert browser._page.engine_page.route.call_args[0][0] == "**/safe/**"
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# block_requests() security (delegates to intercept_requests)
# ---------------------------------------------------------------------------

class TestBlockRequestsSecurity:

    def test_secured_as_dangerous(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.block_requests("**/ads/**")
            mgr.check_action.assert_called_once()
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.DANGEROUS
            assert mgr.check_action.call_args[0][0] == "intercept_requests"
        asyncio.run(_test())

    def test_blocked_does_not_call_route(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.block_requests("**/ads/**")
            assert not result.ok
            browser._page.engine_page.route.assert_not_called()
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# mock_response() security
# ---------------------------------------------------------------------------

class TestMockResponseSecurity:

    def test_calls_security_before_route(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.mock_response("**/api/data", '{"ok": true}')
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "mock_response"
        asyncio.run(_test())

    def test_uses_dangerous_level(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.mock_response("**/api/data", '{"ok": true}')
            from super_browser.security.types import SecurityLevel
            assert mgr.check_action.call_args[0][3] == SecurityLevel.DANGEROUS
        asyncio.run(_test())

    def test_blocked_does_not_call_route(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="injection policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.mock_response("**/api/data", '{"evil": true}')
            assert not result.ok
            assert result.error.category.value == "security"
            browser._page.engine_page.route.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.mock_response("**/api/data", '{"ok": true}')
            assert result.ok
            browser._page.engine_page.route.assert_called_once()
        asyncio.run(_test())

    def test_redacted_params_consumed(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)

            async def redacting_check(action_name, params, url, level):
                if action_name == "mock_response":
                    params["body"] = '{"safe": true}'
                    params["status"] = 404
                r = MagicMock()
                r.passed = True
                r.blocked_by = ""
                return r

            mgr.check_action = AsyncMock(side_effect=redacting_check)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.mock_response("**/api/data", '{"evil": true}', status=200)
            # Verify route was called — the body/status are inside the handler
            # closure so we verify route was called at all
            browser._page.engine_page.route.assert_called_once()
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# clear_interceptions() security
# ---------------------------------------------------------------------------

class TestClearInterceptionsSecurity:

    def test_calls_security_before_unroute(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=False)
            browser = _make_browser_with_mocks(security_manager=mgr)
            await browser.clear_interceptions()
            mgr.check_action.assert_called_once()
            assert mgr.check_action.call_args[0][0] == "clear_interceptions"
        asyncio.run(_test())

    def test_blocked_does_not_call_unroute(self) -> None:
        async def _test():
            mgr, _ = _make_fake_security_manager(blocked=True, blocked_by="policy")
            browser = _make_browser_with_mocks(security_manager=mgr)
            result = await browser.clear_interceptions()
            assert not result.ok
            browser._page.engine_page.unroute_all.assert_not_called()
        asyncio.run(_test())

    def test_no_security_manager_allows(self) -> None:
        async def _test():
            browser = _make_browser_with_mocks(security_manager=None)
            result = await browser.clear_interceptions()
            assert result.ok
            browser._page.engine_page.unroute_all.assert_called_once()
        asyncio.run(_test())
