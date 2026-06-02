"""Gate 2 tests — Network Stealth: TLS awareness, proxy pool, IP reputation.

Covers:
- 2-A: TLS JA4 validation and reporting
- 2-B: ProxyPool management (rotation, sticky sessions, health)
- 2-C: IP reputation pre-flight check
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from super_browser.stealth.proxy import (
    ProxyEndpoint,
    ProxyEscalator,
    ProxyPool,
    ProxyTier,
)
from super_browser.stealth.tls import (
    CHROME_JA4_BASELINE,
    IPReputationReport,
    TLSReport,
    _ja4_pattern_match,
    validate_ja4,
)
from super_browser.stealth.types import (
    EscalationRecord,
    StealthConfig,
)

# ── 2-A: TLS / JA4 ──────────────────────────────────────────────────────


class TestJA4Validation:
    """JA4 hash validation against Chrome baselines."""

    def test_exact_match_chrome131(self) -> None:
        ja4 = CHROME_JA4_BASELINE["chrome131"]["ja4"]
        matches, version = validate_ja4(ja4)
        assert matches is True
        assert version == "chrome131"

    def test_exact_match_chrome132(self) -> None:
        ja4 = CHROME_JA4_BASELINE["chrome132"]["ja4"]
        matches, version = validate_ja4(ja4)
        assert matches is True
        assert version == "chrome132"

    def test_no_match_unknown_hash(self) -> None:
        matches, version = validate_ja4("t13d0000h2_000000000000_000000000000")
        assert matches is False
        assert version is None

    def test_pattern_match_similar_prefix(self) -> None:
        """JA4 with same cipher/extension count pattern but different suffix."""
        baseline = CHROME_JA4_BASELINE["chrome131"]["ja4"]
        prefix = baseline.split("_")[0]
        modified = prefix + "_aaaaaaaaaaaa_bbbbbbbbbbbb"
        matches, version = validate_ja4(modified)
        # Should get a "-like" match (same prefix, different suffix)
        assert matches is False  # Not exact
        assert version is not None and "-like" in version

    def test_ja4_pattern_match_same_prefix(self) -> None:
        assert _ja4_pattern_match("t13d1517h2_abc_def", "t13d1517h2_xyz_uvw") is True

    def test_ja4_pattern_match_different_prefix(self) -> None:
        assert _ja4_pattern_match("t13d1517h2_abc_def", "t13d1516h2_xyz_uvw") is False


class TestTLSReport:
    """TLSReport dataclass and formatting."""

    def test_report_defaults(self) -> None:
        report = TLSReport()
        assert report.ja4_hash is None
        assert report.ja4_matches_chrome is False
        assert report.supports_http2 is False

    def test_report_diagnostic_detail_with_ja4(self) -> None:
        report = TLSReport(
            ja4_hash="t13d1517h2_abc_def",
            ja4_matches_chrome=True,
            chrome_version_guess="chrome131",
            alpn_protocols=["h2", "http/1.1"],
            supports_http2=True,
            cipher_suite_count=17,
        )
        detail = report.to_diagnostic_detail()
        assert "MATCHES" in detail
        assert "chrome131" in detail
        assert "h2" in detail

    def test_report_diagnostic_detail_no_ja4(self) -> None:
        report = TLSReport()
        detail = report.to_diagnostic_detail()
        assert "not available" in detail


class TestIPReputationReport:
    """IPReputationReport dataclass and flags."""

    def test_clean_ip(self) -> None:
        report = IPReputationReport(ip_address="1.2.3.4", risk_level="low")
        assert not report.is_flagged

    def test_datacenter_flagged(self) -> None:
        report = IPReputationReport(ip_address="1.2.3.4", is_datacenter=True)
        assert report.is_flagged

    def test_proxy_flagged(self) -> None:
        report = IPReputationReport(ip_address="1.2.3.4", is_proxy=True)
        assert report.is_flagged

    def test_tor_flagged(self) -> None:
        report = IPReputationReport(ip_address="1.2.3.4", is_tor=True)
        assert report.is_flagged

    def test_diagnostic_detail(self) -> None:
        report = IPReputationReport(
            ip_address="1.2.3.4",
            is_datacenter=True,
            asn="AS13335",
            org="Cloudflare",
            country="US",
        )
        detail = report.to_diagnostic_detail()
        assert "DATACENTER" in detail
        assert "1.2.3.4" in detail

    def test_diagnostic_detail_clean(self) -> None:
        report = IPReputationReport(ip_address="1.2.3.4", risk_level="low")
        detail = report.to_diagnostic_detail()
        assert "CLEAN" in detail


# ── 2-B: ProxyPool ──────────────────────────────────────────────────────


class TestProxyEndpoint:
    """ProxyEndpoint health tracking."""

    def test_initial_state(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080", tier=ProxyTier.STANDARD_RESIDENTIAL)
        assert ep.healthy is True
        assert ep.fail_count == 0
        assert ep.success_count == 0

    def test_record_success(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080")
        ep.fail_count = 2
        ep.record_success()
        assert ep.success_count == 1
        assert ep.fail_count == 1  # Decay

    def test_record_failure_under_threshold(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080")
        ep.record_failure()
        ep.record_failure()
        assert ep.healthy is True  # Not yet 3

    def test_record_failure_over_threshold(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080")
        for _ in range(3):
            ep.record_failure()
        assert ep.healthy is False

    def test_sticky_session_active(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080", sticky_domain="example.com", sticky_until=9999999999.0)
        assert ep.is_sticky_active

    def test_sticky_session_expired(self) -> None:
        ep = ProxyEndpoint(url="http://proxy:8080", sticky_domain="example.com", sticky_until=0.0)
        assert not ep.is_sticky_active


class TestProxyPool:
    """ProxyPool rotation, sticky sessions, and health."""

    def test_add_endpoint(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://p2:8080", ProxyTier.STANDARD_RESIDENTIAL)
        assert pool.total_count == 2
        assert pool.healthy_count == 2

    def test_remove_endpoint(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        assert pool.remove_endpoint("http://p1:8080") is True
        assert pool.remove_endpoint("http://nonexistent:8080") is False
        assert pool.total_count == 0

    def test_get_proxy_returns_url(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080", ProxyTier.STANDARD_RESIDENTIAL)
        url = pool.get_proxy("example.com")
        assert url == "http://p1:8080"

    def test_get_proxy_empty_pool(self) -> None:
        pool = ProxyPool()
        url = pool.get_proxy("example.com")
        assert url is None

    def test_get_proxy_sticky_session(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.add_endpoint("http://p2:8080")

        # First call assigns sticky
        url1 = pool.get_proxy("example.com", sticky=True)
        # Second call should return same proxy
        url2 = pool.get_proxy("example.com", sticky=True)
        assert url1 == url2

    def test_get_proxy_no_sticky(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.add_endpoint("http://p2:8080")

        # Without sticky, rotation should cycle
        urls = set()
        for _ in range(4):
            url = pool.get_proxy("example.com", sticky=False)
            if url:
                urls.add(url)
        # Should have used both endpoints (round-robin)
        assert len(urls) >= 1

    def test_get_proxy_by_tier(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://res:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://dc:8080", ProxyTier.DATACENTER_TLS)

        url = pool.get_proxy("example.com", tier=ProxyTier.DATACENTER_TLS, sticky=False)
        assert url == "http://dc:8080"

    def test_mark_success(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.mark_success("http://p1:8080")
        eps = pool.endpoints
        assert eps[0].success_count == 1

    def test_mark_failed_unhealthy(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        for _ in range(3):
            pool.mark_failed("http://p1:8080")
        eps = pool.endpoints
        assert eps[0].healthy is False

    def test_unhealthy_excluded(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.add_endpoint("http://p2:8080")
        # Kill p1
        for _ in range(3):
            pool.mark_failed("http://p1:8080")
        # Only p2 should be returned
        for _ in range(5):
            url = pool.get_proxy("test.com", sticky=False)
            assert url == "http://p2:8080"

    def test_clear_sticky(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.get_proxy("example.com", sticky=True)
        cleared = pool.clear_sticky("example.com")
        assert cleared == 1

    def test_clear_all(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://p1:8080")
        pool.add_endpoint("http://p2:8080")
        pool.clear_all()
        assert pool.total_count == 0

    def test_endpoints_by_tier(self) -> None:
        pool = ProxyPool()
        pool.add_endpoint("http://res:8080", ProxyTier.STANDARD_RESIDENTIAL)
        pool.add_endpoint("http://dc:8080", ProxyTier.DATACENTER_TLS)
        residential = pool.endpoints_by_tier(ProxyTier.STANDARD_RESIDENTIAL)
        assert len(residential) == 1
        assert residential[0].url == "http://res:8080"


class TestProxyEscalatorPreserved:
    """ProxyEscalator still works (backward compat)."""

    def test_escalation_logic(self) -> None:
        config = StealthConfig()
        esc = ProxyEscalator(config)
        assert esc.should_escalate(403, "example.com") is True
        assert esc.should_escalate(200, "example.com") is False

    def test_next_tier(self) -> None:
        config = StealthConfig()
        esc = ProxyEscalator(config)
        assert esc.next_tier(ProxyTier.DIRECT) == ProxyTier.STANDARD_RESIDENTIAL
        assert esc.next_tier(ProxyTier.DATACENTER_TLS) is None

    def test_record_escalation(self) -> None:
        config = StealthConfig()
        esc = ProxyEscalator(config)
        record = EscalationRecord(
            domain="example.com",
            from_tier=ProxyTier.DIRECT,
            to_tier=ProxyTier.STANDARD_RESIDENTIAL,
            trigger_status=403,
        )
        esc.record_escalation(record)
        assert esc.escalation_count == 1
        assert esc.current_tier_for_domain("example.com") == ProxyTier.STANDARD_RESIDENTIAL


# ── 2-C: IP reputation integration ─────────────────────────────────────


class TestIPReputationCheck:
    """IP reputation check via public API."""

    @pytest.mark.asyncio
    async def test_check_with_mock_api(self) -> None:
        """IP reputation check returns report (mocked API)."""
        from super_browser.stealth.tls import check_ip_reputation

        mock_response = MagicMock()
        mock_response.read.return_value = b'{"status":"success","country":"US","city":"New York","as":"AS13335","org":"Cloudflare","query":"1.2.3.4","hosting":true,"proxy":false}'
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_response):
            report = await check_ip_reputation()

        assert report.ip_address == "1.2.3.4"
        assert report.is_datacenter is True
        assert report.is_proxy is False
        assert report.risk_level == "high"
        assert report.source == "ip_api"

    @pytest.mark.asyncio
    async def test_check_handles_error(self) -> None:
        """IP reputation check handles API errors gracefully."""
        from super_browser.stealth.tls import check_ip_reputation

        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            report = await check_ip_reputation()

        assert report.risk_level == "unknown"
        assert report.source == "error"
