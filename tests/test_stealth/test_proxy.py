"""Tests for ProxyEscalator — tier progression, domain memory, history."""

import time

import pytest

from super_browser.stealth.proxy import ProxyEscalator
from super_browser.stealth.types import EscalationRecord, ProxyPoolConfig, ProxyTier, StealthConfig


def _config(**overrides):
    pool = overrides.pop("pool", None)
    defaults = dict(
        proxy_tier=ProxyTier.DIRECT,
        proxy_config=pool or ProxyPoolConfig(),
        max_escalation_level=3,
        escalation_status_codes=(401, 403, 429),
    )
    defaults.update(overrides)
    return StealthConfig(**defaults)


class TestShouldEscalate:
    def test_403_triggers_escalation(self):
        esc = ProxyEscalator(_config())
        assert esc.should_escalate(403, "example.com") is True

    def test_401_triggers_escalation(self):
        esc = ProxyEscalator(_config())
        assert esc.should_escalate(401, "example.com") is True

    def test_429_triggers_escalation(self):
        esc = ProxyEscalator(_config())
        assert esc.should_escalate(429, "example.com") is True

    def test_200_does_not_escalate(self):
        esc = ProxyEscalator(_config())
        assert esc.should_escalate(200, "example.com") is False

    def test_404_does_not_escalate(self):
        esc = ProxyEscalator(_config())
        assert esc.should_escalate(404, "example.com") is False

    def test_already_at_max_tier(self):
        cfg = _config(proxy_tier=ProxyTier.DATACENTER_TLS)
        esc = ProxyEscalator(cfg)
        assert esc.should_escalate(403, "example.com") is False


class TestNextTier:
    def test_direct_to_standard(self):
        esc = ProxyEscalator(_config())
        assert esc.next_tier(ProxyTier.DIRECT) == ProxyTier.STANDARD_RESIDENTIAL

    def test_standard_to_premium(self):
        esc = ProxyEscalator(_config())
        assert esc.next_tier(ProxyTier.STANDARD_RESIDENTIAL) == ProxyTier.PREMIUM_RESIDENTIAL

    def test_premium_to_datacenter(self):
        esc = ProxyEscalator(_config())
        assert esc.next_tier(ProxyTier.PREMIUM_RESIDENTIAL) == ProxyTier.DATACENTER_TLS

    def test_max_tier_returns_none(self):
        esc = ProxyEscalator(_config())
        assert esc.next_tier(ProxyTier.DATACENTER_TLS) is None

    def test_limited_max_escalation(self):
        cfg = _config(max_escalation_level=1)
        esc = ProxyEscalator(cfg)
        assert esc.next_tier(ProxyTier.STANDARD_RESIDENTIAL) is None


class TestGetProxyUrl:
    def test_direct_returns_none(self):
        esc = ProxyEscalator(_config())
        assert esc.get_proxy_url(ProxyTier.DIRECT) is None

    def test_configured_tier_returns_url(self):
        pool = ProxyPoolConfig(tiers={"standard_residential": "http://proxy:8080"})
        esc = ProxyEscalator(_config(pool=pool))
        assert esc.get_proxy_url(ProxyTier.STANDARD_RESIDENTIAL) == "http://proxy:8080"

    def test_unconfigured_tier_returns_none(self):
        esc = ProxyEscalator(_config())
        assert esc.get_proxy_url(ProxyTier.STANDARD_RESIDENTIAL) is None


class TestDomainMemory:
    def test_recommended_tier_default(self):
        esc = ProxyEscalator(_config())
        assert esc.recommended_tier("example.com") == ProxyTier.DIRECT

    def test_escalation_records_tier(self):
        esc = ProxyEscalator(_config())
        rec = EscalationRecord(
            domain="example.com",
            from_tier=ProxyTier.DIRECT,
            to_tier=ProxyTier.STANDARD_RESIDENTIAL,
            trigger_status=403,
        )
        esc.record_escalation(rec)
        assert esc.recommended_tier("example.com") == ProxyTier.STANDARD_RESIDENTIAL

    def test_ttl_expiry(self):
        pool = ProxyPoolConfig(domain_history_ttl=0.01)
        esc = ProxyEscalator(_config(pool=pool))
        rec = EscalationRecord(
            domain="example.com",
            from_tier=ProxyTier.DIRECT,
            to_tier=ProxyTier.STANDARD_RESIDENTIAL,
            trigger_status=403,
        )
        esc.record_escalation(rec)
        time.sleep(0.02)
        assert esc.recommended_tier("example.com") == ProxyTier.DIRECT

    def test_current_tier_alias(self):
        esc = ProxyEscalator(_config())
        assert esc.current_tier_for_domain("example.com") == esc.recommended_tier("example.com")


class TestHistory:
    def test_empty_history(self):
        esc = ProxyEscalator(_config())
        assert esc.escalation_history() == []
        assert esc.escalation_count == 0

    def test_record_and_filter(self):
        esc = ProxyEscalator(_config())
        r1 = EscalationRecord("a.com", ProxyTier.DIRECT, ProxyTier.STANDARD_RESIDENTIAL, 403)
        r2 = EscalationRecord("b.com", ProxyTier.DIRECT, ProxyTier.PREMIUM_RESIDENTIAL, 401)
        esc.record_escalation(r1)
        esc.record_escalation(r2)
        assert esc.escalation_count == 2
        assert len(esc.escalation_history("a.com")) == 1
        assert len(esc.escalation_history("b.com")) == 1
        assert len(esc.escalation_history()) == 2

    def test_clear_history(self):
        esc = ProxyEscalator(_config())
        esc.record_escalation(EscalationRecord("x.com", ProxyTier.DIRECT, ProxyTier.STANDARD_RESIDENTIAL, 403))
        count = esc.clear_history()
        assert count == 1
        assert esc.escalation_count == 0
        assert esc.recommended_tier("x.com") == ProxyTier.DIRECT
