"""Tests for GAP-08 stealth types — enums, dataclasses, properties."""

import time

import pytest

from super_browser.stealth.types import (
    CAPTCHADetection,
    CAPTCHAProvider,
    EscalationRecord,
    HTTPMorphRequestConfig,
    HTTPMorphResponse,
    ProxyPoolConfig,
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthEventType,
    StealthHealthItem,
    StealthHealthReport,
    StealthRisk,
)

# -- Enum values --


class TestProxyTier:
    def test_values(self):
        assert ProxyTier.DIRECT == "direct"
        assert ProxyTier.STANDARD_RESIDENTIAL == "standard_residential"
        assert ProxyTier.PREMIUM_RESIDENTIAL == "premium_residential"
        assert ProxyTier.DATACENTER_TLS == "datacenter_tls"

    def test_count(self):
        assert len(ProxyTier) == 4


class TestCAPTCHAProvider:
    def test_values(self):
        assert CAPTCHAProvider.CLOUDFLARE_TURNSTILE == "cloudflare_turnstile"
        assert CAPTCHAProvider.HCAPTCHA == "hcaptcha"
        assert CAPTCHAProvider.RECAPTCHA_V2 == "recaptcha_v2"
        assert CAPTCHAProvider.RECAPTCHA_V3 == "recaptcha_v3"
        assert CAPTCHAProvider.DATADOME == "datadome"
        assert CAPTCHAProvider.KASADA == "kasada"
        assert CAPTCHAProvider.AKAMAI == "akamai"
        assert CAPTCHAProvider.GENERIC == "generic"

    def test_count(self):
        assert len(CAPTCHAProvider) == 8


class TestStealthHealthItem:
    def test_count(self):
        assert len(StealthHealthItem) >= 7


class TestStealthEventType:
    def test_count(self):
        assert len(StealthEventType) == 6


class TestStealthRisk:
    def test_values(self):
        assert StealthRisk.LOW == "low"
        assert StealthRisk.MEDIUM == "medium"
        assert StealthRisk.HIGH == "high"


# -- Dataclasses --


class TestProxyPoolConfig:
    def test_defaults(self):
        cfg = ProxyPoolConfig()
        assert cfg.tiers == {}
        assert cfg.domain_history_ttl == 3600.0
        assert cfg.retry_delay == 2.0
        assert cfg.max_retries_per_tier == 2

    def test_custom_tiers(self):
        cfg = ProxyPoolConfig(tiers={"standard_residential": "http://proxy:8080"})
        assert "standard_residential" in cfg.tiers


class TestStealthConfig:
    def test_frozen(self):
        cfg = StealthConfig()
        with pytest.raises(AttributeError):
            cfg.headless = True

    def test_defaults(self):
        cfg = StealthConfig()
        assert cfg.headless is False
        assert cfg.httpmorph_enabled is True
        assert cfg.locale == "en-US"
        assert cfg.viewport_width == 1920
        assert cfg.viewport_height == 1080
        assert cfg.proxy_tier == ProxyTier.DIRECT
        assert cfg.captcha_detection_enabled is True
        assert cfg.captcha_blocking_timeout == 120.0
        assert len(cfg.captcha_selectors) > 0
        assert len(cfg.stealth_check_urls) > 0

    def test_custom(self):
        cfg = StealthConfig(headless=True, locale="de-DE", proxy_tier=ProxyTier.PREMIUM_RESIDENTIAL)
        assert cfg.headless is True
        assert cfg.locale == "de-DE"
        assert cfg.proxy_tier == ProxyTier.PREMIUM_RESIDENTIAL


class TestCAPTCHADetection:
    def test_age_seconds(self):
        det = CAPTCHADetection(captcha_type=CAPTCHAProvider.HCAPTCHA)
        time.sleep(0.05)
        assert det.age_seconds >= 0.04

    def test_defaults(self):
        det = CAPTCHADetection(captcha_type=CAPTCHAProvider.RECAPTCHA_V2)
        assert det.resolved is False
        assert det.resolution_time_ms is None
        assert det.selector is None
        assert det.page_url == ""


class TestEscalationRecord:
    def test_creation(self):
        rec = EscalationRecord(
            domain="example.com",
            from_tier=ProxyTier.DIRECT,
            to_tier=ProxyTier.STANDARD_RESIDENTIAL,
            trigger_status=403,
        )
        assert rec.domain == "example.com"
        assert rec.retry_succeeded is None


class TestStealthDiagnostic:
    def test_creation(self):
        d = StealthDiagnostic(check=StealthHealthItem.WEBDRIVER_UNDEFINED, passed=True, detail="OK")
        assert d.passed is True
        assert d.check == StealthHealthItem.WEBDRIVER_UNDEFINED


class TestStealthHealthReport:
    def test_pass_fail_counts(self):
        checks = [
            StealthDiagnostic(check=StealthHealthItem.WEBDRIVER_UNDEFINED, passed=True),
            StealthDiagnostic(check=StealthHealthItem.CLI_SWITCHES_CLEAN, passed=False),
            StealthDiagnostic(check=StealthHealthItem.TLS_JA4_MATCH, passed=True),
        ]
        report = StealthHealthReport(checks=checks, overall_passed=False)
        assert report.pass_count == 2
        assert report.fail_count == 1

    def test_empty_report(self):
        report = StealthHealthReport()
        assert report.pass_count == 0
        assert report.fail_count == 0


class TestHTTPMorphRequestConfig:
    def test_defaults(self):
        cfg = HTTPMorphRequestConfig(url="https://example.com")
        assert cfg.method == "GET"
        assert cfg.timeout == 30.0
        assert cfg.follow_redirects is True
        assert cfg.max_redirects == 10


class TestHTTPMorphResponse:
    def test_defaults(self):
        resp = HTTPMorphResponse(status_code=200, headers={}, body=b"", url="https://example.com")
        assert resp.proxy_tier_used == ProxyTier.DIRECT
        assert resp.ja4_hash is None
        assert resp.redirect_chain == []
