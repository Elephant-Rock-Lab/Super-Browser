"""StealthManager — orchestrator for the multi-layer stealth stack."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from super_browser.stealth.action_policy import StealthActionPolicy
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.diagnostics import run_diagnostics
from super_browser.stealth.proxy import ProxyEscalator
from super_browser.stealth.types import (
    CAPTCHADetection,
    EscalationRecord,
    HTTPMorphRequestConfig,
    HTTPMorphResponse,
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthHealthItem,
    StealthHealthReport,
)

logger = logging.getLogger(__name__)


class CaptchaTimeoutError(Exception):
    pass


class ProxyExhaustedError(Exception):
    pass


class StealthManager:
    """Top-level orchestrator for the multi-layer stealth stack."""

    def __init__(
        self,
        config: Optional[StealthConfig] = None,
        cdp: Any = None,
        event_bus: Any = None,
    ) -> None:
        self._config = config or StealthConfig()
        self._cdp = cdp
        self._event_bus = event_bus
        self._captcha_watchdog = CAPTCHAWatchdog(self._config, event_bus) if event_bus else None
        self._proxy_escalator = ProxyEscalator(self._config)
        self._action_policy = StealthActionPolicy(
            policy_file=self._config.policy_file,
            confirm_callback=self._config.confirm_callback,
        )
        self._initialized = False

    async def initialize(self, session: Any = None) -> None:
        if session:
            if hasattr(session, "_page") and session._page and hasattr(session._page, "cdp"):
                self._cdp = session._page.cdp
            elif hasattr(session, "cdp"):
                self._cdp = session.cdp
        if self._captcha_watchdog and session:
            page = getattr(session, "_page", None) or session
            await self._captcha_watchdog.start(page=page)
        if self._cdp:
            await self._inject_init_scripts()
        self._initialized = True
        logger.info("StealthManager initialized")

    async def shutdown(self) -> None:
        if self._captcha_watchdog:
            await self._captcha_watchdog.stop()
        self._initialized = False
        logger.info("StealthManager shutdown")

    async def __aenter__(self) -> StealthManager:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.shutdown()

    async def http_request(self, config: HTTPMorphRequestConfig) -> HTTPMorphResponse:
        start = time.monotonic()
        domain = self._extract_domain(config.url)
        tier = self._proxy_escalator.recommended_tier(domain)
        proxy_url = self._proxy_escalator.get_proxy_url(tier) or config.proxy_url

        try:
            return await self._do_http_request(config, proxy_url, tier, start)
        except Exception:
            pass

        if self._proxy_escalator.should_escalate(0, domain):
            next_tier = self._proxy_escalator.next_tier(tier)
            if next_tier:
                new_proxy = self._proxy_escalator.get_proxy_url(next_tier)
                self._proxy_escalator.record_escalation(EscalationRecord(
                    domain=domain, from_tier=tier, to_tier=next_tier, trigger_status=0,
                ))
                return await self._do_http_request(config, new_proxy, next_tier, start)

        return HTTPMorphResponse(
            status_code=0, headers={}, body=b"", url=config.url,
            timing_ms=(time.monotonic() - start) * 1000, proxy_tier_used=tier,
        )

    async def _do_http_request(
        self, config: HTTPMorphRequestConfig, proxy_url: Optional[str], tier: ProxyTier, start: float,
    ) -> HTTPMorphResponse:
        try:
            from httpmorph import Client
            client = Client(proxy=proxy_url)
            resp = client.request(config.method, config.url, headers=config.headers or {})
            return HTTPMorphResponse(
                status_code=resp.status_code,
                headers=dict(resp.headers),
                body=resp.content,
                url=str(resp.url),
                timing_ms=(time.monotonic() - start) * 1000,
                proxy_tier_used=tier,
            )
        except ImportError:
            import urllib.request
            req = urllib.request.Request(config.url, method=config.method, data=config.body)
            if config.headers:
                for k, v in config.headers.items():
                    req.add_header(k, v)
            if proxy_url:
                handler = urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
                opener = urllib.request.build_opener(handler)
                resp = opener.open(req, timeout=config.timeout)
            else:
                resp = urllib.request.urlopen(req, timeout=config.timeout)
            return HTTPMorphResponse(
                status_code=resp.status,
                headers=dict(resp.headers),
                body=resp.read(),
                url=resp.url,
                timing_ms=(time.monotonic() - start) * 1000,
                proxy_tier_used=tier,
            )

    def current_captcha(self) -> Optional[CAPTCHADetection]:
        if self._captcha_watchdog:
            return self._captcha_watchdog.detection
        return None

    async def wait_for_captcha_resolution(self, timeout: Optional[float] = None) -> CAPTCHADetection:
        if not self._captcha_watchdog:
            raise CaptchaTimeoutError("No watchdog configured")
        deadline = time.monotonic() + (timeout or self._config.captcha_blocking_timeout)
        while time.monotonic() < deadline:
            det = self._captcha_watchdog.detection
            if det is None or det.resolved:
                if det and det.resolved:
                    return det
                raise CaptchaTimeoutError("CAPTCHA resolved or disappeared")
            await asyncio.sleep(0.5)
        raise CaptchaTimeoutError(f"CAPTCHA not resolved within {timeout or self._config.captcha_blocking_timeout}s")

    @property
    def captcha_encounter_count(self) -> int:
        if self._captcha_watchdog:
            return self._captcha_watchdog.encounter_count
        return 0

    def evaluate_action(self, action: str, url: str) -> Any:
        return self._action_policy.evaluate(action, url)

    def current_proxy_tier(self, domain: Optional[str] = None) -> ProxyTier:
        if domain:
            return self._proxy_escalator.recommended_tier(domain)
        return self._config.proxy_tier

    def escalation_history(self, domain: Optional[str] = None) -> list[EscalationRecord]:
        return self._proxy_escalator.escalation_history(domain)

    async def run_diagnostics(self) -> StealthHealthReport:
        return await run_diagnostics(self._cdp, self._config)

    async def validate_stealth_site(self, url: str) -> StealthDiagnostic:
        if not self._cdp:
            return StealthDiagnostic(
                check=StealthHealthItem.WEBDRIVER_UNDEFINED,
                passed=False,
                detail="No CDP session for site validation",
            )
        try:
            await self._cdp.send("Page.navigate", {"url": url})
            await asyncio.sleep(2)
            result = await self._cdp.send("Runtime.evaluate", {
                "expression": "navigator.webdriver",
                "returnByValue": True,
            })
            val = None
            if result.ok and result.data:
                val = result.data.get("result", {}).get("value")
            passed = val is None or val is False or val == "undefined"
            return StealthDiagnostic(
                check=StealthHealthItem.WEBDRIVER_UNDEFINED,
                passed=passed,
                detail=f"Site {url}: webdriver={val!r}",
            )
        except Exception as exc:
            return StealthDiagnostic(
                check=StealthHealthItem.WEBDRIVER_UNDEFINED,
                passed=False,
                detail=f"Site validation failed: {exc}",
            )

    async def _inject_init_scripts(self) -> None:
        for script in self._config.custom_init_scripts:
            try:
                await self._cdp.send("Page.addScriptToEvaluateOnNewDocument", {"source": script})
                logger.debug("Injected init script (%d bytes)", len(script))
            except Exception as exc:
                logger.warning("Failed to inject init script: %s", exc)

    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse
        try:
            return urlparse(url).hostname or ""
        except Exception:
            return ""

    @property
    def config(self) -> StealthConfig:
        return self._config

    @property
    def proxy_escalator(self) -> ProxyEscalator:
        return self._proxy_escalator

    @property
    def action_policy(self) -> StealthActionPolicy:
        return self._action_policy
