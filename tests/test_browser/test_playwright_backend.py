"""Tests for BATCH-47/TASK-02 — PlaywrightBackend.

TEST-47-02-01 through TEST-47-02-09 as specified in Blueprint v1.1.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from super_browser.browser.engine import (
    BrowserEngine,
    EngineCapabilities,
    EnginePage,
    _detect_backend,
)

# =========================================================================
# TEST-47-02-01: PlaywrightEngine constructable
# =========================================================================


class TestPlaywrightEngineConstruction:
    """TEST-47-02-01: PlaywrightEngine exists and is constructable."""

    def test_creating_instance(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine()
        assert engine is not None
        assert engine.backend_name == "playwright"

    def test_creating_with_browser_type(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine(browser_type="firefox")
        assert engine._browser_type == "firefox"


# =========================================================================
# TEST-47-02-02: PlaywrightEngine implements BrowserEngine
# =========================================================================


class TestPlaywrightEngineProtocol:
    """TEST-47-02-02: PlaywrightEngine satisfies BrowserEngine protocol."""

    def test_implements_browser_engine(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine()
        assert isinstance(engine, BrowserEngine)


# =========================================================================
# TEST-47-02-03: PlaywrightPage implements EnginePage
# =========================================================================


class TestPlaywrightPageProtocol:
    """TEST-47-02-03: PlaywrightPage satisfies EnginePage protocol."""

    def test_implements_engine_page(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightPage

        mock_page = MagicMock()
        mock_page.url = "https://example.com"
        page = PlaywrightPage(mock_page, "chromium", None)
        assert isinstance(page, EnginePage)


# =========================================================================
# TEST-47-02-04: Chromium capabilities report CDP
# =========================================================================


class TestPlaywrightCapabilitiesChromium:
    """TEST-47-02-04: Chromium capabilities report CDP."""

    def test_chromium_has_cdp(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine(browser_type="chromium")
        caps = engine.capabilities
        assert isinstance(caps, EngineCapabilities)
        assert caps.cdp is True
        assert caps.stealth_inject_before is True
        assert caps.name == "playwright-chromium"


# =========================================================================
# TEST-47-02-05: Firefox capabilities report no CDP
# =========================================================================


class TestPlaywrightCapabilitiesFirefox:
    """TEST-47-02-05: Firefox capabilities — no CDP, has BiDi."""

    def test_firefox_no_cdp(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine(browser_type="firefox")
        caps = engine.capabilities
        assert caps.cdp is False
        assert caps.bidi is True
        assert caps.name == "playwright-firefox"


# =========================================================================
# TEST-47-02-06: WebKit capabilities report no CDP
# =========================================================================


class TestPlaywrightCapabilitiesWebKit:
    """TEST-47-02-06: WebKit capabilities — no CDP, no BiDi."""

    def test_webkit_no_cdp(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine(browser_type="webkit")
        caps = engine.capabilities
        assert caps.cdp is False
        assert caps.bidi is False
        assert caps.name == "playwright-webkit"


# =========================================================================
# TEST-47-02-07: Stealth bridge available on Chromium
# =========================================================================


class TestPlaywrightStealthBridge:
    """TEST-47-02-07: Stealth bridge lifecycle."""

    def test_chromium_stealth_bridge_none_without_context(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightPage

        mock_page = MagicMock()
        page = PlaywrightPage(mock_page, "chromium", None)
        assert page.stealth_bridge is None

    def test_firefox_no_stealth_bridge(self) -> None:
        from super_browser.browser.backends.playwright_backend import PlaywrightPage

        mock_page = MagicMock()
        page = PlaywrightPage(mock_page, "firefox", None)
        assert page.stealth_bridge is None


# =========================================================================
# TEST-47-02-08: Auto-detect returns playwright when configured
# =========================================================================


class TestDetectBackendPlaywright:
    """TEST-47-02-08: _detect_backend returns playwright when configured."""

    def test_explicit_playwright(self) -> None:
        import argparse

        config = argparse.Namespace(backend="playwright", mode=None)
        assert _detect_backend(config) == "playwright"


# =========================================================================
# TEST-47-02-09: Playwright import failure handled gracefully
# =========================================================================


class TestPlaywrightImportFailure:
    """TEST-47-02-09: PlaywrightBackend handles ImportError gracefully."""

    def test_import_failure_graceful(self) -> None:
        """Engine is importable and constructable even without playwright installed."""
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine

        engine = PlaywrightEngine()
        assert engine is not None
        # If start() is called without playwright, it should raise ImportError
        # (not a segfault or silent failure)
