"""Tests for StealthDiagnostics — health check execution and reporting."""

import asyncio

from super_browser.stealth.diagnostics import run_diagnostics
from super_browser.stealth.types import ProxyTier, StealthConfig, StealthHealthItem


class _FakeCDPResult:
    def __init__(self, value=None):
        self.ok = True
        self.data = {"result": {"value": value}}


class _FakeCDP:
    def __init__(self, webdriver_val=None):
        self._webdriver_val = webdriver_val

    async def send(self, method, params=None):
        if "webdriver" in params.get("expression", ""):
            return _FakeCDPResult(self._webdriver_val)
        return _FakeCDPResult(None)


class TestWebdriverCheck:
    def test_undefined_passes(self):
        cdp = _FakeCDP(webdriver_val=None)

        async def _test():
            report = await run_diagnostics(cdp, StealthConfig())
            wd = [c for c in report.checks if c.check == StealthHealthItem.WEBDRIVER_UNDEFINED][0]
            assert wd.passed is True

        asyncio.run(_test())

    def test_false_passes(self):
        cdp = _FakeCDP(webdriver_val=False)

        async def _test():
            report = await run_diagnostics(cdp, StealthConfig())
            wd = [c for c in report.checks if c.check == StealthHealthItem.WEBDRIVER_UNDEFINED][0]
            assert wd.passed is True

        asyncio.run(_test())

    def test_true_fails(self):
        cdp = _FakeCDP(webdriver_val=True)

        async def _test():
            report = await run_diagnostics(cdp, StealthConfig())
            wd = [c for c in report.checks if c.check == StealthHealthItem.WEBDRIVER_UNDEFINED][0]
            assert wd.passed is False

        asyncio.run(_test())

    def test_none_cdp_fails(self):
        async def _test():
            report = await run_diagnostics(None, StealthConfig())
            wd = [c for c in report.checks if c.check == StealthHealthItem.WEBDRIVER_UNDEFINED][0]
            assert wd.passed is False

        asyncio.run(_test())


class TestCLISwitches:
    def test_clean_args_pass(self):
        cfg = StealthConfig(patchright_args=("--disable-blink-features=AutomationControlled",))

        async def _test():
            report = await run_diagnostics(None, cfg)
            sw = [c for c in report.checks if c.check == StealthHealthItem.CLI_SWITCHES_CLEAN][0]
            assert sw.passed is True

        asyncio.run(_test())

    def test_enable_automation_fails(self):
        cfg = StealthConfig(patchright_args=("--enable-automation",))

        async def _test():
            report = await run_diagnostics(None, cfg)
            sw = [c for c in report.checks if c.check == StealthHealthItem.CLI_SWITCHES_CLEAN][0]
            assert sw.passed is False

        asyncio.run(_test())


class TestTLSJA4:
    def test_graceful_without_httpmorph(self):
        async def _test():
            report = await run_diagnostics(None, StealthConfig())
            tls = [c for c in report.checks if c.check == StealthHealthItem.TLS_JA4_MATCH][0]
            assert tls.passed is True

        asyncio.run(_test())


class TestRuntimeEnable:
    def test_no_cdp_passes(self):
        async def _test():
            report = await run_diagnostics(None, StealthConfig())
            re = [c for c in report.checks if c.check == StealthHealthItem.RUNTIME_ENABLE_ABSENT][0]
            assert re.passed is True

        asyncio.run(_test())


class TestHeadlessMode:
    def test_headed_passes(self):
        cfg = StealthConfig(headless=False)

        async def _test():
            report = await run_diagnostics(None, cfg)
            hm = [c for c in report.checks if c.check == StealthHealthItem.HEADLESS_MODE_NEW][0]
            assert hm.passed is True

        asyncio.run(_test())

    def test_headless_passes_patchright(self):
        cfg = StealthConfig(headless=True)

        async def _test():
            report = await run_diagnostics(None, cfg)
            hm = [c for c in report.checks if c.check == StealthHealthItem.HEADLESS_MODE_NEW][0]
            assert hm.passed is True

        asyncio.run(_test())


class TestProxyCheck:
    def test_direct_passes(self):
        cfg = StealthConfig(proxy_tier=ProxyTier.DIRECT)

        async def _test():
            report = await run_diagnostics(None, cfg)
            px = [c for c in report.checks if c.check == StealthHealthItem.PROXY_ACTIVE][0]
            assert px.passed is True

        asyncio.run(_test())

    def test_proxy_tier_passes(self):
        cfg = StealthConfig(proxy_tier=ProxyTier.PREMIUM_RESIDENTIAL)

        async def _test():
            report = await run_diagnostics(None, cfg)
            px = [c for c in report.checks if c.check == StealthHealthItem.PROXY_ACTIVE][0]
            assert px.passed is True
            assert "premium_residential" in px.detail

        asyncio.run(_test())


class TestOverallReport:
    def test_six_checks_total(self):
        async def _test():
            report = await run_diagnostics(None, StealthConfig())
            assert len(report.checks) == 6

        asyncio.run(_test())

    def test_report_timing(self):
        async def _test():
            report = await run_diagnostics(None, StealthConfig())
            assert report.report_time_ms >= 0

        asyncio.run(_test())
