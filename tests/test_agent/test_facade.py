"""Tests for SuperBrowser facade."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.agent.facade import ConfigurationError, SuperBrowser
from super_browser.agent.registry import ToolRegistry
from super_browser.interaction.decorator import agent_action
from super_browser.results import ActionResult, ClickResult, FillResult, NavigateResult, action_result


def _make_browser_with_mocks():
    browser = SuperBrowser()
    browser._session = MagicMock()
    browser._page = MagicMock()
    browser._page.url = "https://example.com"
    browser._page.title = AsyncMock(return_value="Test Page")
    browser._page.goto = AsyncMock()
    browser._page.close = AsyncMock()
    browser._controller = MagicMock()
    browser._controller.click = AsyncMock(return_value=action_result(ok=True, data=ClickResult(target="#btn", method="selector")))
    browser._controller.fill = AsyncMock(return_value=action_result(ok=True, data=FillResult(selector="#email", value_entered="test@test.com", method="selector", character_count=12, clear_first=True)))
    browser._controller.capture_ax_snapshot = AsyncMock()
    browser._running = True
    return browser


class TestNavigate:
    def test_delegates_to_page(self):
        async def _test():
            browser = _make_browser_with_mocks()
            result = await browser.navigate("https://example.com")
            assert result.ok
            assert isinstance(result.data, NavigateResult)
            browser._page.goto.assert_called_once()
        asyncio.run(_test())


class TestClick:
    def test_delegates_to_controller(self):
        async def _test():
            browser = _make_browser_with_mocks()
            result = await browser.click("#btn")
            assert result.ok
            browser._controller.click.assert_called_once()
        asyncio.run(_test())


class TestFill:
    def test_delegates_to_controller(self):
        async def _test():
            browser = _make_browser_with_mocks()
            result = await browser.fill("#email", "test@test.com")
            assert result.ok
            browser._controller.fill.assert_called_once()
        asyncio.run(_test())


class TestAct:
    def test_raises_without_llm_client(self):
        """act() must raise ConfigurationError when no LLM client is set."""
        async def _test():
            browser = _make_browser_with_mocks()
            with pytest.raises(ConfigurationError):
                await browser.act("test instruction", max_steps=5)
        asyncio.run(_test())


class TestObserve:
    def test_returns_page_state(self):
        async def _test():
            browser = _make_browser_with_mocks()
            snap = MagicMock()
            snap.nodes = {}
            browser._controller.capture_ax_snapshot = AsyncMock(return_value=snap)
            result = await browser.observe()
            assert result.ok
            assert "url" in result.data
        asyncio.run(_test())


class TestExtract:
    def test_with_selector(self):
        async def _test():
            browser = _make_browser_with_mocks()
            cdp_mock = AsyncMock()
            cdp_result = MagicMock()
            cdp_result.ok = True
            cdp_result.data = {"result": {"value": "Hello"}}
            cdp_mock.evaluate = AsyncMock(return_value=cdp_result)
            browser._controller._cdp = cdp_mock
            result = await browser.extract("heading", selector="h1")
            assert result.ok
        asyncio.run(_test())


class TestTools:
    def test_returns_api_description(self):
        browser = _make_browser_with_mocks()
        desc = browser.tools()
        assert isinstance(desc, str)


class TestRegisterTool:
    def test_adds_to_registry(self):
        browser = _make_browser_with_mocks()

        @agent_action
        async def custom_action(x: int) -> None:
            """Custom."""

        browser.register_tool(custom_action)
        assert browser._registry.get("custom_action") is not None


class TestLifecycle:
    def test_is_running(self):
        browser = _make_browser_with_mocks()
        assert browser.is_running

    def test_not_running_initially(self):
        browser = SuperBrowser()
        assert not browser.is_running

    def test_abort(self):
        browser = SuperBrowser()
        browser.abort()
        assert browser._abort_signal.is_set()


class TestNotStarted:
    def test_click_returns_failure(self):
        async def _test():
            browser = SuperBrowser()
            result = await browser.click("#btn")
            assert not result.ok
        asyncio.run(_test())
