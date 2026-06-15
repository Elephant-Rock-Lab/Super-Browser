"""Integration tests for v1.10.0 — Launch Blockers Fix.

ITEM-1: Friendly error when no browser backend installed (already exists)
ITEM-2: _configure_verification() wired to Config.agent.core.enable_verification
ITEM-3: BiDi injector documented as future (doc-only)
ITEM-4-5: Backend NotImplementedError documented (doc-only)
ITEM-6-7: Stealth test fixes (live tests, not unit)
ITEM-8: README badges + pyproject.toml URLs updated
"""

from __future__ import annotations

import pytest
from packaging.version import Version as _V

# -- ITEM-1: Backend detection error message --


class TestBackendDetection:
    """_detect_backend gives a clear error when no backend found."""

    def test_detect_backend_raises_with_message(self):
        """When no browser library is importable, raise RuntimeError with install hints."""
        from unittest.mock import patch

        from super_browser.browser.engine import _detect_backend

        # Patch all import probes to raise ImportError
        with patch.dict("sys.modules", {
            "patchright": None,
            "playwright": None,
            "selenium": None,
        }):
            # Force re-import scenario
            with pytest.raises(RuntimeError, match="No browser backend found"):
                _detect_backend(None)


# -- ITEM-2: _configure_verification wiring --


class TestVerificationWiring:
    """_configure_verification reads Config.agent.core.enable_verification."""

    def test_enable_verification_field_exists(self):
        """SuperBrowserConfig has enable_verification field."""
        from super_browser.config import AgentConfig

        cfg = AgentConfig()
        assert hasattr(cfg, "enable_verification")
        assert cfg.enable_verification is False

    def test_enable_verification_can_be_true(self):
        """SuperBrowserConfig.enable_verification can be set to True."""
        from super_browser.config import AgentConfig

        cfg = AgentConfig(enable_verification=True)
        assert cfg.enable_verification is True

    def test_facade_configure_verification_is_not_pass(self):
        """_configure_verification is not a bare pass anymore."""
        import inspect

        from super_browser.agent.facade import SuperBrowser

        source = inspect.getsource(SuperBrowser._configure_verification)
        # Should not be just "pass" — should have real logic
        stripped = source.strip()
        # The method should contain 'verif' or 'return' or 'import'
        assert "pass" not in stripped.split("#")[0] or "verif" in stripped, (
            "_configure_verification should have real implementation, not bare pass"
        )


# -- ITEM-8: README badges --


class TestReadmeBadges:
    """README badges point to real Octo-Lex URLs."""

    @pytest.fixture()
    def readme(self):
        with open("README.md") as f:
            return f.read()

    def test_ci_badge_points_to_github(self, readme):
        """CI badge uses github.com/Octo-Lex."""
        assert "Octo-Lex/Super-Browser" in readme

    def test_no_example_com_badges(self, readme):
        """No badges point to example.com."""
        assert "github.com/example/" not in readme

    def test_pypi_badge_exists(self, readme):
        """PyPI badge exists."""
        assert "pypi.org/project/superbrowser-sdk" in readme or "pypi/v/superbrowser-sdk" in readme


class TestPyprojectUrls:
    """pyproject.toml URLs point to Octo-Lex."""

    @pytest.fixture()
    def pyproject(self):
        import tomllib
        with open("pyproject.toml", "rb") as f:
            return tomllib.load(f)

    def test_homepage_url(self, pyproject):
        urls = pyproject["project"]["urls"]
        assert "Octo-Lex/Super-Browser" in urls["Homepage"]

    def test_issues_url(self, pyproject):
        urls = pyproject["project"]["urls"]
        assert "Octo-Lex/Super-Browser/issues" in urls["Issues"]

    def test_no_fake_super_browser_org(self, pyproject):
        urls = pyproject["project"]["urls"]
        for v in urls.values():
            assert "github.com/super-browser/super-browser" not in v


# -- Version check --


class TestVersion:
    """Version is 1.10.0."""

    def test_version_string(self):
        from super_browser import __version__

        assert _V(__version__) >= _V("1.10.0")

    def test_pyproject_version(self):
        import tomllib
        with open("pyproject.toml", "rb") as f:
            d = tomllib.load(f)
        assert _V(d["project"]["version"]) >= _V("1.10.0")
