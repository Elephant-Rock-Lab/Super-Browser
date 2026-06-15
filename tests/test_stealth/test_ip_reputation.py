"""Tests for IPReputationClient — Track B slice 2 (Wave 19).

Covers offline mode, provider integration (mocked), caching, verdict
classification, and failure semantics.
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest

from super_browser.stealth.ip_reputation import (
    IPReputationClient,
    IPReputationResult,
    ReputationVerdict,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def offline_client() -> IPReputationClient:
    """Client with no provider — always offline."""
    return IPReputationClient()


@pytest.fixture
def online_client() -> IPReputationClient:
    """Client with a provider URL."""
    return IPReputationClient(
        provider_url="https://ipapi.co/{ip}/json/",
        timeout=5.0,
        cache_ttl=60.0,
    )


# ---------------------------------------------------------------------------
# ReputationVerdict
# ---------------------------------------------------------------------------

class TestReputationVerdict:
    def test_values(self) -> None:
        assert ReputationVerdict.UNKNOWN == "unknown"
        assert ReputationVerdict.CLEAN == "clean"
        assert ReputationVerdict.LOW_RISK == "low_risk"
        assert ReputationVerdict.MEDIUM_RISK == "medium_risk"
        assert ReputationVerdict.HIGH_RISK == "high_risk"


# ---------------------------------------------------------------------------
# IPReputationResult
# ---------------------------------------------------------------------------

class TestIPReputationResult:
    def test_defaults(self) -> None:
        result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.UNKNOWN,
            risk_score=-1.0,
        )
        assert result.ip == "1.2.3.4"
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.risk_score == -1.0
        assert result.details == {}
        assert result.source == "unknown"
        assert result.cached is False

    def test_frozen(self) -> None:
        result = IPReputationResult(
            ip="1.2.3.4",
            verdict=ReputationVerdict.CLEAN,
            risk_score=0.0,
        )
        with pytest.raises(AttributeError):
            result.ip = "5.6.7.8"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Offline mode
# ---------------------------------------------------------------------------

class TestOfflineMode:
    @pytest.mark.asyncio
    async def test_returns_unknown_without_provider(
        self, offline_client: IPReputationClient,
    ) -> None:
        result = await offline_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.risk_score == -1.0
        assert result.source == "offline"
        assert result.details["reason"] == "no_provider_configured"

    @pytest.mark.asyncio
    async def test_offline_with_no_ip(self, offline_client: IPReputationClient) -> None:
        result = await offline_client.check()
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.ip == ""

    def test_is_offline_property(self, offline_client: IPReputationClient) -> None:
        assert offline_client.is_offline is True

    def test_is_not_offline_when_configured(self, online_client: IPReputationClient) -> None:
        assert online_client.is_offline is False


# ---------------------------------------------------------------------------
# Online mode — mocked responses
# ---------------------------------------------------------------------------

class TestOnlineMode:
    @pytest.mark.asyncio
    async def test_clean_response(self, online_client: IPReputationClient) -> None:
        mock_data = {
            "ip": "1.2.3.4",
            "risk_score": 0.0,
            "country": "US",
            "isp": "Comcast",
        }
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.CLEAN
        assert result.risk_score == 0.0
        assert result.details.get("country") == "US"

    @pytest.mark.asyncio
    async def test_high_risk_response(self, online_client: IPReputationClient) -> None:
        mock_data = {
            "ip": "1.2.3.4",
            "risk_score": 0.95,
            "proxy": True,
        }
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.HIGH_RISK
        assert result.risk_score == 0.95
        assert result.details.get("proxy_detected") is True

    @pytest.mark.asyncio
    async def test_medium_risk_response(self, online_client: IPReputationClient) -> None:
        mock_data = {"ip": "1.2.3.4", "risk_score": 0.50}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.MEDIUM_RISK

    @pytest.mark.asyncio
    async def test_low_risk_response(self, online_client: IPReputationClient) -> None:
        mock_data = {"ip": "1.2.3.4", "risk_score": 0.20}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.LOW_RISK

    @pytest.mark.asyncio
    async def test_proxy_flag_alone(
        self, online_client: IPReputationClient,
    ) -> None:
        """Proxy flag with no risk score → MEDIUM_RISK."""
        mock_data = {"ip": "1.2.3.4", "proxy": True}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.MEDIUM_RISK

    @pytest.mark.asyncio
    async def test_no_data_unknown(self, online_client: IPReputationClient) -> None:
        mock_data = {"ip": "1.2.3.4"}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.risk_score == -1.0

    @pytest.mark.asyncio
    async def test_abuse_confidence_score(
        self, online_client: IPReputationClient,
    ) -> None:
        """AbuseIPDB-style abuse_confidence_score (0-100)."""
        mock_data = {"ip": "1.2.3.4", "abuse_confidence_score": 85}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.risk_score == pytest.approx(0.85)
        assert result.verdict == ReputationVerdict.HIGH_RISK

    @pytest.mark.asyncio
    async def test_score_0_100_normalized(
        self, online_client: IPReputationClient,
    ) -> None:
        """Score field using 0-100 range."""
        mock_data = {"ip": "1.2.3.4", "score": 45}
        with patch.object(online_client, "_fetch", return_value=mock_data):
            result = await online_client.check("1.2.3.4")
        assert result.risk_score == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# Failure semantics
# ---------------------------------------------------------------------------

class TestFailureSemantics:
    @pytest.mark.asyncio
    async def test_http_error_returns_unknown(
        self, online_client: IPReputationClient,
    ) -> None:
        import urllib.error
        with patch.object(online_client, "_fetch", side_effect=urllib.error.HTTPError(
            url="test", code=500, msg="Server Error", hdrs=None, fp=None,
        )):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.details["reason"] == "http_error"
        assert result.details["status"] == 500

    @pytest.mark.asyncio
    async def test_rate_limit_returns_unknown(
        self, online_client: IPReputationClient,
    ) -> None:
        import urllib.error
        with patch.object(online_client, "_fetch", side_effect=urllib.error.HTTPError(
            url="test", code=429, msg="Too Many Requests", hdrs=None, fp=None,
        )):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.details["reason"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_url_error_returns_unknown(
        self, online_client: IPReputationClient,
    ) -> None:
        import urllib.error
        with patch.object(
            online_client, "_fetch",
            side_effect=urllib.error.URLError("Connection refused"),
        ):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.details["reason"] == "url_error"

    @pytest.mark.asyncio
    async def test_timeout_returns_unknown(
        self, online_client: IPReputationClient,
    ) -> None:
        with patch.object(online_client, "_fetch", side_effect=TimeoutError()):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.details["reason"] == "timeout"

    @pytest.mark.asyncio
    async def test_unexpected_error_returns_unknown(
        self, online_client: IPReputationClient,
    ) -> None:
        with patch.object(online_client, "_fetch", side_effect=RuntimeError("boom")):
            result = await online_client.check("1.2.3.4")
        assert result.verdict == ReputationVerdict.UNKNOWN
        assert result.details["reason"] == "unexpected"

    @pytest.mark.asyncio
    async def test_never_raises(self, online_client: IPReputationClient) -> None:
        """No matter what goes wrong, check() must not raise."""
        with patch.object(
            online_client, "_fetch",
            side_effect=ValueError("totally unexpected"),
        ):
            result = await online_client.check("1.2.3.4")
        assert result is not None
        assert result.verdict == ReputationVerdict.UNKNOWN


# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

class TestCaching:
    @pytest.mark.asyncio
    async def test_caches_result(self, online_client: IPReputationClient) -> None:
        mock_data = {"ip": "1.2.3.4", "risk_score": 0.1}
        call_count = 0

        def counting_fetch(url: str) -> dict:
            nonlocal call_count
            call_count += 1
            return mock_data

        with patch.object(online_client, "_fetch", side_effect=counting_fetch):
            r1 = await online_client.check("1.2.3.4")
            r2 = await online_client.check("1.2.3.4")

        assert call_count == 1  # Second call served from cache
        assert r1.cached is False
        assert r2.cached is True

    @pytest.mark.asyncio
    async def test_cache_expires(self) -> None:
        client = IPReputationClient(
            provider_url="https://example.com/{ip}",
            cache_ttl=0.01,  # 10ms
        )
        mock_data = {"ip": "1.2.3.4", "risk_score": 0.1}
        call_count = 0

        def counting_fetch(url: str) -> dict:
            nonlocal call_count
            call_count += 1
            return mock_data

        with patch.object(client, "_fetch", side_effect=counting_fetch):
            await client.check("1.2.3.4")
            time.sleep(0.02)
            await client.check("1.2.3.4")

        assert call_count == 2  # Cache expired, refetched

    @pytest.mark.asyncio
    async def test_cache_keyed_by_ip(self, online_client: IPReputationClient) -> None:
        with patch.object(online_client, "_fetch", return_value={"ip": "1.2.3.4", "risk_score": 0.0}):
            await online_client.check("1.2.3.4")
        with patch.object(online_client, "_fetch", return_value={"ip": "5.6.7.8", "risk_score": 0.9}):
            result = await online_client.check("5.6.7.8")
        assert result.ip == "5.6.7.8"  # Different IP, not cached

    @pytest.mark.asyncio
    async def test_clear_cache(self, online_client: IPReputationClient) -> None:
        with patch.object(online_client, "_fetch", return_value={"ip": "1.2.3.4", "risk_score": 0.0}):
            await online_client.check("1.2.3.4")
        count = online_client.clear_cache()
        assert count == 1


# ---------------------------------------------------------------------------
# URL formatting
# ---------------------------------------------------------------------------

class TestURLFormatting:
    @pytest.mark.asyncio
    async def test_ip_placeholder_in_url(self) -> None:
        client = IPReputationClient(provider_url="https://api.test/{ip}/check")
        captured_url = []

        def capture_fetch(url: str) -> dict:
            captured_url.append(url)
            return {"ip": "1.2.3.4", "risk_score": 0.0}

        with patch.object(client, "_fetch", side_effect=capture_fetch):
            await client.check("1.2.3.4")

        assert captured_url[0] == "https://api.test/1.2.3.4/check"

    @pytest.mark.asyncio
    async def test_no_placeholder_uses_url_as_is(self) -> None:
        client = IPReputationClient(provider_url="https://api.test/check-all")
        captured_url = []

        def capture_fetch(url: str) -> dict:
            captured_url.append(url)
            return {"ip": "1.2.3.4", "risk_score": 0.0}

        with patch.object(client, "_fetch", side_effect=capture_fetch):
            await client.check("1.2.3.4")

        assert captured_url[0] == "https://api.test/check-all"
