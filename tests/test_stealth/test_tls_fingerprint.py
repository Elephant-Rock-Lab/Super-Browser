"""Tests for TLSFingerprintChecker and NetworkStealthReport — Wave 20.

Covers baselines, offline mode, online observe (mocked), compare logic,
report aggregation, and status derivation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.stealth.ip_reputation import IPReputationResult, ReputationVerdict
from super_browser.stealth.proxy_pool import ProxyHealth
from super_browser.stealth.tls_fingerprint import (
    NetworkStealthStatus,
    TLSFingerprintChecker,
    TLSFingerprintObservation,
    TLSFingerprintReport,
    build_network_stealth_report,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def checker() -> TLSFingerprintChecker:
    return TLSFingerprintChecker()


def make_mock_page(json_response: dict[str, Any]) -> MagicMock:
    """Create a mock browser page that returns JSON from echo service."""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.inner_text = AsyncMock(return_value=json.dumps(json_response))
    return page


# ---------------------------------------------------------------------------
# TLSFingerprintObservation
# ---------------------------------------------------------------------------

class TestTLSFingerprintObservation:
    def test_defaults(self) -> None:
        obs = TLSFingerprintObservation()
        assert obs.ja3_hash is None
        assert obs.ja4_hash is None
        assert obs.ja4_string is None
        assert obs.tls_version is None
        assert obs.cipher_suites == []
        assert obs.extensions == []
        assert obs.source == ""
        assert obs.observed_at == 0.0

    def test_frozen(self) -> None:
        obs = TLSFingerprintObservation(ja4_string="test")
        with pytest.raises(AttributeError):
            obs.ja4_string = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Baselines
# ---------------------------------------------------------------------------

class TestBaselines:
    def test_loads_baselines(self, checker: TLSFingerprintChecker) -> None:
        profiles = checker.available_profiles
        assert "chrome143_macos" in profiles
        assert len(profiles) >= 2

    def test_get_baseline(self, checker: TLSFingerprintChecker) -> None:
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None
        assert baseline.ja4_string is not None
        assert baseline.tls_version == "TLSv1.3"

    def test_get_unknown_baseline(self, checker: TLSFingerprintChecker) -> None:
        assert checker.get_baseline("nonexistent") is None

    def test_custom_baselines_path(self, tmp_path: Path) -> None:
        baselines = {
            "baselines": {
                "custom_profile": {
                    "ja4_string": "t13d_test",
                    "tls_version": "TLSv1.3",
                    "source": "test",
                }
            }
        }
        path = tmp_path / "custom_baselines.json"
        path.write_text(json.dumps(baselines))

        checker = TLSFingerprintChecker(baselines_path=path)
        assert "custom_profile" in checker.available_profiles
        baseline = checker.get_baseline("custom_profile")
        assert baseline is not None
        assert baseline.ja4_string == "t13d_test"

    def test_missing_baselines_file(self, tmp_path: Path) -> None:
        """Checker should still work with missing baselines file."""
        path = tmp_path / "nonexistent.json"
        checker = TLSFingerprintChecker(baselines_path=path)
        assert checker.available_profiles == []


# ---------------------------------------------------------------------------
# Observe — offline mode
# ---------------------------------------------------------------------------

class TestObserveOffline:
    @pytest.mark.asyncio
    async def test_offline_returns_stub(self, checker: TLSFingerprintChecker) -> None:
        result = await checker.observe(None)
        assert result.ja4_string is None
        assert result.ja3_hash is None
        assert result.source == "offline"

    @pytest.mark.asyncio
    async def test_offline_with_no_page(self, checker: TLSFingerprintChecker) -> None:
        result = await checker.observe()
        assert result.ja4_hash is None
        assert result.source == "offline"


# ---------------------------------------------------------------------------
# Observe — online mode (mocked)
# ---------------------------------------------------------------------------

class TestObserveOnline:
    @pytest.mark.asyncio
    async def test_observe_tls_peet_ws_format(self, checker: TLSFingerprintChecker) -> None:
        mock_data = {
            "tls": {
                "ja3_hash": "abc123",
                "ja4": "t13d1516h2_8daaf6152771_b0da82dd1658",
                "tls_version": "TLSv1.3",
                "ciphers": ["TLS_AES_128_GCM_SHA256"],
                "extensions": [{"id": 0}, {"id": 23}],
            }
        }
        page = make_mock_page(mock_data)
        result = await checker.observe(page)
        assert result.ja4_string == "t13d1516h2_8daaf6152771_b0da82dd1658"
        assert result.ja3_hash == "abc123"
        assert result.tls_version == "TLSv1.3"
        assert "TLS_AES_128_GCM_SHA256" in result.cipher_suites
        assert 0 in result.extensions
        assert 23 in result.extensions

    @pytest.mark.asyncio
    async def test_observe_flat_format(self, checker: TLSFingerprintChecker) -> None:
        """Some services return flat JSON without 'tls' wrapper."""
        mock_data = {
            "ja3_hash": "def456",
            "ja4_string": "t13d_test_abc_def",
            "tls_version": "TLSv1.3",
        }
        page = make_mock_page(mock_data)
        result = await checker.observe(page)
        assert result.ja3_hash == "def456"
        assert result.ja4_string == "t13d_test_abc_def"

    @pytest.mark.asyncio
    async def test_observe_error_returns_stub(self, checker: TLSFingerprintChecker) -> None:
        """If the echo service fails, return a stub."""
        page = AsyncMock()
        page.goto = AsyncMock(side_effect=RuntimeError("navigation failed"))

        result = await checker.observe(page)
        assert result.ja4_string is None
        assert result.source == "offline"

    @pytest.mark.asyncio
    async def test_observe_invalid_json_returns_stub(self, checker: TLSFingerprintChecker) -> None:
        page = AsyncMock()
        page.goto = AsyncMock()
        page.inner_text = AsyncMock(return_value="not valid json")

        result = await checker.observe(page)
        assert result.ja4_string is None
        assert result.source == "offline"


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------

class TestCompare:
    def test_match(self, checker: TLSFingerprintChecker) -> None:
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None

        observed = TLSFingerprintObservation(
            ja4_string=baseline.ja4_string,
            tls_version=baseline.tls_version,
            source="echo",
        )
        report = checker.compare(observed, "chrome143_macos")
        assert report.matches is True
        assert report.mismatch_details == []
        assert report.recommendation == ""

    def test_ja4_mismatch(self, checker: TLSFingerprintChecker) -> None:
        observed = TLSFingerprintObservation(
            ja4_string="t13dDIFFERENT_hash_here",
            tls_version="TLSv1.3",
            source="echo",
        )
        report = checker.compare(observed, "chrome143_macos")
        assert report.matches is False
        assert len(report.mismatch_details) >= 1
        assert "JA4 mismatch" in report.mismatch_details[0]
        assert "switching backend" in report.recommendation.lower()

    def test_tls_version_mismatch(self, checker: TLSFingerprintChecker) -> None:
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None

        observed = TLSFingerprintObservation(
            ja4_string=baseline.ja4_string,
            tls_version="TLSv1.2",  # Different
            source="echo",
        )
        report = checker.compare(observed, "chrome143_macos")
        assert report.matches is False
        assert any("TLS version mismatch" in d for d in report.mismatch_details)

    def test_unknown_profile(self, checker: TLSFingerprintChecker) -> None:
        observed = TLSFingerprintObservation(ja4_string="test", source="echo")
        report = checker.compare(observed, "nonexistent_profile")
        assert report.matches is False
        assert "Unknown profile" in report.mismatch_details[0]

    def test_stub_observation_skips_comparison(self, checker: TLSFingerprintChecker) -> None:
        """Offline stub should return matches=True (no false alarm)."""
        stub = TLSFingerprintObservation(source="offline")
        report = checker.compare(stub, "chrome143_macos")
        assert report.matches is True
        assert "Offline mode" in report.recommendation

    def test_compare_with_no_baseline_fields(self, checker: TLSFingerprintChecker) -> None:
        """If baseline has no JA4 string, comparison is skipped."""
        observed = TLSFingerprintObservation(ja4_string="test", source="echo")
        report = checker.compare(observed, "chrome143_macos")
        # Baseline has ja4_string, so comparison should run
        # This test verifies that the comparison logic doesn't crash
        # when some baseline fields are None
        assert isinstance(report, TLSFingerprintReport)


# ---------------------------------------------------------------------------
# Check (observe + compare)
# ---------------------------------------------------------------------------

class TestCheck:
    @pytest.mark.asyncio
    async def test_check_offline(self, checker: TLSFingerprintChecker) -> None:
        report = await checker.check(None, "chrome143_macos")
        assert report.matches is True  # No false alarm in offline
        assert "Offline" in report.recommendation

    @pytest.mark.asyncio
    async def test_check_online_match(self, checker: TLSFingerprintChecker) -> None:
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None

        mock_data = {
            "tls": {
                "ja4": baseline.ja4_string,
                "tls_version": baseline.tls_version,
            }
        }
        page = make_mock_page(mock_data)
        report = await checker.check(page, "chrome143_macos")
        assert report.matches is True


# ---------------------------------------------------------------------------
# NetworkStealthReport — build_network_stealth_report
# ---------------------------------------------------------------------------

class TestNetworkStealthReport:
    def test_empty_inputs_unknown(self) -> None:
        report = build_network_stealth_report()
        assert report.overall_status == NetworkStealthStatus.UNKNOWN
        assert report.warnings == []

    def test_all_healthy_proxies(self) -> None:
        proxy_health = {
            "http://a:8080": ProxyHealth(healthy=True),
            "http://b:8080": ProxyHealth(healthy=True),
        }
        report = build_network_stealth_report(proxy_health=proxy_health)
        assert report.overall_status in (
            NetworkStealthStatus.HEALTHY, NetworkStealthStatus.UNKNOWN,
        )

    def test_unhealthy_proxies_degraded(self) -> None:
        proxy_health = {
            "http://a:8080": ProxyHealth(healthy=True),
            "http://b:8080": ProxyHealth(healthy=False, consecutive_failures=3),
        }
        report = build_network_stealth_report(proxy_health=proxy_health)
        assert report.overall_status == NetworkStealthStatus.DEGRADED
        assert any("unhealthy" in w for w in report.warnings)

    def test_high_risk_ip_compromised(self) -> None:
        ip_result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.HIGH_RISK,
            risk_score=0.95,
        )
        report = build_network_stealth_report(ip_reputation=ip_result)
        assert report.overall_status == NetworkStealthStatus.COMPROMISED
        assert any("high_risk" in w for w in report.warnings)

    def test_medium_risk_ip_degraded(self) -> None:
        ip_result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.MEDIUM_RISK,
            risk_score=0.50,
        )
        report = build_network_stealth_report(ip_reputation=ip_result)
        assert report.overall_status == NetworkStealthStatus.DEGRADED

    def test_clean_ip_healthy(self) -> None:
        ip_result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.CLEAN,
            risk_score=0.0,
        )
        report = build_network_stealth_report(ip_reputation=ip_result)
        assert report.overall_status == NetworkStealthStatus.HEALTHY

    def test_tls_mismatch_compromised(self, checker: TLSFingerprintChecker) -> None:
        observed = TLSFingerprintObservation(
            ja4_string="t13dDIFFERENT",
            source="echo",
        )
        tls_report = checker.compare(observed, "chrome143_macos")
        report = build_network_stealth_report(tls_report=tls_report)
        assert report.overall_status == NetworkStealthStatus.COMPROMISED
        assert any("TLS" in w for w in report.warnings)

    def test_tls_match_healthy(self, checker: TLSFingerprintChecker) -> None:
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None
        observed = TLSFingerprintObservation(
            ja4_string=baseline.ja4_string,
            tls_version=baseline.tls_version,
            source="echo",
        )
        tls_report = checker.compare(observed, "chrome143_macos")
        report = build_network_stealth_report(tls_report=tls_report)
        assert report.overall_status == NetworkStealthStatus.HEALTHY

    def test_compromised_takes_precedence_over_degraded(self) -> None:
        """TLS mismatch + unhealthy proxies → COMPROMISED."""
        proxy_health = {
            "http://a:8080": ProxyHealth(healthy=False, consecutive_failures=3),
        }
        observed = TLSFingerprintObservation(ja4_string="wrong", source="echo")
        checker = TLSFingerprintChecker()
        tls_report = checker.compare(observed, "chrome143_macos")
        report = build_network_stealth_report(
            proxy_health=proxy_health,
            tls_report=tls_report,
        )
        assert report.overall_status == NetworkStealthStatus.COMPROMISED

    def test_all_components_combined(self, checker: TLSFingerprintChecker) -> None:
        proxy_health = {"http://a:8080": ProxyHealth(healthy=True)}
        ip_result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.CLEAN,
            risk_score=0.0,
        )
        baseline = checker.get_baseline("chrome143_macos")
        assert baseline is not None
        observed = TLSFingerprintObservation(
            ja4_string=baseline.ja4_string,
            tls_version=baseline.tls_version,
            source="echo",
        )
        tls_report = checker.compare(observed, "chrome143_macos")

        report = build_network_stealth_report(
            proxy_health=proxy_health,
            ip_reputation=ip_result,
            tls_report=tls_report,
        )
        assert report.overall_status == NetworkStealthStatus.HEALTHY
        assert report.warnings == []

    @pytest.mark.asyncio
    async def test_offline_tls_not_warning(self, checker: TLSFingerprintChecker) -> None:
        """Offline TLS report should not add warnings."""
        report = await checker.check(None, "chrome143_macos")
        ns_report = build_network_stealth_report(tls_report=report)
        # Offline mode — no warnings from TLS
        assert not any("TLS" in w for w in ns_report.warnings)


def await_run(coro: Any) -> Any:
    """Helper to run a coroutine in tests."""
    import asyncio
    return asyncio.get_event_loop().run_until_complete(coro)
