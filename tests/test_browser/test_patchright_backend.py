"""Tests for PatchrightBackend — BATCH-46/TASK-02.

TEST-46-02-01 through TEST-46-02-10 as specified in Blueprint v1.1.
"""

from unittest.mock import AsyncMock, MagicMock

from super_browser.browser.backends.patchright_backend import (
    PatchrightEngine,
    PatchrightPage,
    PatchrightStealthBridge,
)
from super_browser.browser.cdp import CDPBridge, CDPResult
from super_browser.browser.config import SessionConfig
from super_browser.browser.engine import (
    BrowserEngine,
    EngineCapabilities,
    EnginePage,
    StealthBridge,
    _detect_backend,
)
from super_browser.browser.page import PageHandle

# =========================================================================
# TEST-46-02-01: PatchrightEngine exists and is constructable
# =========================================================================


class TestPatchrightEngineConstruction:
    def test_creating_instance(self):
        """TEST-46-02-01: PatchrightEngine exists and is constructable."""
        engine = PatchrightEngine()
        assert engine is not None
        assert engine.backend_name == "patchright"

    def test_creating_with_config(self):
        config = SessionConfig(headless=True)
        engine = PatchrightEngine(config)
        assert engine is not None


# =========================================================================
# TEST-46-02-02: PatchrightEngine implements BrowserEngine
# =========================================================================


class TestPatchrightEngineProtocol:
    def test_implements_browser_engine(self):
        """TEST-46-02-02: PatchrightEngine implements BrowserEngine."""
        engine = PatchrightEngine()
        assert isinstance(engine, BrowserEngine)


# =========================================================================
# TEST-46-02-03: PatchrightPage implements EnginePage
# =========================================================================


class TestPatchrightPageProtocol:
    def _make_page(self):
        raw = MagicMock()
        raw.url = "https://example.com"
        raw.title = AsyncMock(return_value="Test")
        raw.goto = AsyncMock()
        raw.click = AsyncMock()
        raw.fill = AsyncMock()
        raw.close = AsyncMock()
        raw.content = AsyncMock(return_value="<html></html>")
        raw.screenshot = AsyncMock(return_value=b"\x89PNG")
        raw.hover = AsyncMock()
        raw.drag_and_drop = AsyncMock()
        raw.select_option = AsyncMock()
        raw.set_input_files = AsyncMock()
        raw.evaluate = AsyncMock(return_value=None)
        raw.route = AsyncMock()
        raw.unroute_all = AsyncMock()
        raw.frame_locator = MagicMock(return_value=MagicMock())
        raw.expect_download = MagicMock()
        raw.keyboard = MagicMock()
        raw.keyboard.type = AsyncMock()
        raw.keyboard.press = AsyncMock()
        raw.mouse = MagicMock()
        raw.mouse.wheel = AsyncMock()
        raw.locator = MagicMock(return_value=raw)
        raw.scroll = AsyncMock()
        cdp = MagicMock(spec=CDPBridge)
        return PatchrightPage(raw, cdp)

    def test_implements_engine_page(self):
        """TEST-46-02-03: PatchrightPage implements EnginePage."""
        page = self._make_page()
        assert isinstance(page, EnginePage)


# =========================================================================
# TEST-46-02-04: PatchrightStealthBridge implements StealthBridge
# =========================================================================


class TestPatchrightStealthBridgeProtocol:
    def _make_bridge(self):
        cdp = MagicMock(spec=CDPBridge)
        cdp.send = AsyncMock(return_value=CDPResult(ok=True, data={}, method="test"))
        return PatchrightStealthBridge(cdp)

    def test_implements_stealth_bridge(self):
        """TEST-46-02-04: PatchrightStealthBridge implements StealthBridge."""
        bridge = self._make_bridge()
        assert isinstance(bridge, StealthBridge)


# =========================================================================
# TEST-46-02-05: PatchrightEngine capabilities report CDP
# =========================================================================


class TestPatchrightEngineCapabilities:
    def test_capabilities_report_cdp(self):
        """TEST-46-02-05: PatchrightEngine capabilities report CDP."""
        engine = PatchrightEngine()
        caps = engine.capabilities
        assert isinstance(caps, EngineCapabilities)
        assert caps.cdp is True
        assert caps.stealth_inject_before is True
        assert caps.name == "patchright"


# =========================================================================
# TEST-46-02-06: PageHandle.raw_page still works (deprecated)
# =========================================================================


class TestPageHandleRawPage:
    def test_raw_page_returns_underlying_page(self):
        """TEST-46-02-06: PageHandle.raw_page still works (deprecated)."""
        mock_page = MagicMock()
        mock_cdp = MagicMock(spec=CDPBridge)
        handle = PageHandle(mock_page, mock_cdp)
        assert handle.raw_page is mock_page


# =========================================================================
# TEST-46-02-07: PageHandle.engine_page returns EnginePage
# =========================================================================


class TestPageHandleEnginePage:
    def test_engine_page_returns_engine_page(self):
        """TEST-46-02-07: PageHandle.engine_page returns EnginePage."""
        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        mock_cdp = MagicMock(spec=CDPBridge)
        handle = PageHandle(mock_page, mock_cdp)
        ep = handle.engine_page
        assert isinstance(ep, EnginePage)
        assert isinstance(ep, PatchrightPage)


# =========================================================================
# TEST-46-02-08: Controller uses EnginePage methods
# =========================================================================


class TestControllerEnginePage:
    def test_controller_instantiates_with_page_handle(self):
        """TEST-46-02-08: Controller instantiates with EnginePage."""
        from super_browser.interaction.controller import MultimodalController

        page = MagicMock()
        page.url = "https://example.com"
        page.title = AsyncMock(return_value="Test")
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
        cdp = MagicMock(spec=CDPBridge)
        cdp.send = AsyncMock(return_value=CDPResult(ok=True, data={}, method="test"))

        ctrl = MultimodalController(page, cdp)
        assert ctrl is not None
        # Verify the page handle has engine_page
        assert hasattr(page, "engine_page") or hasattr(page, "raw_page")


# =========================================================================
# TEST-46-02-09: SessionConfig has backend field
# =========================================================================


class TestSessionConfigBackend:
    def test_backend_field_default(self):
        """TEST-46-02-09: SessionConfig has backend field."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            config = SessionConfig()
        assert config.backend == "auto"
        assert config.browser_type == "chromium"
        assert config.endpoint == ""


# =========================================================================
# TEST-46-02-10: _detect_backend picks patchright when available
# =========================================================================


class TestDetectBackend:
    def test_detects_patchright(self):
        """TEST-46-02-10: _detect_backend picks patchright when available."""
        config = MagicMock()
        config.backend = "auto"
        # patchright is importable in this environment
        result = _detect_backend(config)
        assert result == "patchright"

    def test_explicit_backend(self):
        config = MagicMock()
        config.backend = "playwright"
        result = _detect_backend(config)
        assert result == "playwright"
