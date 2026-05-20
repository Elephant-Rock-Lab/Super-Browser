"""CAPTCHAWatchdog — CDP event-driven CAPTCHA detection and classification."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import WatchdogEvent
from super_browser.recovery.watchdogs import BaseWatchdog
from super_browser.stealth.types import (
    CAPTCHADetection,
    CAPTCHAProvider,
    CAPTCHAResolution,
    StealthConfig,
)

logger = logging.getLogger(__name__)

_CAPTCHA_PATTERNS: list[tuple[str, CAPTCHAProvider]] = [
    ("challenges.cloudflare.com", CAPTCHAProvider.CLOUDFLARE_TURNSTILE),
    ("hcaptcha.com", CAPTCHAProvider.HCAPTCHA),
    ("google.com/recaptcha", CAPTCHAProvider.RECAPTCHA_V2),
    ("recaptcha.net", CAPTCHAProvider.RECAPTCHA_V2),
    ("datadome.co", CAPTCHAProvider.DATADOME),
    ("kasada", CAPTCHAProvider.KASADA),
    ("akamai", CAPTCHAProvider.AKAMAI),
]


class CAPTCHAWatchdog(BaseWatchdog):
    """Monitors for CAPTCHA insertion via CDP events and selector polling."""

    LISTENS_TO: list[WatchdogEvent] = []
    EMITS: list[WatchdogEvent] = [WatchdogEvent.CAPTCHA_DETECTED]

    def __init__(self, config: StealthConfig, event_bus: WatchdogEventBus) -> None:
        super().__init__(event_bus)
        self._config = config
        self._detection: Optional[CAPTCHADetection] = None
        self._encounter_count = 0
        self._cdp: Any = None
        self._page: Any = None

    async def start(self, page: Any = None) -> None:
        self._page = page
        if page and hasattr(page, "engine_page"):
            engine_pg = page.engine_page
            stealth_bridge = getattr(engine_pg, "stealth_bridge", None)
            if stealth_bridge is not None:
                self._cdp = stealth_bridge
            elif hasattr(page, "cdp"):
                self._cdp = page.cdp
        elif page and hasattr(page, "cdp"):
            self._cdp = page.cdp
        await super().start()

    async def _monitoring_loop(self) -> None:
        if not self._config.captcha_detection_enabled:
            return
        poll_interval = 1.0
        while self._running:
            try:
                result = await self._check_selectors()
                if result and self._detection is None:
                    selector, url = result
                    captcha_type = self.classify_captcha(selector, url)
                    self._detection = CAPTCHADetection(
                        captcha_type=captcha_type,
                        selector=selector,
                        iframe_url=url,
                        page_url=getattr(self._page, "url", "") if self._page else "",
                    )
                    self._encounter_count += 1
                    await self._emit(
                        WatchdogEvent.CAPTCHA_DETECTED,
                        f"CAPTCHA detected: {captcha_type.value}",
                        "high",
                        {"captcha_type": captcha_type.value, "selector": selector},
                    )
                    logger.warning("CAPTCHA detected: %s via %s", captcha_type.value, selector)
                elif not result and self._detection is not None:
                    self._detection.resolved = True
                    self._detection.resolution_time_ms = (time.monotonic() - self._detection.detected_at) * 1000
                    self._detection = None
            except Exception as exc:
                logger.debug("CAPTCHA check error: %s", exc)
            await asyncio.sleep(poll_interval)

    async def _check_selectors(self) -> Optional[tuple[str, str]]:
        if not self._cdp:
            return None
        selectors_js = ", ".join(f'"{s}"' for s in self._config.captcha_selectors)
        expr = (
            f"(function() {{ "
            f"var selectors = [{selectors_js}]; "
            f"for (var i = 0; i < selectors.length; i++) {{ "
            f"var el = document.querySelector(selectors[i]); "
            f"if (el) {{ var src = el.src || el.getAttribute('src') || ''; "
            f"return JSON.stringify({{selector: selectors[i], url: src}}); }} "
            f"}} return null; }})()"
        )
        try:
            result = await self._send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
            if result.ok and result.data:
                val = result.data.get("result", {}).get("value")
                if val:
                    import json
                    data = json.loads(val)
                    return (data["selector"], data.get("url", ""))
        except Exception:
            pass
        return None

    def classify_captcha(self, selector: str, iframe_url: Optional[str]) -> CAPTCHAProvider:
        if iframe_url:
            for pattern, provider in _CAPTCHA_PATTERNS:
                if pattern in iframe_url:
                    if provider == CAPTCHAProvider.RECAPTCHA_V2 and "enterprise" in iframe_url:
                        return CAPTCHAProvider.RECAPTCHA_V3
                    return provider
        lower = (selector + " " + (iframe_url or "")).lower()
        if "turnstile" in lower or "cloudflare" in lower:
            return CAPTCHAProvider.CLOUDFLARE_TURNSTILE
        if "hcaptcha" in lower:
            return CAPTCHAProvider.HCAPTCHA
        if "recaptcha" in lower:
            return CAPTCHAProvider.RECAPTCHA_V2
        if "datadome" in lower:
            return CAPTCHAProvider.DATADOME
        return CAPTCHAProvider.GENERIC

    async def resolve_captcha(self) -> CAPTCHAResolution:
        """Attempt to resolve the currently-detected CAPTCHA using page interaction only.

        No external API calls are made (HB-10-02). Provider-specific strategies:
          - CLOUDFLARE_TURNSTILE: find challenge iframe, click, wait for callback.
          - RECAPTCHA_V2: find .recaptcha-checkbox, click, wait for success indicator.
          - RECAPTCHA_V3: score-based, just wait.
          - HCAPTCHA: find checkbox in iframe, click, wait.
          - GENERIC: wait 5s and re-check.
          - DATADOME / KASADA / AKAMAI: log warning, return unresolved.

        Returns:
            CAPTCHAResolution with resolved status, strategy name, and duration.
        """
        start = time.monotonic()
        detection = self._detection
        if detection is None:
            return CAPTCHAResolution(
                resolved=False, strategy="none", duration_ms=0.0,
            )

        provider = detection.captcha_type
        try:
            if provider == CAPTCHAProvider.CLOUDFLARE_TURNSTILE:
                result = await self._resolve_turnstile()
            elif provider == CAPTCHAProvider.RECAPTCHA_V2:
                result = await self._resolve_recaptcha_v2()
            elif provider == CAPTCHAProvider.RECAPTCHA_V3:
                result = await self._resolve_recaptcha_v3()
            elif provider == CAPTCHAProvider.HCAPTCHA:
                result = await self._resolve_hcaptcha()
            elif provider == CAPTCHAProvider.GENERIC:
                result = await self._resolve_generic()
            elif provider in (
                CAPTCHAProvider.DATADOME,
                CAPTCHAProvider.KASADA,
                CAPTCHAProvider.AKAMAI,
            ):
                logger.warning(
                    "CAPTCHA provider %s requires external solver — deferred to v2.0",
                    provider.value,
                )
                result = False
            else:
                logger.warning("Unknown CAPTCHA provider: %s", provider.value)
                result = False
        except Exception as exc:
            logger.debug("CAPTCHA resolution error for %s: %s", provider.value, exc)
            result = False

        duration_ms = (time.monotonic() - start) * 1000
        if result and self._detection is not None:
            self._detection.resolved = True
            self._detection.resolution_time_ms = duration_ms

        return CAPTCHAResolution(
            resolved=result,
            strategy=f"page_interaction:{provider.value}",
            duration_ms=duration_ms,
        )

    # ------------------------------------------------------------------
    # Provider-specific resolution helpers (page-interaction only)
    # ------------------------------------------------------------------

    async def _resolve_turnstile(self) -> bool:
        """Click the Turnstile challenge iframe and wait for cf-turnstile-response callback."""
        if not self._page:
            return False
        try:
            iframe = await self._page.wait_for_selector(
                'iframe[src*="challenges.cloudflare.com"]', timeout=5000,
            )
            if iframe:
                await iframe.click()
                # Wait for the cf-turnstile-response hidden input to get a value
                js = (
                    "(function() {"
                    "  var el = document.querySelector('[name=\"cf-turnstile-response\"]');"
                    "  return el ? (el.value || '').length > 0 : false;"
                    "})()"
                )
                return await self._poll_js_true(js, timeout=30.0)
        except Exception:
            logger.debug("Turnstile resolution failed")
        return False

    async def _resolve_recaptcha_v2(self) -> bool:
        """Click the reCAPTCHA v2 checkbox and wait for success indicator."""
        if not self._page:
            return False
        try:
            # Find and click the reCAPTCHA checkbox
            checkbox = await self._page.wait_for_selector(
                ".recaptcha-checkbox", timeout=5000,
            )
            if checkbox:
                await checkbox.click()
                # Wait for the checkmark / success indicator
                js = (
                    '(function() {'
                    '  var el = document.querySelector(".recaptcha-checkbox-checkmark");'
                    '  return el !== null;'
                    '})()'
                )
                return await self._poll_js_true(js, timeout=30.0)
        except Exception:
            logger.debug("reCAPTCHA v2 resolution failed")
        return False

    async def _resolve_recaptcha_v3(self) -> bool:
        """reCAPTCHA v3 is score-based — no user interaction needed, just wait."""
        await asyncio.sleep(2.0)
        return True

    async def _resolve_hcaptcha(self) -> bool:
        """Click the hCaptcha checkbox in its iframe and wait for completion."""
        if not self._page:
            return False
        try:
            iframe = await self._page.wait_for_selector(
                'iframe[src*="hcaptcha.com"]', timeout=5000,
            )
            if iframe:
                await iframe.click()
                # Wait for hCaptcha completion indicator
                js = (
                    '(function() {'
                    '  var el = document.querySelector(".hcaptcha-success");'
                    '  return el !== null;'
                    '})()'
                )
                return await self._poll_js_true(js, timeout=30.0)
        except Exception:
            logger.debug("hCaptcha resolution failed")
        return False

    async def _resolve_generic(self) -> bool:
        """Generic fallback: wait 5 seconds and re-check."""
        await asyncio.sleep(5.0)
        result = await self._check_selectors()
        return result is None

    async def _poll_js_true(self, js: str, timeout: float = 30.0) -> bool:
        """Poll a JS expression until it returns true or timeout elapses."""
        if not self._cdp:
            return False
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                result = await self._send(
                    "Runtime.evaluate",
                    {"expression": js, "returnByValue": True},
                )
                if result.ok and result.data:
                    val = result.data.get("result", {}).get("value")
                    if val:
                        return True
            except Exception:
                pass
            await asyncio.sleep(0.5)
        return False

    @property
    def is_captcha_present(self) -> bool:
        return self._detection is not None

    @property
    def detection(self) -> Optional[CAPTCHADetection]:
        return self._detection

    @property
    def encounter_count(self) -> int:
        return self._encounter_count

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _send(self, method: str, params: dict) -> Any:
        """Dispatch a CDP command via stealth_bridge.cdp_send or cdp.send."""
        if hasattr(self._cdp, "cdp_send"):
            return await self._cdp.cdp_send(method, params)
        return await self._cdp.send(method, params)
