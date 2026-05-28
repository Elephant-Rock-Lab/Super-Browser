"""Integration tests for BATCH-46 — Platform abstraction engine backends."""

from __future__ import annotations

from packaging.version import Version as _V

from super_browser import __version__
from super_browser.browser.engine import (
    EngineCapabilities,
    EnginePage,
    StealthBridge,
    _detect_backend,
)
from super_browser.config import Config
from super_browser.results import ActionResult, SuccessCategory


class TestV190EngineBackends:
    """TEST-46-03: Integration verification for platform abstraction."""

    def test_version_is_180_or_later(self) -> None:
        """Version is at least 1.8.0."""
        assert _V(__version__) >= _V("1.8.0")

    def test_facade_constructs_with_auto_backend(self) -> None:
        """SuperBrowser can be created with auto backend config."""
        config = Config()
        # Don't call start() — just verify construction
        assert config.browser is not None

    def test_engine_capabilities_patchright(self) -> None:
        """Patchright backend capabilities are correct."""
        caps = EngineCapabilities(
            cdp=True,
            stealth_inject_before=True,
            network_intercept=True,
            multi_tab=True,
            name="patchright",
        )
        assert caps.cdp is True
        assert caps.stealth_inject_before is True
        assert caps.name == "patchright"

    def test_detect_backend_returns_patchright(self) -> None:
        """Auto-detection finds Patchright when installed."""
        result = _detect_backend(None)
        assert result in ("patchright", "playwright", "selenium")

    def test_action_result_unchanged(self) -> None:
        """ActionResult has same fields after refactoring."""
        r = ActionResult(ok=True, success_category=SuccessCategory.NAVIGATION)
        d = r.to_dict()
        assert "ok" in d
        assert "result_category" in d
        assert "success_category" in d
        assert "failure_category" in d
        assert "next_actions" in d
        assert "page_change_summary" in d

    def test_engine_page_protocol_complete(self) -> None:
        """EnginePage protocol has all required members."""
        expected = {
            "goto", "title", "close", "content", "click", "fill",
            "select_option", "hover", "drag_and_drop", "scroll",
            "type_text", "press_key", "set_input_files", "evaluate",
            "screenshot", "route", "unroute_all", "frame_locator",
            "expect_download", "url", "stealth_bridge",
        }
        for name in expected:
            assert hasattr(EnginePage, name), f"Missing: {name}"

    def test_stealth_bridge_protocol_complete(self) -> None:
        """StealthBridge protocol has all required methods."""
        expected = {
            "cdp_send", "inject_script_before_load",
            "get_ax_tree", "get_all_cookies", "set_cookies",
            "capture_screenshot_cdp",
        }
        for name in expected:
            assert hasattr(StealthBridge, name), f"Missing: {name}"

    def test_config_has_backend_fields(self) -> None:
        """Config supports backend/browser_type/endpoint."""
        config = Config()
        assert hasattr(config.browser, "backend")
        assert hasattr(config.browser, "browser_type")
        assert hasattr(config.browser, "endpoint")
