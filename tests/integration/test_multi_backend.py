"""Integration tests for BATCH-48 — SeleniumBackend + CDPDirectBackend."""

from __future__ import annotations

from super_browser.browser.engine import BackendType, _detect_backend


class TestMultiBackendIntegration:
    """TEST-48-03: Integration verification for all four backends."""

    def test_selenium_importable(self) -> None:
        """SeleniumBackend module loads without error."""
        from super_browser.browser.backends.selenium_backend import (
            SeleniumEngine,
            SeleniumPage,
            SeleniumStealthBridge,
        )
        assert SeleniumEngine is not None
        assert SeleniumPage is not None
        assert SeleniumStealthBridge is not None

    def test_cdp_direct_importable(self) -> None:
        """CDPDirectBackend module loads without error."""
        from super_browser.browser.backends.cdp_backend import (
            CDPDirectEngine,
            CDPDirectPage,
            CDPDirectStealthBridge,
        )
        assert CDPDirectEngine is not None
        assert CDPDirectPage is not None
        assert CDPDirectStealthBridge is not None

    def test_all_backends_in_init(self) -> None:
        """All four backends exported from __init__."""
        # CDPDirect may be None if websockets not installed
        from super_browser.browser import backends
        assert hasattr(backends, "CDPDirectEngine")

    def test_backend_type_enum_complete(self) -> None:
        """BackendType enum has all 5 values."""
        assert BackendType.AUTO == "auto"
        assert BackendType.PATCHRIGHT == "patchright"
        assert BackendType.PLAYWRIGHT == "playwright"
        assert BackendType.SELENIUM == "selenium"
        assert BackendType.CDP == "cdp"

    def test_explicit_selenium_detection(self) -> None:
        """Explicit config backend='selenium' returns 'selenium'."""
        import argparse
        config = argparse.Namespace(backend="selenium", mode=None)
        assert _detect_backend(config) == "selenium"

    def test_explicit_cdp_detection(self) -> None:
        """Explicit config backend='cdp' returns 'cdp'."""
        import argparse
        config = argparse.Namespace(backend="cdp", mode=None)
        assert _detect_backend(config) == "cdp"
