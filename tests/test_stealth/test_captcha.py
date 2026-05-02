"""Tests for CAPTCHAWatchdog — classification, detection lifecycle, CDP integration."""

import asyncio
import json

import pytest

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import WatchdogEvent
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.types import CAPTCHADetection, CAPTCHAProvider, StealthConfig


def _config(**overrides):
    defaults = dict(
        captcha_detection_enabled=True,
        captcha_selectors=('iframe[src*="challenges.cloudflare.com"]',),
    )
    defaults.update(overrides)
    return StealthConfig(**defaults)


class _FakeCDPResult:
    def __init__(self, value=None):
        self.ok = True
        self.data = {"result": {"value": value}}


class _FakePage:
    def __init__(self, cdp_result=None):
        self.url = "https://example.com"
        self._cdp_result = cdp_result
        self.cdp = self

    async def send(self, method, params=None):
        return _FakeCDPResult(self._cdp_result)


class _FakeEventBus(WatchdogEventBus):
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


class TestClassifyCaptcha:
    def test_cloudflare_from_iframe_url(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("iframe", "https://challenges.cloudflare.com/xxx") == CAPTCHAProvider.CLOUDFLARE_TURNSTILE

    def test_hcaptcha_from_iframe_url(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("iframe", "https://hcaptcha.com/captcha") == CAPTCHAProvider.HCAPTCHA

    def test_recaptcha_v2_from_url(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("iframe", "https://google.com/recaptcha/api2") == CAPTCHAProvider.RECAPTCHA_V2

    def test_recaptcha_v3_enterprise(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("iframe", "https://google.com/recaptcha/enterprise") == CAPTCHAProvider.RECAPTCHA_V3

    def test_datadome(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("iframe", "https://datadome.co/captcha") == CAPTCHAProvider.DATADOME

    def test_kasada(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("div", "https://kasada.io/challenge") == CAPTCHAProvider.KASADA

    def test_akamai(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("div", "https://akamai.com/captcha") == CAPTCHAProvider.AKAMAI

    def test_generic_fallback(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("#captcha", None) == CAPTCHAProvider.GENERIC

    def test_selector_based_cloudflare(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha(".cf-turnstile", None) == CAPTCHAProvider.CLOUDFLARE_TURNSTILE

    def test_selector_based_hcaptcha(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha("div.hcaptcha", None) == CAPTCHAProvider.HCAPTCHA

    def test_selector_based_recaptcha(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.classify_captcha(".g-recaptcha", None) == CAPTCHAProvider.RECAPTCHA_V2


class TestDetectionLifecycle:
    def test_initial_no_detection(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.is_captcha_present is False
        assert wd.detection is None

    def test_initial_encounter_count(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        assert wd.encounter_count == 0


class TestCheckSelectors:
    def test_no_cdp_returns_none(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())

        async def _test():
            result = await wd._check_selectors()
            assert result is None

        asyncio.run(_test())

    def test_cdp_match_returns_selector_url(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        page = _FakePage(cdp_result=json.dumps({"selector": 'iframe[src*="challenges.cloudflare.com"]', "url": "https://challenges.cloudflare.com/xxx"}))
        wd._cdp = page.cdp
        wd._page = page

        async def _test():
            result = await wd._check_selectors()
            assert result is not None
            assert result[0] == 'iframe[src*="challenges.cloudflare.com"]'
            assert "cloudflare.com" in result[1]

        asyncio.run(_test())

    def test_cdp_no_match_returns_none(self):
        wd = CAPTCHAWatchdog(_config(), _FakeEventBus())
        page = _FakePage(cdp_result=None)
        wd._cdp = page.cdp
        wd._page = page

        async def _test():
            result = await wd._check_selectors()
            assert result is None

        asyncio.run(_test())


class TestMonitoringStartStop:
    def test_start_stop_lifecycle(self):
        bus = _FakeEventBus()
        wd = CAPTCHAWatchdog(_config(), bus)

        async def _test():
            await wd.start()
            assert wd._running is True
            await wd.stop()
            assert wd._running is False

        asyncio.run(_test())

    def test_start_with_page(self):
        bus = _FakeEventBus()
        wd = CAPTCHAWatchdog(_config(), bus)
        page = _FakePage()

        async def _test():
            await wd.start(page=page)
            assert wd._page is page
            assert wd._cdp is not None
            await wd.stop()

        asyncio.run(_test())

    def test_detection_disabled_skips_monitoring(self):
        bus = _FakeEventBus()
        cfg = _config(captcha_detection_enabled=False)
        wd = CAPTCHAWatchdog(cfg, bus)

        async def _test():
            await wd.start()
            await asyncio.sleep(0.1)
            assert wd.encounter_count == 0
            await wd.stop()

        asyncio.run(_test())
