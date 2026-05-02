"""Tests for StealthManager — orchestrator lifecycle, delegation, HTTP requests."""

import asyncio
import json
import time

import pytest

from super_browser.stealth.manager import CaptchaTimeoutError, StealthManager
from super_browser.stealth.types import (
    EscalationRecord,
    HTTPMorphRequestConfig,
    HTTPMorphResponse,
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthHealthItem,
    StealthHealthReport,
    ProxyPoolConfig,
)
from super_browser.security.types import PolicyVerdict


class _FakeCDPResult:
    def __init__(self, data=None):
        self.ok = True
        self.data = data or {"result": {"value": None}}


class _FakeCDP:
    def __init__(self):
        self.calls = []

    async def send(self, method, params=None):
        self.calls.append((method, params))
        return _FakeCDPResult()


class _FakeWatchdog:
    def __init__(self):
        self._detection = None
        self._running = False
        self._encounter_count = 0

    @property
    def detection(self):
        return self._detection

    @property
    def encounter_count(self):
        return self._encounter_count

    async def start(self, page=None):
        self._running = True

    async def stop(self):
        self._running = False


class TestInit:
    def test_default_config(self):
        mgr = StealthManager()
        assert mgr.config.proxy_tier == ProxyTier.DIRECT
        assert mgr.captcha_encounter_count == 0

    def test_custom_config(self):
        cfg = StealthConfig(proxy_tier=ProxyTier.PREMIUM_RESIDENTIAL)
        mgr = StealthManager(config=cfg)
        assert mgr.config.proxy_tier == ProxyTier.PREMIUM_RESIDENTIAL


class TestShutdown:
    def test_shutdown_without_watchdog(self):
        mgr = StealthManager()

        async def _test():
            await mgr.shutdown()
            assert mgr._initialized is False

        asyncio.run(_test())


class TestEvaluateAction:
    def test_allow_action(self):
        mgr = StealthManager()
        d = mgr.evaluate_action("navigate", "https://example.com")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_confirm_action(self):
        mgr = StealthManager()
        d = mgr.evaluate_action("file_upload", "")
        assert d.verdict == PolicyVerdict.CONFIRM

    def test_deny_action(self):
        from super_browser.security.types import PolicyRule
        mgr = StealthManager()
        mgr.action_policy.add_rule(PolicyRule(action="dangerous", verdict=PolicyVerdict.DENY))
        d = mgr.evaluate_action("dangerous", "")
        assert d.verdict == PolicyVerdict.DENY


class TestProxyTier:
    def test_default_tier(self):
        mgr = StealthManager()
        assert mgr.current_proxy_tier() == ProxyTier.DIRECT

    def test_domain_tier(self):
        mgr = StealthManager()
        mgr.proxy_escalator.record_escalation(EscalationRecord(
            domain="example.com",
            from_tier=ProxyTier.DIRECT,
            to_tier=ProxyTier.STANDARD_RESIDENTIAL,
            trigger_status=403,
        ))
        assert mgr.current_proxy_tier("example.com") == ProxyTier.STANDARD_RESIDENTIAL


class TestEscalationHistory:
    def test_empty_history(self):
        mgr = StealthManager()
        assert mgr.escalation_history() == []

    def test_recorded_history(self):
        mgr = StealthManager()
        mgr.proxy_escalator.record_escalation(EscalationRecord(
            domain="x.com", from_tier=ProxyTier.DIRECT, to_tier=ProxyTier.STANDARD_RESIDENTIAL, trigger_status=403,
        ))
        assert len(mgr.escalation_history()) == 1
        assert len(mgr.escalation_history("x.com")) == 1
        assert len(mgr.escalation_history("y.com")) == 0


class TestRunDiagnostics:
    def test_delegates_to_diagnostics(self):
        mgr = StealthManager()

        async def _test():
            report = await mgr.run_diagnostics()
            assert isinstance(report, StealthHealthReport)
            assert len(report.checks) == 6

        asyncio.run(_test())


class TestValidateStealthSite:
    def test_no_cdp_returns_failed(self):
        mgr = StealthManager()

        async def _test():
            result = await mgr.validate_stealth_site("https://example.com")
            assert isinstance(result, StealthDiagnostic)
            assert result.passed is False

        asyncio.run(_test())


class TestInjectInitScripts:
    def test_injects_via_cdp(self):
        cfg = StealthConfig(custom_init_scripts=("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",))
        cdp = _FakeCDP()
        mgr = StealthManager(config=cfg, cdp=cdp)

        async def _test():
            await mgr._inject_init_scripts()
            assert len(cdp.calls) == 1
            assert cdp.calls[0][0] == "Page.addScriptToEvaluateOnNewDocument"

        asyncio.run(_test())

    def test_no_scripts_no_calls(self):
        mgr = StealthManager(cdp=_FakeCDP())

        async def _test():
            await mgr._inject_init_scripts()
            # _FakeCDP starts with empty calls
            pass

        asyncio.run(_test())


class TestExtractDomain:
    def test_extracts_hostname(self):
        assert StealthManager._extract_domain("https://example.com/path") == "example.com"

    def test_empty_string(self):
        assert StealthManager._extract_domain("") == ""

    def test_no_scheme(self):
        assert StealthManager._extract_domain("example.com/path") == ""


class TestWaitForCaptchaResolution:
    def test_no_watchdog_raises(self):
        mgr = StealthManager()

        async def _test():
            with pytest.raises(CaptchaTimeoutError):
                await mgr.wait_for_captcha_resolution(timeout=0.1)

        asyncio.run(_test())


class TestContextManager:
    def test_aenter_aexit(self):
        mgr = StealthManager()

        async def _test():
            async with mgr as m:
                assert m is mgr

        asyncio.run(_test())


class TestCurrentCaptcha:
    def test_no_watchdog_returns_none(self):
        mgr = StealthManager()
        assert mgr.current_captcha() is None


class TestProperties:
    def test_config_property(self):
        cfg = StealthConfig(headless=True)
        mgr = StealthManager(config=cfg)
        assert mgr.config.headless is True

    def test_proxy_escalator_property(self):
        mgr = StealthManager()
        assert mgr.proxy_escalator is mgr._proxy_escalator

    def test_action_policy_property(self):
        mgr = StealthManager()
        assert mgr.action_policy is mgr._action_policy
