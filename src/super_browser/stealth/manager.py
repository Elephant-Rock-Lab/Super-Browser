"""StealthManager — orchestrator for the multi-layer stealth stack."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from super_browser.stealth.action_policy import StealthActionPolicy
from super_browser.stealth.captcha import CAPTCHAWatchdog
from super_browser.stealth.consistency import (
    InjectDelivery,
    derive_matrix,
    generate_inject,
)
from super_browser.stealth.diagnostics import run_diagnostics
from super_browser.stealth.headers import HeaderRandomizer
from super_browser.stealth.profiles import load_profile
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
from super_browser.stealth.user_agent_pool import UserAgentPool

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
        page: Any = None,
        stealth_bridge: Any = None,
    ) -> None:
        self._config = config or StealthConfig()
        self._stealth_bridge = stealth_bridge
        self._cdp = cdp
        self._event_bus = event_bus
        self._page = page
        self._captcha_watchdog = CAPTCHAWatchdog(self._config, event_bus) if event_bus else None
        self._proxy_escalator = ProxyEscalator(self._config)
        self._action_policy = StealthActionPolicy(
            policy_file=self._config.policy_file,
            confirm_callback=self._config.confirm_callback,
        )
        self._header_randomizer = HeaderRandomizer()
        self._ua_pool: Optional[UserAgentPool] = None
        self._inject_delivery: Optional[InjectDelivery] = None
        self._initialized = False

    async def initialize(self, session: Any = None) -> None:
        if session:
            if hasattr(session, "_page") and session._page:
                if hasattr(session._page, "engine_page"):
                    # PageHandle — use engine_page (protocol-compliant).
                    self._page = session._page.engine_page
                    # Prefer StealthBridge from engine_page.
                    if self._stealth_bridge is None:
                        self._stealth_bridge = getattr(
                            session._page.engine_page, "stealth_bridge", None,
                        )
                    # Fallback: CDPBridge from engine_page.
                    if self._cdp is None and hasattr(session._page, "cdp"):
                        self._cdp = session._page.cdp
                elif hasattr(session._page, "backend_page") or hasattr(session._page, "raw_page"):
                    # Fallback — raw Playwright Page (backend_page or legacy raw_page).
                    self._page = getattr(session._page, "backend_page", None) or getattr(session._page, "raw_page", None)
                elif hasattr(session._page, "cdp"):
                    self._cdp = session._page.cdp
            elif hasattr(session, "cdp"):
                self._cdp = session.cdp
        if self._captcha_watchdog and session:
            page = getattr(session, "_page", None) or session
            await self._captcha_watchdog.start(page=page)

        # ── Consistency engine path ────────────────────────────────
        consistency_cfg = getattr(
            getattr(session, "_config", None), "consistency", None
        ) if session else None
        # Also check if a Config was passed via StealthConfig
        if consistency_cfg is None:
            consistency_cfg = _detect_consistency_config()

        if consistency_cfg is not None and consistency_cfg.enabled:
            await self._initialize_consistency(consistency_cfg)
        else:
            # Legacy path — UA pool + route-based init scripts.
            if self._page or self._cdp:
                await self._inject_init_scripts()

        self._initialized = True
        logger.info("StealthManager initialized")

    def randomize_headers(self, *, is_json: bool = False) -> dict[str, str]:
        """Return a fresh set of randomised HTTP headers.

        Call this before each navigation request to vary the browser
        fingerprint.
        """
        return self._header_randomizer.randomize_all(is_json=is_json)

    def get_user_agent(self) -> str:
        """Return the next user-agent string from the UA pool.

        Lazily initialises the pool on first call.
        """
        if self._ua_pool is None:
            self._ua_pool = UserAgentPool()
        return self._ua_pool.get_next()

    @property
    def ua_pool(self) -> Optional[UserAgentPool]:
        """The underlying UserAgentPool (``None`` until first accessed)."""
        return self._ua_pool

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
        bridge = self._stealth_bridge or self._cdp
        return await run_diagnostics(bridge, self._config)

    async def validate_stealth_site(self, url: str) -> StealthDiagnostic:
        bridge = self._stealth_bridge or self._cdp
        if not bridge:
            return StealthDiagnostic(
                check=StealthHealthItem.WEBDRIVER_UNDEFINED,
                passed=False,
                detail="No CDP session for site validation",
            )
        try:
            await self._send(bridge, "Page.navigate", {"url": url})
            await asyncio.sleep(2)
            result = await self._send(bridge, "Runtime.evaluate", {
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
        """Inject stealth init scripts via Patchright route interception.

        Instead of using Page.addScriptToEvaluateOnNewDocument (which conflicts
        with Patchright's internal patches), we intercept HTML responses and
        prepend stealth scripts into the page content before the browser parses
        it.  We also strip restrictive CSP headers that would block injection.
        """
        scripts = self._config.custom_init_scripts
        if not scripts:
            return

        # Build a single <script> block from all init scripts.
        combined = "\n".join(scripts)
        script_tag = (
            f"<script>\n{combined}\n</script>"
        )

        _manager_ref = self  # closure reference

        async def _intercept(route: Any) -> None:
            try:
                response = await route.fetch()
                content_type = response.headers.get("content-type", "")

                if "text/html" not in content_type:
                    await route.fallback()
                    return

                body = await response.text()
                # Strip restrictive CSP headers from the response.
                headers = dict(response.headers)
                for csp_key in ("content-security-policy",
                                "content-security-policy-report-only"):
                    headers.pop(csp_key, None)
                    # Also handle title-case variants.
                    headers.pop(csp_key.replace("-", "-"), None)

                # Inject stealth script as the first element in <head>.
                if "<head" in body:
                    body = body.replace("<head", "<head", 1)
                    # Find the closing '>' of the <head> tag.
                    head_close = body.find(">", body.find("<head"))
                    if head_close != -1:
                        body = body[: head_close + 1] + script_tag + body[head_close + 1 :]
                elif "<html" in body:
                    # Fallback: inject before </html>.
                    body = body.replace("</html>", f"{script_tag}</html>", 1)
                else:
                    # No HTML structure — wrap entirely.
                    body = f"<html><head>{script_tag}</head><body>{body}</body></html>"

                _manager_ref._log_injection(len(body))
                await route.fulfill(
                    response=response.status,
                    headers=headers,
                    body=body,
                )
            except Exception as exc:
                logger.warning("Route interception failed, falling back: %s", exc)
                await route.fallback()

        # Register route interception on the Patchright page.
        target = self._page
        if target is None and self._cdp is not None:
            logger.warning(
                "No Patchright page available for route interception; "
                "init scripts will not be injected."
            )
            return

        await target.route("**/*", _intercept)
        logger.info(
            "Stealth route interception registered (%d init scripts)",
            len(scripts),
        )

    @staticmethod
    def _log_injection(body_size: int) -> None:
        logger.debug("Injected stealth scripts via route interception (body %d bytes)", body_size)

    @staticmethod
    def _extract_domain(url: str) -> str:
        from urllib.parse import urlparse
        try:
            return urlparse(url).hostname or ""
        except Exception:
            return ""

    async def _initialize_consistency(self, consistency_cfg: Any) -> None:
        """Load profile → derive_matrix → generate_inject → install delivery."""
        profile_id = consistency_cfg.profile_id
        if profile_id is None:
            profile_id = _detect_host_profile()
            logger.info("Auto-detected host profile: %s", profile_id)

        try:
            profile = load_profile(profile_id)
        except Exception as exc:
            logger.warning(
                "Failed to load profile %r: %s — falling back to legacy path",
                profile_id, exc,
            )
            if self._page or self._cdp:
                await self._inject_init_scripts()
            return

        matrix = derive_matrix(profile, consistency_cfg.seed)
        js_payload = generate_inject(matrix)

        self._inject_delivery = InjectDelivery(js_payload)

        if self._stealth_bridge or self._cdp or self._page:
            await self._inject_delivery.install(
                stealth_bridge=self._stealth_bridge,
                cdp_bridge=self._cdp,
                page=self._page,
            )
        else:
            logger.warning(
                "No CDP/page available for inject delivery; "
                "consistency engine payloads will not be injected."
            )

        logger.info(
            "Consistency engine active (profile=%s, seed=%s, %d bytes JS)",
            profile_id, consistency_cfg.seed, len(js_payload),
        )

    @property
    def config(self) -> StealthConfig:
        return self._config

    @property
    def proxy_escalator(self) -> ProxyEscalator:
        return self._proxy_escalator

    @property
    def action_policy(self) -> StealthActionPolicy:
        return self._action_policy

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _send(bridge: Any, method: str, params: dict) -> Any:
        """Dispatch a CDP command via stealth_bridge.cdp_send or cdp.send."""
        if hasattr(bridge, "cdp_send"):
            return bridge.cdp_send(method, params)
        return bridge.send(method, params)


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _detect_host_profile() -> str:
    """Auto-detect the best device profile for the current host OS.

    Returns one of the standard profile IDs or falls back to
    ``"windows-chrome-stable"``.
    """
    import platform

    system = platform.system().lower()
    if system == "darwin":
        machine = platform.machine().lower()
        if "arm" in machine or "aarch" in machine:
            return "macos-m4-chrome-stable"
        return "macos-chrome-stable"
    if system == "linux":
        return "linux-chrome-stable"
    return "windows-chrome-stable"


def _detect_consistency_config() -> Any:
    """Try to find a ConsistencyConfig from the importable config module."""
    try:
        from super_browser.config import ConsistencyConfig
        return ConsistencyConfig()
    except ImportError:
        return None
