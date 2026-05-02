"""CAPTCHAWatchdog — CDP event-driven CAPTCHA detection and classification."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Optional

from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.types import WatchdogEvent
from super_browser.recovery.watchdogs import BaseWatchdog
from super_browser.stealth.types import CAPTCHADetection, CAPTCHAProvider, StealthConfig

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
        if page and hasattr(page, "cdp"):
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
            result = await self._cdp.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})
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

    @property
    def is_captcha_present(self) -> bool:
        return self._detection is not None

    @property
    def detection(self) -> Optional[CAPTCHADetection]:
        return self._detection

    @property
    def encounter_count(self) -> int:
        return self._encounter_count
