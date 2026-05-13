"""Tests for StealthManager — orchestrator lifecycle, delegation, HTTP requests."""

import asyncio

import pytest
from super_browser.security.types import PolicyVerdict
from super_browser.stealth.manager import CaptchaTimeoutError, StealthManager
from super_browser.stealth.types import (
    EscalationRecord,
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthHealthReport,
)


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


class _FakeRoute:
    """Captures route() calls for testing Patchright route interception."""
    def __init__(self):
        self.routes = []

    async def route(self, pattern, handler):
        self.routes.append((pattern, handler))


class _FakeResponse:
    """Simulates a Patchright APIResponse for route.fetch()."""
    def __init__(self, body="<html><head></head><body>Hello</body></html>",
                 content_type="text/html", status=200,
                 extra_headers=None):
        self._body = body
        self.status = status
        self._headers = {"content-type": content_type}
        if extra_headers:
            self._headers.update(extra_headers)

    @property
    def headers(self):
        return self._headers

    async def text(self):
        return self._body


class _FakeRouteContext:
    """Simulates a Patchright Route object passed to the handler."""
    def __init__(self, response=None, fetch_error=None):
        self._response = response or _FakeResponse()
        self._fetch_error = fetch_error
        self.fulfilled = None
        self.fell_back = False

    async def fetch(self):
        if self._fetch_error:
            raise self._fetch_error
        return self._response

    async def fallback(self):
        self.fell_back = True

    async def fulfill(self, **kwargs):
        self.fulfilled = kwargs


class TestInjectInitScripts:
    def test_registers_route_on_patchright_page(self):
        cfg = StealthConfig(custom_init_scripts=(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})",
        ))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            assert len(fake_page.routes) == 1
            assert fake_page.routes[0][0] == "**/*"

        asyncio.run(_test())

    def test_injects_script_into_html_head(self):
        script = "window.__test = true;"
        cfg = StealthConfig(custom_init_scripts=(script,))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            handler = fake_page.routes[0][1]
            route_ctx = _FakeRouteContext()
            await handler(route_ctx)
            assert route_ctx.fulfilled is not None
            body = route_ctx.fulfilled["body"]
            assert script in body
            # Script tag should be inside <head>
            head_end = body.find("</head>")
            script_pos = body.find(script)
            assert script_pos < head_end

        asyncio.run(_test())

    def test_strips_csp_headers(self):
        cfg = StealthConfig(custom_init_scripts=("console.log('x');",))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            handler = fake_page.routes[0][1]
            resp = _FakeResponse(
                extra_headers={
                    "content-security-policy": "default-src 'self'",
                    "content-security-policy-report-only": "script-src 'none'",
                }
            )
            route_ctx = _FakeRouteContext(response=resp)
            await handler(route_ctx)
            assert route_ctx.fulfilled is not None
            headers = route_ctx.fulfilled["headers"]
            assert "content-security-policy" not in headers
            assert "content-security-policy-report-only" not in headers

        asyncio.run(_test())

    def test_non_html_passthrough(self):
        cfg = StealthConfig(custom_init_scripts=("console.log('x');",))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            handler = fake_page.routes[0][1]
            resp = _FakeResponse(
                body="var x = 1;",
                content_type="application/javascript",
            )
            route_ctx = _FakeRouteContext(response=resp)
            await handler(route_ctx)
            assert route_ctx.fell_back is True
            assert route_ctx.fulfilled is None

        asyncio.run(_test())

    def test_no_scripts_no_route_registered(self):
        fake_page = _FakeRoute()
        mgr = StealthManager(page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            assert len(fake_page.routes) == 0

        asyncio.run(_test())

    def test_no_page_with_cdp_logs_warning(self):
        cfg = StealthConfig(custom_init_scripts=("console.log('x');",))
        cdp = _FakeCDP()
        mgr = StealthManager(config=cfg, cdp=cdp)

        async def _test():
            # Should not raise; logs warning instead.
            await mgr._inject_init_scripts()
            assert len(cdp.calls) == 0  # No CDP calls made

        asyncio.run(_test())

    def test_multiple_scripts_combined(self):
        cfg = StealthConfig(custom_init_scripts=(
            "window.__a = 1;",
            "window.__b = 2;",
        ))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            handler = fake_page.routes[0][1]
            route_ctx = _FakeRouteContext()
            await handler(route_ctx)
            body = route_ctx.fulfilled["body"]
            assert "window.__a = 1;" in body
            assert "window.__b = 2;" in body

        asyncio.run(_test())

    def test_interception_error_falls_back(self):
        cfg = StealthConfig(custom_init_scripts=("console.log('x');",))
        fake_page = _FakeRoute()
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            await mgr._inject_init_scripts()
            handler = fake_page.routes[0][1]
            route_ctx = _FakeRouteContext(fetch_error=RuntimeError("network error"))
            await handler(route_ctx)
            assert route_ctx.fell_back is True

        asyncio.run(_test())


class TestGrepAddScript:
    """TEST-08-01-01: Verify no addScriptToEvaluateOnNewDocument calls in codebase."""
    def test_no_add_script_to_evaluate(self):
        import os
        import subprocess
        src_dir = os.path.join(
            os.path.dirname(__file__), "..", "..", "src"
        )
        # Match only actual CDP.send() calls, not comments or docstrings.
        # The pattern matches: await ...send("Page.addScriptToEvaluateOnNewDocument"
        result = subprocess.run(
            ["grep", "-r", "send(.*Page.addScriptToEvaluateOnNewDocument", src_dir],
            capture_output=True, text=True,
        )
        # grep returns 1 when no matches found — that's the success condition.
        assert result.returncode != 0, (
            f"Found Page.addScriptToEvaluateOnNewDocument call in src:\n{result.stdout}"
        )


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
