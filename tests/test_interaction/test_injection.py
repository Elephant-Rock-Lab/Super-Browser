"""TEST-09-01: Selector injection safety tests (HB-09-01)."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.browser.cdp import CDPResult
from super_browser.interaction.controller import MultimodalController
from super_browser.results.validation import PreExecutionValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cdp():
    """Create a mock CDP bridge."""
    cdp = AsyncMock()
    cdp.evaluate = AsyncMock(return_value=CDPResult(
        ok=True,
        data={"result": {"value": json.dumps({"x": 50.0, "y": 100.0, "w": 200.0, "h": 40.0})}},
        error=None, method="Runtime.evaluate", duration_ms=1.0,
    ))
    cdp.compositor_click = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="click", duration_ms=1.0))
    return cdp


def _make_page(url="https://example.com"):
    page = MagicMock()
    page.url = url
    page.title = AsyncMock(return_value="Test Page")
    raw = AsyncMock()
    raw.click = AsyncMock()
    raw.fill = AsyncMock()
    raw.hover = AsyncMock()
    raw.drag_and_drop = AsyncMock()
    raw.select_option = AsyncMock()
    raw.mouse = MagicMock()
    raw.mouse.wheel = AsyncMock()
    raw.locator = MagicMock(return_value=raw)
    raw.scroll = AsyncMock()
    page.raw_page = raw
    return page


def _make_controller(page=None, cdp=None):
    page = page or _make_page()
    cdp = cdp or _make_cdp()
    return MultimodalController(page, cdp)


# ---------------------------------------------------------------------------
# TEST-09-01-01: Double-quote + semicolon injection
# ---------------------------------------------------------------------------

class TestDoubleQuoteInjection:
    """Selector '"]; alert(1); //"' must not break evaluation."""

    def test_injection_selector_does_not_raise(self):
        """TEST-09-01-01: Malicious selector handled safely."""
        async def _test():
            controller = _make_controller()
            # Should not raise — selector is JSON-encoded, not interpolated
            result = await controller._resolve_to_coordinates('"]; alert(1); //"')
            # The CDP mock returns valid coords, so result should be a tuple or None
            assert result is None or isinstance(result, tuple)
        asyncio.run(_test())

    def test_injection_selector_uses_json_dumps(self):
        """Verify the JS expression contains JSON.parse, not raw interpolation."""
        async def _test():
            cdp = _make_cdp()
            controller = _make_controller(cdp=cdp)
            malicious = '"]; alert(1); //"'
            await controller._resolve_to_coordinates(malicious)

            # Verify evaluate was called with JSON.parse pattern
            cdp.evaluate.assert_called_once()
            expr = cdp.evaluate.call_args[0][0]
            # Must contain JSON.parse (safe parameterized pattern)
            assert "JSON.parse" in expr
            # Must NOT contain the raw malicious string outside JSON
            # (it should only appear inside json.dumps output)
            assert 'document.querySelector(""]' not in expr
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-01-02: Single-quote injection
# ---------------------------------------------------------------------------

class TestSingleQuoteInjection:
    """Selector with single quotes handled safely."""

    def test_single_quote_selector_safe(self):
        """TEST-09-01-02: Selector with single quotes does not break evaluation."""
        async def _test():
            controller = _make_controller()
            result = await controller._resolve_to_coordinates("'); window.x='")
            assert result is None or isinstance(result, tuple)
        asyncio.run(_test())

    def test_single_quote_uses_json_parse(self):
        """Verify JSON.parse is used, not raw f-string interpolation."""
        async def _test():
            cdp = _make_cdp()
            controller = _make_controller(cdp=cdp)
            await controller._resolve_to_coordinates("'); window.x='")

            cdp.evaluate.assert_called_once()
            expr = cdp.evaluate.call_args[0][0]
            assert "JSON.parse" in expr
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-01-03: Backtick / template-literal injection
# ---------------------------------------------------------------------------

class TestBacktickInjection:
    """Selector with backticks handled safely."""

    def test_backtick_selector_safe(self):
        """TEST-09-01-03: Selector with backticks does not break evaluation."""
        async def _test():
            controller = _make_controller()
            result = await controller._resolve_to_coordinates("`${constructor}('')`")
            assert result is None or isinstance(result, tuple)
        asyncio.run(_test())

    def test_backtick_uses_json_parse(self):
        """Verify JSON.parse is used, not raw interpolation."""
        async def _test():
            cdp = _make_cdp()
            controller = _make_controller(cdp=cdp)
            await controller._resolve_to_coordinates("`${constructor}('')`")

            cdp.evaluate.assert_called_once()
            expr = cdp.evaluate.call_args[0][0]
            assert "JSON.parse" in expr
            # Ensure no raw backtick injection into JS context
            assert 'document.querySelector(`' not in expr
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-01-04: Normal selectors still resolve correctly
# ---------------------------------------------------------------------------

class TestNormalSelectorsStillWork:
    """Normal selectors must still resolve correctly after the fix."""

    def test_css_selector_resolves(self):
        """TEST-09-01-04a: Normal CSS selector resolves to coordinates."""
        async def _test():
            controller = _make_controller()
            result = await controller._resolve_to_coordinates("#login-btn")
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
        asyncio.run(_test())

    def test_xpath_resolves(self):
        """TEST-09-01-04b: XPath selector resolves to coordinates."""
        async def _test():
            controller = _make_controller()
            result = await controller._resolve_to_coordinates("//button[@id='submit']")
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
        asyncio.run(_test())

    def test_class_selector_resolves(self):
        """TEST-09-01-04c: Class selector resolves to coordinates."""
        async def _test():
            controller = _make_controller()
            result = await controller._resolve_to_coordinates(".submit-btn")
            assert result is not None
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# PreExecutionValidator injection safety
# ---------------------------------------------------------------------------

class TestPreExecutionValidatorInjectionSafe:
    """Verify PreExecutionValidator also uses safe parameterized evaluation."""

    def test_validate_selector_with_injection(self):
        """Malicious selector in PreExecutionValidator is handled safely."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=0)
        validator = PreExecutionValidator(page)

        result = validator.validate_selector('"]; alert(1); //"')
        # Should return a result (not raise), with ok=False since count=0
        assert result.ok is False

        # Verify evaluate was called with JSON.parse pattern
        page.evaluate.assert_called_once()
        expr = page.evaluate.call_args[0][0]
        assert "JSON.parse" in expr

    def test_validate_xpath_with_injection(self):
        """Malicious xpath in PreExecutionValidator is handled safely."""
        page = MagicMock()
        page.evaluate = MagicMock(return_value=0)
        validator = PreExecutionValidator(page)

        result = validator.validate_xpath("'); window.x='")
        assert result.ok is False

        page.evaluate.assert_called_once()
        expr = page.evaluate.call_args[0][0]
        assert "JSON.parse" in expr
