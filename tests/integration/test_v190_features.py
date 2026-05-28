"""Integration tests for v1.9.0 — Platform Abstraction + Distribution."""

from __future__ import annotations

from packaging.version import Version as _V
from super_browser import __version__


class TestV190Features:
    """Verify all v1.9.0 features are present and working."""

    def test_version_is_190(self) -> None:
        """Version bumped to 1.9.0."""
        assert _V(__version__) >= _V("1.9.0")

    def test_engine_protocols_defined(self) -> None:
        """All four core protocols exist."""
        from super_browser.browser.engine import (
            BrowserEngine,
            EnginePage,
            StealthBridge,
            StealthInjector,
        )
        assert BrowserEngine is not None
        assert EnginePage is not None
        assert StealthBridge is not None
        assert StealthInjector is not None

    def test_four_backends_exist(self) -> None:
        """All four backend implementations exist."""
        from super_browser.browser.backends.cdp_backend import CDPDirectEngine
        from super_browser.browser.backends.patchright_backend import PatchrightEngine
        from super_browser.browser.backends.playwright_backend import PlaywrightEngine
        from super_browser.browser.backends.selenium_backend import SeleniumEngine

        assert PatchrightEngine is not None
        assert PlaywrightEngine is not None
        assert SeleniumEngine is not None
        assert CDPDirectEngine is not None

    def test_backend_type_enum(self) -> None:
        """BackendType enum has all 5 values."""
        from super_browser.browser.engine import BackendType
        assert BackendType.AUTO == "auto"
        assert BackendType.PATCHRIGHT == "patchright"
        assert BackendType.PLAYWRIGHT == "playwright"
        assert BackendType.SELENIUM == "selenium"
        assert BackendType.CDP == "cdp"

    def test_injectors_module(self) -> None:
        """StealthInjector implementations exist."""
        from super_browser.browser.injectors import (
            BiDiInjector,
            CDPInjector,
            PageScriptInjector,
            select_injector,
        )
        assert CDPInjector is not None
        assert PageScriptInjector is not None
        assert BiDiInjector is not None
        assert callable(select_injector)

    def test_engine_capabilities_flags(self) -> None:
        """EngineCapabilities has all 8 flags."""
        from super_browser.browser.engine import EngineCapabilities
        caps = EngineCapabilities()
        assert hasattr(caps, "cdp")
        assert hasattr(caps, "bidi")
        assert hasattr(caps, "stealth_inject_before")
        assert hasattr(caps, "stealth_inject_after")
        assert hasattr(caps, "network_intercept")
        assert hasattr(caps, "multi_tab")
        assert hasattr(caps, "screenshots")
        assert hasattr(caps, "name")

    def test_controller_no_raw_page(self) -> None:
        """Controller uses EnginePage, not raw_page."""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "raw_page", "src/super_browser/interaction/controller.py"],
            capture_output=True, text=True, cwd="C:/Next AI/SUPER-BROWSER",
        )
        assert result.returncode != 0 or result.stdout.strip() == "0"

    def test_facade_no_batch47_markers(self) -> None:
        """No TODO(BATCH-47) markers remain."""
        import subprocess
        result = subprocess.run(
            ["grep", "-c", "TODO.BATCH-47", "src/super_browser/agent/facade.py"],
            capture_output=True, text=True, cwd="C:/Next AI/SUPER-BROWSER",
        )
        assert result.returncode != 0 or result.stdout.strip() == "0"

    def test_stealth_manager_accepts_bridge(self) -> None:
        """StealthManager accepts StealthBridge protocol."""
        from unittest.mock import MagicMock

        from super_browser.stealth.manager import StealthManager
        bridge = MagicMock()
        mgr = StealthManager(stealth_bridge=bridge)
        assert mgr._stealth_bridge is bridge

    def test_config_backend_fields(self) -> None:
        """Config has backend, browser_type, endpoint fields."""
        from super_browser.config import Config
        cfg = Config()
        assert hasattr(cfg.browser, "backend")
        assert hasattr(cfg.browser, "browser_type")
        assert hasattr(cfg.browser, "endpoint")
        assert cfg.browser.backend == "auto"
        assert cfg.browser.browser_type == "chromium"

    def test_pyproject_optional_deps(self) -> None:
        """pyproject.toml has all backend dep groups."""
        import tomllib
        with open("C:/Next AI/SUPER-BROWSER/pyproject.toml", "rb") as f:
            data = tomllib.load(f)
        deps = data["project"]["optional-dependencies"]
        for group in ("patchright", "playwright", "selenium", "cdp", "all"):
            assert group in deps, f"Missing dep group: {group}"

    def test_ci_workflow_exists(self) -> None:
        """GitHub Actions CI workflow exists."""
        import os
        assert os.path.exists("C:/Next AI/SUPER-BROWSER/.github/workflows/test.yml")
        assert os.path.exists("C:/Next AI/SUPER-BROWSER/.github/workflows/publish.yml")

    def test_platform_abstraction_doc_exists(self) -> None:
        """Platform abstraction documentation exists."""
        import os
        assert os.path.exists("C:/Next AI/SUPER-BROWSER/docs/platform-abstraction.md")
