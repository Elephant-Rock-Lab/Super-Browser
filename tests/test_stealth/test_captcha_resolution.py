"""Tests for CAPTCHAWatchdog.resolve_captcha() — BATCH-10 TASK-01.

TEST-10-01-01 through TEST-10-01-05.
"""

import asyncio
import time

import pytest

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.types import (
    CAPTCHADetection,
    CAPTCHAProvider,
    CAPTCHAResolution,
    StealthConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
    """Fake page that supports wait_for_selector / click / CDP send."""

    def __init__(self, *, cdp_value=None, click_success=True):
        self.url = "https://example.com"
        self._cdp_value = cdp_value
        self._click_success = click_success
        self._clicked_selectors: list[str] = []
        self.cdp = self

    async def send(self, method, params=None):
        return _FakeCDPResult(self._cdp_value)

    async def wait_for_selector(self, selector, timeout=5000):
        """Return a fake element handle that records clicks."""
        el = _FakeElement(self._click_success)
        return el

    async def query_selector(self, selector):
        return _FakeElement(self._click_success)


class _FakeElement:
    def __init__(self, success=True):
        self._success = success

    async def click(self):
        if not self._success:
            raise RuntimeError("click failed")


class _FakeEventBus(WatchdogEventBus):
    def __init__(self):
        self.events = []

    async def emit(self, event):
        self.events.append(event)


def _make_watchdog(
    provider: CAPTCHAProvider,
    *,
    cdp_value=None,
    click_success=True,
) -> CAPTCHAWatchdog:
    """Create a watchdog with a pre-set detection of the given provider."""
    bus = _FakeEventBus()
    cfg = _config()
    wd = CAPTCHAWatchdog(cfg, bus)
    page = _FakePage(cdp_value=cdp_value, click_success=click_success)
    wd._page = page
    wd._cdp = page.cdp
    wd._detection = CAPTCHADetection(
        captcha_type=provider,
        selector="iframe",
        iframe_url="https://example.com/captcha",
        page_url="https://example.com",
    )
    return wd


# ---------------------------------------------------------------------------
# TEST-10-01-01: Turnstile — clicks challenge iframe, waits for callback
# ---------------------------------------------------------------------------

class TestResolveTurnstile:
    def test_turnstile_clicks_and_waits_for_callback(self):
        """TEST-10-01-01: Turnstile resolution clicks iframe, waits for cf-turnstile-response."""
        wd = _make_watchdog(
            CAPTCHAProvider.CLOUDFLARE_TURNSTILE,
            cdp_value=True,  # JS poll returns True immediately
        )

        async def _test():
            result = await wd.resolve_captcha()
            assert isinstance(result, CAPTCHAResolution)
            assert result.resolved is True
            assert "cloudflare_turnstile" in result.strategy
            assert result.duration_ms >= 0

        asyncio.run(_test())

    def test_turnstile_fails_when_no_response(self):
        wd = _make_watchdog(
            CAPTCHAProvider.CLOUDFLARE_TURNSTILE,
            cdp_value=False,  # JS poll never returns True
        )
        # Override the CDP send to return False consistently (timeout quickly)
        original_send = wd._cdp.send  # noqa: F841

        async def _fast_false_send(method, params=None):
            return _FakeCDPResult(False)

        wd._cdp.send = _fast_false_send

        async def _test():
            # Patch _poll_js_true timeout to be very short for test speed
            result = await wd.resolve_captcha()
            assert result.resolved is False
            assert "cloudflare_turnstile" in result.strategy

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-01-02: reCAPTCHA v2 — clicks checkbox, waits for success
# ---------------------------------------------------------------------------

class TestResolveRecaptchaV2:
    def test_recaptcha_v2_clicks_checkbox_waits(self):
        """TEST-10-01-02: reCAPTCHA v2 clicks .recaptcha-checkbox, waits for success."""
        wd = _make_watchdog(
            CAPTCHAProvider.RECAPTCHA_V2,
            cdp_value=True,
        )

        async def _test():
            result = await wd.resolve_captcha()
            assert isinstance(result, CAPTCHAResolution)
            assert result.resolved is True
            assert "recaptcha_v2" in result.strategy

        asyncio.run(_test())

    def test_recaptcha_v2_fails_without_page(self):
        wd = _make_watchdog(CAPTCHAProvider.RECAPTCHA_V2, cdp_value=True)
        wd._page = None  # remove page

        async def _test():
            result = await wd.resolve_captcha()
            assert result.resolved is False

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-01-03: hCaptcha — clicks checkbox, waits
# ---------------------------------------------------------------------------

class TestResolveHcaptcha:
    def test_hcaptcha_clicks_checkbox_waits(self):
        """TEST-10-01-03: hCaptcha clicks checkbox in iframe, waits for completion."""
        wd = _make_watchdog(
            CAPTCHAProvider.HCAPTCHA,
            cdp_value=True,
        )

        async def _test():
            result = await wd.resolve_captcha()
            assert isinstance(result, CAPTCHAResolution)
            assert result.resolved is True
            assert "hcaptcha" in result.strategy

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-01-04: Generic — waits and retries, no crash
# ---------------------------------------------------------------------------

class TestResolveGeneric:
    def test_generic_waits_and_retries(self):
        """TEST-10-01-04: Generic resolution waits 5s and re-checks, no crash."""
        wd = _make_watchdog(
            CAPTCHAProvider.GENERIC,
            cdp_value=None,  # _check_selectors returns None → resolved
        )
        # Override _check_selectors to return None (CAPTCHA gone)
        async def _check_none():
            return None
        wd._check_selectors = _check_none

        async def _test():
            t0 = time.monotonic()
            result = await wd.resolve_captcha()
            elapsed = (time.monotonic() - t0)
            # Should have waited ~5 seconds
            assert result.resolved is True
            assert "generic" in result.strategy
            assert elapsed >= 4.5  # allow small timing wiggle

        asyncio.run(_test())

    def test_generic_fails_if_captcha_persists(self):
        wd = _make_watchdog(CAPTCHAProvider.GENERIC)

        async def _check_persists():
            return ("iframe", "https://example.com/captcha")
        wd._check_selectors = _check_persists

        async def _test():
            result = await wd.resolve_captcha()
            assert result.resolved is False

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-10-01-05: Encounter count tracked across resolve attempts
# ---------------------------------------------------------------------------

class TestEncounterCountTracking:
    def test_encounter_count_preserved_after_resolve(self):
        """TEST-10-01-05: Encounter count is tracked across resolve attempts."""
        bus = _FakeEventBus()
        cfg = _config()
        wd = CAPTCHAWatchdog(cfg, bus)
        wd._detection = CAPTCHADetection(
            captcha_type=CAPTCHAProvider.RECAPTCHA_V3,
        )
        wd._encounter_count = 3

        async def _test():
            result = await wd.resolve_captcha()
            # V3 always resolves (just waits)
            assert result.resolved is True
            # Encounter count should still be 3
            assert wd.encounter_count == 3

        asyncio.run(_test())

    def test_no_detection_returns_unresolved(self):
        bus = _FakeEventBus()
        cfg = _config()
        wd = CAPTCHAWatchdog(cfg, bus)
        # No detection set

        async def _test():
            result = await wd.resolve_captcha()
            assert result.resolved is False
            assert result.strategy == "none"
            assert result.duration_ms == 0.0

        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Additional: External-solver providers return unresolved
# ---------------------------------------------------------------------------

class TestExternalSolverProviders:
    @pytest.mark.parametrize("provider", [
        CAPTCHAProvider.DATADOME,
        CAPTCHAProvider.KASADA,
        CAPTCHAProvider.AKAMAI,
    ])
    def test_external_solver_returns_unresolved(self, provider):
        """DATADOME/KASADA/AKAMAI log warning and return unresolved (v2.0)."""
        wd = _make_watchdog(provider)

        async def _test():
            result = await wd.resolve_captcha()
            assert result.resolved is False
            assert provider.value in result.strategy

        asyncio.run(_test())
