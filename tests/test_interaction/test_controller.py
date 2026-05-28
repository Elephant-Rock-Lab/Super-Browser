"""Tests for MultimodalController."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

from super_browser.browser.cdp import CDPResult
from super_browser.interaction.cache import TierPreferenceCache
from super_browser.interaction.controller import MultimodalController
from super_browser.interaction.types import AXNode, AXSnapshot, Tier
from super_browser.results import ActionMethod, ErrorCategory


def _make_cdp():
    cdp = AsyncMock()
    cdp.send = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="test", duration_ms=1.0))
    cdp.evaluate = AsyncMock(return_value=CDPResult(
        ok=True,
        data={"result": {"value": json.dumps({"x": 50.0, "y": 100.0, "w": 200.0, "h": 40.0})}},
        error=None, method="Runtime.evaluate", duration_ms=1.0,
    ))
    cdp.compositor_click = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="click", duration_ms=1.0))
    cdp.compositor_type = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="type", duration_ms=1.0))
    cdp.compositor_key_press = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="key", duration_ms=1.0))
    cdp.capture_screenshot = AsyncMock(return_value=CDPResult(
        ok=True, data={"data": "aGVsbG8="}, error=None, method="screenshot", duration_ms=1.0,
    ))
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
    page.engine_page = raw
    return page


def _make_controller(page=None, cdp=None, cache=None, vision=None, **kwargs):
    page = page or _make_page()
    cdp = cdp or _make_cdp()
    return MultimodalController(page, cdp, tier_cache=cache, vision_provider=vision, **kwargs)


# ===========================================================================
# Click
# ===========================================================================

class TestClick:
    def test_tier1_success(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.click("#btn")
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
        asyncio.run(_test())

    def test_tier1_fails_tier2_succeeds(self):
        async def _test():
            page = _make_page()
            page.raw_page.click = AsyncMock(side_effect=RuntimeError("not found"))
            ctrl = _make_controller(page=page)
            result = await ctrl.click("#btn")
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
        asyncio.run(_test())

    def test_all_tiers_fail(self):
        async def _test():
            page = _make_page()
            page.raw_page.click = AsyncMock(side_effect=RuntimeError("not found"))
            cdp = _make_cdp()
            cdp.evaluate = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="test", duration_ms=1.0))
            ctrl = _make_controller(page=page, cdp=cdp)
            result = await ctrl.click("#missing")
            assert not result.ok
            assert result.error.category == ErrorCategory.SELECTOR_NOT_FOUND
        asyncio.run(_test())


# ===========================================================================
# Fill
# ===========================================================================

class TestFill:
    def test_tier1_success(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.fill("#email", "test@example.com")
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
            assert result.data.value_entered == "test@example.com"
        asyncio.run(_test())

    def test_tier2_with_clear_first(self):
        async def _test():
            page = _make_page()
            page.raw_page.click = AsyncMock(side_effect=RuntimeError("shadow"))
            page.raw_page.fill = AsyncMock(side_effect=RuntimeError("shadow"))
            ctrl = _make_controller(page=page)
            result = await ctrl.fill("#email", "new@test.com", clear_first=True)
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
            ctrl._cdp.compositor_key_press.assert_any_call("a", modifiers=2)
        asyncio.run(_test())


# ===========================================================================
# Select
# ===========================================================================

class TestSelect:
    def test_tier1_success(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.select("#country", "US")
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
        asyncio.run(_test())


# ===========================================================================
# Hover
# ===========================================================================

class TestHover:
    def test_tier1_success(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.hover("#menu")
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
        asyncio.run(_test())

    def test_tier2_mouse_moved(self):
        async def _test():
            page = _make_page()
            page.raw_page.hover = AsyncMock(side_effect=RuntimeError("fail"))
            ctrl = _make_controller(page=page)
            result = await ctrl.hover("#menu")
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
            ctrl._cdp.send.assert_any_call("Input.dispatchMouseEvent", {
                "type": "mouseMoved", "x": 150.0, "y": 120.0,
            })
        asyncio.run(_test())


# ===========================================================================
# Drag
# ===========================================================================

class TestDrag:
    def test_tier1_success(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.drag("#src", "#dst")
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
        asyncio.run(_test())

    def test_tier2_dispatches_sequence(self):
        async def _test():
            page = _make_page()
            page.raw_page.drag_and_drop = AsyncMock(side_effect=RuntimeError("fail"))
            ctrl = _make_controller(page=page)
            result = await ctrl.drag("#src", "#dst", steps=3)
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
            # Should have: mousePressed, 3 mouseMoved, mouseReleased
            calls = [c for c in ctrl._cdp.send.call_args_list if "dispatchMouseEvent" in str(c)]
            types = [c[0][1].get("type") for c in calls]
            assert "mousePressed" in types
            assert "mouseReleased" in types
        asyncio.run(_test())


# ===========================================================================
# Scroll
# ===========================================================================

class TestScroll:
    def test_tier1_page_scroll(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.scroll(direction="down", amount=3)
            assert result.ok
            assert result.meta.method == ActionMethod.SELECTOR
        asyncio.run(_test())

    def test_tier2_scroll(self):
        async def _test():
            page = _make_page()
            page.engine_page.scroll = AsyncMock(side_effect=RuntimeError("fail"))
            ctrl = _make_controller(page=page)
            result = await ctrl.scroll(direction="up", amount=2)
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
        asyncio.run(_test())


# ===========================================================================
# Keypress (no cascade)
# ===========================================================================

class TestKeypress:
    def test_direct_dispatch(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.keypress("Enter")
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
            ctrl._cdp.compositor_key_press.assert_called_once_with("Enter", modifiers=0)
        asyncio.run(_test())

    def test_with_modifiers(self):
        async def _test():
            ctrl = _make_controller()
            result = await ctrl.keypress("c", modifiers=2)  # noqa: F841
            ctrl._cdp.compositor_key_press.assert_called_once_with("c", modifiers=2)
        asyncio.run(_test())


# ===========================================================================
# AX Snapshot + coordinate resolution
# ===========================================================================

class TestCoordinateResolution:
    def test_ax_ref_resolution(self):
        async def _test():
            ctrl = _make_controller()
            snap = AXSnapshot(url="https://x.com", title="X", nodes={
                "e5": AXNode(ref="@e5", role="button", name="OK", bounds=(10.0, 20.0, 100.0, 40.0)),
            })
            ctrl._ax_snapshot = snap
            coords = await ctrl._resolve_to_coordinates("@e5")
            assert coords == (60.0, 40.0)
        asyncio.run(_test())

    def test_css_selector_resolution(self):
        async def _test():
            ctrl = _make_controller()
            coords = await ctrl._resolve_to_coordinates("#btn")
            assert coords is not None
            assert coords == (150.0, 120.0)  # x+w/2, y+h/2
        asyncio.run(_test())

    def test_xpath_resolution(self):
        async def _test():
            ctrl = _make_controller()
            coords = await ctrl._resolve_to_coordinates("//button")
            assert coords is not None
        asyncio.run(_test())

    def test_unresolvable_returns_none(self):
        async def _test():
            cdp = _make_cdp()
            cdp.evaluate = AsyncMock(return_value=CDPResult(ok=True, data={}, error=None, method="test", duration_ms=1.0))
            ctrl = _make_controller(cdp=cdp)
            coords = await ctrl._resolve_to_coordinates("#nothing")
            assert coords is None
        asyncio.run(_test())


# ===========================================================================
# Cascade timeout
# ===========================================================================

class TestCascadeTimeout:
    def test_tier1_timeout_falls_to_tier2(self):
        async def _test():
            page = _make_page()

            async def slow_click(*args, **kwargs):
                await asyncio.sleep(10)

            page.raw_page.click = slow_click
            ctrl = _make_controller(page=page, tier_timeouts={Tier.SELECTOR: 0.05, Tier.COORDINATE: 5.0, Tier.VISION: 15.0})
            result = await ctrl.click("#btn")
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
        asyncio.run(_test())


# ===========================================================================
# Tier preference cache integration
# ===========================================================================

class TestCacheIntegration:
    def test_cache_prefers_recorded_tier(self):
        async def _test():
            cache = TierPreferenceCache()
            cache.record_success("example.com", "button.*", Tier.COORDINATE)
            page = _make_page()
            # Tier 1 will succeed, but cache prefers Tier 2
            page.raw_page.click = AsyncMock()
            ctrl = _make_controller(page=page, cache=cache)
            result = await ctrl.click("button.login")
            assert result.ok
            assert result.meta.method == ActionMethod.COORDINATE
        asyncio.run(_test())


# ===========================================================================
# Utility
# ===========================================================================

class TestUtility:
    def test_extract_domain(self):
        ctrl = _make_controller(page=_make_page("https://github.com/user/repo"))
        assert ctrl._extract_domain() == "github.com"

    def test_extract_domain_empty(self):
        ctrl = _make_controller(page=_make_page("about:blank"))
        assert ctrl._extract_domain() == ""

    def test_classify_selector_button(self):
        ctrl = _make_controller()
        assert ctrl._classify_selector_pattern("button.login-btn") == "button.*"

    def test_classify_selector_id(self):
        ctrl = _make_controller()
        assert ctrl._classify_selector_pattern("#submit-abc123") == "#submit-*"

    def test_classify_selector_ref(self):
        ctrl = _make_controller()
        assert ctrl._classify_selector_pattern("@e5") == "@ref"

    def test_classify_selector_xpath(self):
        ctrl = _make_controller()
        assert ctrl._classify_selector_pattern("//div/span") == "xpath"
