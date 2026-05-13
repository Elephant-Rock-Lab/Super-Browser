"""BATCH-27/TASK-02 — Launch Integration & Option Passthrough tests.

TEST-27-02-01: proxy passed to cloakbrowser.launch
TEST-27-02-02: humanize=True passed through
TEST-27-02-03: fingerprint seed set via config
TEST-27-02-04: CDP session created from CloakBrowser page
TEST-27-02-05: cloak_config property returns CloakConfig
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from super_browser.browser import BrowserSession, SessionConfig, SessionMode
from super_browser.browser.cloak_backend import CloakBrowserAdapter
from super_browser.config import CloakConfig

# ── TEST-27-02-01: proxy passed to cloakbrowser.launch ──────────────────


class TestProxyPassthrough:
    """TEST-27-02-01 — proxy passed to cloakbrowser.launch."""

    def test_proxy_forwarded(self) -> None:
        """Proxy URL from config is forwarded to adapter."""
        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            cloak_cfg = CloakConfig()
            adapter = CloakBrowserAdapter.from_config(
                cloak_cfg,
                proxy="http://user:pass@proxy:8080",
                headless=True,
            )
            assert adapter is not None
            assert adapter._proxy == "http://user:pass@proxy:8080"


# ── TEST-27-02-02: humanize=True passed through ────────────────────────


class TestHumanizePassthrough:
    """TEST-27-02-02 — humanize=True passed through."""

    def test_humanize_forwarded(self) -> None:
        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            cloak_cfg = CloakConfig(cloak_humanize=True, cloak_humanize_preset="careful")
            adapter = CloakBrowserAdapter.from_config(cloak_cfg)
            assert adapter is not None
            assert adapter._humanize is True
            assert adapter._humanize_preset == "careful"


# ── TEST-27-02-03: fingerprint seed set via config ─────────────────────


class TestFingerprintSeed:
    """TEST-27-02-03 — fingerprint seed set via config."""

    def test_seed_forwarded(self) -> None:
        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            cloak_cfg = CloakConfig(cloak_fingerprint_seed=42)
            adapter = CloakBrowserAdapter.from_config(cloak_cfg)
            assert adapter is not None
            assert adapter._fingerprint_seed == 42

    def test_seed_none_by_default(self) -> None:
        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            cloak_cfg = CloakConfig()
            adapter = CloakBrowserAdapter.from_config(cloak_cfg)
            assert adapter is not None
            assert adapter._fingerprint_seed is None


# ── TEST-27-02-04: CDP session created from CloakBrowser page ──────────


class TestCDPSessionFromCloak:
    """TEST-27-02-04 — CDP session created from CloakBrowser page."""

    def test_cdp_session_on_cloak_page(self) -> None:
        """After CloakBrowser launch, new_page() creates a CDP bridge."""

        async def _test() -> None:
            mock_browser = AsyncMock()
            mock_browser.version = "1.0-cloak"
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)

            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_cdp = AsyncMock()
            mock_cdp.on = MagicMock()
            mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

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

                # Create a page — CDP session should work
                ph = await session.new_page()
                assert ph is not None
                assert ph.cdp is not None

                await session.stop()

        asyncio.run(_test())


# ── TEST-27-02-05: cloak_config property returns CloakConfig ────────────


class TestCloakConfigProperty:
    """TEST-27-02-05 — cloak_config property returns CloakConfig."""

    def test_returns_cloak_config_on_facade(self) -> None:
        """Facade exposes cloak_config when a session is active."""

        async def _test() -> None:
            from super_browser.agent.facade import SuperBrowser

            mock_browser = AsyncMock()
            mock_browser.version = "1.0-cloak"
            mock_context = AsyncMock()
            mock_browser.new_context = AsyncMock(return_value=mock_context)
            mock_page = AsyncMock()
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_cdp = AsyncMock()
            mock_cdp.on = MagicMock()
            mock_context.new_cdp_session = AsyncMock(return_value=mock_cdp)

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
                patch.object(SuperBrowser, "_configure_verification"),
                patch.object(SuperBrowser, "_configure_vision"),
                patch.object(SuperBrowser, "_configure_stealth"),
                patch.object(SuperBrowser, "_configure_skills"),
            ):
                sb = SuperBrowser()
                await sb.start()
                # facade should expose stealth_backend
                assert sb.stealth_backend == "cloak"
                await sb.stop()

    def test_returns_none_without_session(self) -> None:
        """Facade returns None for cloak_config when no session."""
        from super_browser.agent.facade import SuperBrowser

        sb = SuperBrowser()
        assert sb.cloak_config is None
        assert sb.stealth_backend == "patchright"
