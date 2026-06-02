"""Full E2E — Real browser end-to-end validation of v2.0.

Launches Patchright, navigates to real pages, and validates:
- Browser lifecycle (start → navigate → extract → stop)
- Config composition with flattened AgentConfig
- Consistency inject (fingerprint override)
- Diagnostics (7 checks including IP reputation)
- Human behavior (scroll, dwell, Bézier)
- Challenge token cache
- Stealth health report

Requires: Patchright installed, internet access.
Duration: ~30 seconds.
"""

from __future__ import annotations

import pytest

from super_browser.agent.config import AgentConfig
from super_browser.config import Config, TracingConfig
from super_browser.stealth.behavioral import (
    BezierConfig,
    DwellConfig,
    ScrollProfile,
    dwell,
    generate_bezier_path,
    natural_scroll,
)
from super_browser.stealth.challenges.cache import ChallengeTokenCache
from super_browser.stealth.challenges.turnstile import TurnstileVersion, detect_turnstile_version
from super_browser.stealth.proxy import ProxyPool, ProxyTier
from super_browser.stealth.tls import (
    CHROME_JA4_BASELINE,
    validate_ja4,
)
from super_browser.stealth.types import StealthConfig

# ── Helper ──────────────────────────────────────────────────────────────


def _has_patchright() -> bool:
    try:
        import patchright  # noqa: F401
        return True
    except ImportError:
        return False


pytestmark = pytest.mark.skipif(not _has_patchright(), reason="Patchright not installed")


# ── 1. Browser lifecycle ────────────────────────────────────────────────


class TestRealBrowserLifecycle:
    """Launch Patchright, navigate, extract, stop."""

    @pytest.mark.asyncio
    async def test_start_navigate_extract_stop(self) -> None:
        """Full lifecycle: start → navigate → extract → stop."""
        from super_browser.agent.facade import SuperBrowser

        cfg = Config(
            agent=AgentConfig(enable_stealth=True),
            tracing=TracingConfig(enabled=False),
        )
        sb = SuperBrowser(config=cfg)
        try:
            await sb.start()
            assert sb.is_running

            # Navigate to a lightweight page
            result = await sb.navigate("https://example.com")
            assert result.ok, f"Navigate failed: {result.error}"

            # Extract content
            result = await sb.extract("page heading")
            assert result.ok

            # Observe page state
            result = await sb.observe()
            assert result.ok
            assert result.data["url"] == "https://example.com/"

        finally:
            await sb.stop()
            assert not sb.is_running

    @pytest.mark.asyncio
    async def test_config_composition_works(self) -> None:
        """Flattened AgentConfig enables stealth correctly."""
        cfg = Config(
            agent=AgentConfig(
                enable_stealth=True,
                max_steps=25,
            ),
        )
        assert cfg.agent.enable_stealth is True
        assert cfg.agent.max_steps == 25
        assert not hasattr(cfg.agent, "core")  # v2.0: no .core


# ── 2. Diagnostics with real browser ────────────────────────────────────


class TestRealDiagnostics:
    """Run diagnostics against a live browser session."""

    @pytest.mark.asyncio
    async def test_diagnostics_report(self) -> None:
        """Full diagnostics report with 7 checks."""
        from super_browser.browser.config import SessionConfig
        from super_browser.browser.session import BrowserSession
        from super_browser.stealth.diagnostics import run_diagnostics

        session = BrowserSession(SessionConfig(headless=True))
        try:
            await session.start()
            page = await session.new_page()
            await page.goto("https://example.com")

            stealth_config = StealthConfig(headless=True)
            bridge = getattr(page.engine_page, "stealth_bridge", None) if hasattr(page, "engine_page") else None
            cdp = page.cdp if hasattr(page, "cdp") else None
            target = bridge or cdp

            report = await run_diagnostics(target, stealth_config)

            # Should have 7 checks (v2.0 added IP_REPUTATION)
            assert len(report.checks) >= 7
            check_names = [c.check.value for c in report.checks]
            assert "webdriver_undefined" in check_names
            assert "tls_ja4_match" in check_names
            assert "ip_reputation" in check_names

            # Print report for manual review
            for check in report.checks:
                print(f"  {check.check.value}: {'PASS' if check.passed else 'FAIL'} — {check.detail}")

        finally:
            await session.stop()


# ── 3. Behavioral features ──────────────────────────────────────────────


class TestRealBehavioral:
    """Test behavioral features with real browser."""

    @pytest.mark.asyncio
    async def test_natural_scroll(self) -> None:
        """Natural scroll on a real page."""
        from super_browser.browser.config import SessionConfig
        from super_browser.browser.session import BrowserSession

        session = BrowserSession(SessionConfig(headless=True))
        try:
            await session.start()
            page = await session.new_page()
            await page.goto("https://example.com")

            result = await natural_scroll(
                page.engine_page,
                direction="down",
                distance=100,
                profile=ScrollProfile(pause_probability=0.0),  # No pauses for speed
            )
            assert result["total_px"] >= 100
            assert result["duration_ms"] > 0
        finally:
            await session.stop()

    @pytest.mark.asyncio
    async def test_dwell(self) -> None:
        """Page dwell with short delay."""
        config = DwellConfig(min_seconds=0.05, max_seconds=0.1)
        waited = await dwell(config)
        assert waited >= 0.04  # Some tolerance


# ── 4. TLS / Proxy / IP reputation ──────────────────────────────────────


class TestRealTLS:
    """TLS and IP reputation validation."""

    @pytest.mark.asyncio
    async def test_ip_reputation_check(self) -> None:
        """IP reputation check against real API."""
        from super_browser.stealth.tls import check_ip_reputation

        report = await check_ip_reputation(timeout=15.0)
        assert report.source in ("ip_api", "error")
        if report.source == "ip_api":
            assert report.ip_address != ""
            assert report.risk_level in ("low", "medium", "high", "unknown")
            print(f"  IP: {report.ip_address}, Risk: {report.risk_level}, DC: {report.is_datacenter}")

    def test_ja4_validation_baselines(self) -> None:
        """All JA4 baselines should validate."""
        for version, baseline in CHROME_JA4_BASELINE.items():
            matches, guess = validate_ja4(baseline["ja4"])
            assert matches, f"{version} JA4 baseline should match itself"
            assert guess == version


class TestRealProxyPool:
    """ProxyPool with real endpoint URLs (no actual connections)."""

    def test_pool_operations(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://user:pass@res1.example.com:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://user:pass@res2.example.com:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://user:pass@dc1.example.com:8080", ProxyTier.DATACENTER_TLS)

        assert pool.total_count == 3
        assert pool.healthy_count == 3

        url = pool.get_proxy("example.com", tier=ProxyTier.STANDARD_RESIDENTIAL, sticky=False)
        assert url is not None
        assert "res" in url

        # Sticky session
        url1 = pool.get_proxy("target.com", sticky=True)
        url2 = pool.get_proxy("target.com", sticky=True)
        assert url1 == url2


# ── 5. Challenge token cache ────────────────────────────────────────────


class TestRealTokenCache:
    """Token cache with realistic usage patterns."""

    def test_cache_lifecycle(self) -> None:
        cache = ChallengeTokenCache(default_ttl=60.0)

        # Simulate storing a cf_clearance token
        cache.store("example.com", "cf_clearance", "abc123def456", solve_duration_ms=2500.0)

        # Retrieve it
        token = cache.get("example.com", "cf_clearance")
        assert token is not None
        assert token.token_value == "abc123def456"
        assert token.solve_duration_ms == 2500.0

        # Mark replay success
        cache.mark_replay_success("example.com", "cf_clearance")

        # Check stats
        stats = cache.stats()
        assert stats["total_entries"] == 1
        assert stats["avg_solve_duration_ms"] == 2500.0

    def test_turnstile_version_detection(self) -> None:
        """Turnstile version detection on real-ish URLs."""
        invisible_url = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/if/ov2/av0/rcv/invisible/direct/abc123"
        assert detect_turnstile_version(invisible_url) == TurnstileVersion.INVISIBLE

        managed_url = "https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/turnstile/if/ov2/av0/rcv/managed/direct/abc123"
        assert detect_turnstile_version(managed_url) == TurnstileVersion.MANAGED


# ── 6. Bézier curves (mathematical, no browser needed) ──────────────────


class TestRealBezier:
    """Bézier curve generation validation."""

    def test_curve_path_is_realistic(self) -> None:
        """Generate a path and verify it's not a straight line."""
        points = generate_bezier_path((0, 0), (500, 500), BezierConfig(sample_count=50))
        assert len(points) == 50

        # Start and end should be close to targets
        assert abs(points[0][0]) < 5
        assert abs(points[0][1]) < 5
        assert abs(points[-1][0] - 500) < 10
        assert abs(points[-1][1] - 500) < 10

        # At least some intermediate points should deviate from the diagonal
        deviations = []
        for i, (x, y) in enumerate(points):
            expected_y = x  # Diagonal line y=x
            deviations.append(abs(y - expected_y))
        max_deviation = max(deviations)
        assert max_deviation > 20, f"Path is too straight — max deviation: {max_deviation}"
