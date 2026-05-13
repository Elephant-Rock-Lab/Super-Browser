"""BATCH-27/TASK-01 — CloakConfig & Backend Detection tests.

TEST-27-01-01: cloakbrowser not installed → Patchright
TEST-27-01-02: cloakbrowser installed → uses CloakBrowser
TEST-27-01-03: cloak_enabled=False → Patchright forced
TEST-27-01-04: CloakConfig defaults are correct
TEST-27-01-05: stealth_backend returns "cloak" or "patchright"
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from super_browser.browser import BrowserSession, SessionConfig, SessionMode
from super_browser.config import CloakConfig

# ── TEST-27-01-01: cloakbrowser not installed → Patchright ──────────────


class TestCloakNotInstalled:
    """TEST-27-01-01 — cloakbrowser not installed → falls back to Patchright."""

    def test_falls_back_to_patchright(self) -> None:
        """When cloakbrowser is not importable, session starts with Patchright."""

        async def _test() -> None:
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.version = "1.0"
            mock_browser._impl_obj = MagicMock()
            mock_browser._impl_obj._browser_process = MagicMock()
            mock_browser._impl_obj._browser_process.pid = 1234
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_cdp = AsyncMock()
            mock_cdp.on = MagicMock()
            mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

            with (
                patch(
                    "super_browser.browser.session.async_playwright",
                    return_value=mock_pw,
                ),
                patch(
                    "super_browser.browser.cloak_backend.is_cloak_available",
                    return_value=False,
                ),
            ):
                mock_pw.start = AsyncMock(return_value=mock_pw)
                # Pass a CloakConfig to trigger the cloak path
                cloak_cfg = CloakConfig()
                session = BrowserSession(
                    SessionConfig(headless=True),
                    cloak_config=cloak_cfg,
                )
                await session.start()
                assert session.stealth_backend == "patchright"
                await session.stop()

        asyncio.run(_test())


# ── TEST-27-01-02: cloakbrowser installed → uses CloakBrowser ──────────


class TestCloakInstalled:
    """TEST-27-01-02 — cloakbrowser installed → uses CloakBrowser."""

    def test_uses_cloak_browser(self) -> None:
        """When cloakbrowser is importable, session starts with CloakBrowser."""

        async def _test() -> None:
            mock_browser = AsyncMock()
            mock_browser.version = "1.0-cloak"
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            mock_launch_result = MagicMock()
            mock_launch_result.browser = mock_browser
            mock_launch_result.context = mock_context

            mock_adapter = AsyncMock()
            mock_adapter.launch = AsyncMock(return_value=mock_launch_result)

            with (
                patch(
                    "super_browser.browser.cloak_backend.is_cloak_available",
                    return_value=True,
                ),
                patch(
                    "super_browser.browser.cloak_backend.CloakBrowserAdapter.from_config",
                    return_value=mock_adapter,
                ),
            ):
                cloak_cfg = CloakConfig()
                session = BrowserSession(
                    SessionConfig(mode=SessionMode.CLOAK_LAUNCH),
                    cloak_config=cloak_cfg,
                )
                await session.start()
                assert session.stealth_backend == "cloak"
                await session.stop()

        asyncio.run(_test())


# ── TEST-27-01-03: cloak_enabled=False → Patchright forced ─────────────


class TestCloakDisabled:
    """TEST-27-01-03 — cloak_enabled=False → Patchright forced."""

    def test_forces_patchright(self) -> None:
        """Even if cloakbrowser is installed, cloak_enabled=False forces Patchright."""

        async def _test() -> None:
            mock_pw = AsyncMock()
            mock_browser = AsyncMock()
            mock_browser.version = "1.0"
            mock_browser._impl_obj = MagicMock()
            mock_browser._impl_obj._browser_process = MagicMock()
            mock_browser._impl_obj._browser_process.pid = 1234
            mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            with (
                patch(
                    "super_browser.browser.session.async_playwright",
                    return_value=mock_pw,
                ),
                patch(
                    "super_browser.browser.cloak_backend.is_cloak_available",
                    return_value=True,
                ),
            ):
                mock_pw.start = AsyncMock(return_value=mock_pw)
                cloak_cfg = CloakConfig(cloak_enabled=False)
                session = BrowserSession(
                    SessionConfig(headless=True),
                    cloak_config=cloak_cfg,
                )
                await session.start()
                assert session.stealth_backend == "patchright"
                await session.stop()

        asyncio.run(_test())


# ── TEST-27-01-04: CloakConfig defaults are correct ────────────────────


class TestCloakConfigDefaults:
    """TEST-27-01-04 — CloakConfig has all specified fields with correct defaults."""

    def test_defaults(self) -> None:
        cfg = CloakConfig()
        assert cfg.cloak_enabled is True
        assert cfg.cloak_fingerprint_seed is None
        assert cfg.cloak_humanize is False
        assert cfg.cloak_humanize_preset == "default"
        assert cfg.cloak_geoip is False
        assert cfg.cloak_platform is None

    def test_custom_values(self) -> None:
        cfg = CloakConfig(
            cloak_enabled=False,
            cloak_fingerprint_seed=42,
            cloak_humanize=True,
            cloak_humanize_preset="careful",
            cloak_geoip=True,
            cloak_platform="windows",
        )
        assert cfg.cloak_enabled is False
        assert cfg.cloak_fingerprint_seed == 42
        assert cfg.cloak_humanize is True
        assert cfg.cloak_humanize_preset == "careful"
        assert cfg.cloak_geoip is True
        assert cfg.cloak_platform == "windows"


# ── TEST-27-01-05: stealth_backend returns "cloak" or "patchright" ──────


class TestStealthBackendProperty:
    """TEST-27-01-05 — stealth_backend property reflects actual backend."""

    def test_default_is_patchright(self) -> None:
        session = BrowserSession()
        assert session.stealth_backend == "patchright"

    def test_is_cloak_after_cloak_launch(self) -> None:
        """After successful CloakBrowser launch, returns 'cloak'."""

        async def _test() -> None:
            mock_browser = AsyncMock()
            mock_browser.version = "1.0-cloak"
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            mock_launch_result = MagicMock()
            mock_launch_result.browser = mock_browser
            mock_launch_result.context = mock_context

            mock_adapter = AsyncMock()
            mock_adapter.launch = AsyncMock(return_value=mock_launch_result)

            with (
                patch(
                    "super_browser.browser.cloak_backend.is_cloak_available",
                    return_value=True,
                ),
                patch(
                    "super_browser.browser.cloak_backend.CloakBrowserAdapter.from_config",
                    return_value=mock_adapter,
                ),
            ):
                session = BrowserSession(
                    SessionConfig(mode=SessionMode.CLOAK_LAUNCH),
                    cloak_config=CloakConfig(),
                )
                await session.start()
                assert session.stealth_backend == "cloak"
                await session.stop()

        asyncio.run(_test())
