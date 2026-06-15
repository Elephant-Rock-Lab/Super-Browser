"""TurnstileDetector — Cloudflare Turnstile detection and classification.

Track D slice 1 (Wave 25). Detects Turnstile challenges on a page and
classifies them as invisible or managed.

Design constraints (per RFC v2-track-d-challenge-infrastructure.md):

- **Detection only**: Does NOT solve challenges. No "bypass" language.
- **Two-indicator requirement**: Requires ≥2 independent DOM indicators
  to prevent false positives on normal pages.
- **Offline-first**: All detection is DOM/CDP inspection. No network calls.
- **Single JS evaluation**: One ``Runtime.evaluate`` call checks all
  indicators at once for efficiency.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TurnstileVersion(StrEnum):
    """Turnstile challenge versions."""
    INVISIBLE = "invisible"   # Auto-processed, no user interaction
    MANAGED = "managed"       # Shows interactive widget
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TurnstileDetection:
    """Result of Turnstile challenge detection."""
    detected: bool
    version: TurnstileVersion = TurnstileVersion.UNKNOWN
    iframe_src: str = ""
    sitekey: str = ""
    page_url: str = ""
    indicators: dict[str, bool] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class TurnstileConfig:
    """Configuration for Turnstile detection."""
    detect_enabled: bool = True
    poll_interval_s: float = 0.5
    detection_timeout_s: float = 10.0


# ---------------------------------------------------------------------------
# Version classification (pure function, testable without browser)
# ---------------------------------------------------------------------------

def classify_turnstile_version(iframe_src: str) -> TurnstileVersion:
    """Classify Turnstile version from the iframe src URL.

    Turnstile URLs contain query parameters indicating the mode:
    - 'execution=render' or 'mode=managed' → MANAGED
    - 'execution=execute' or 'mode=invisible' → INVISIBLE
    - Default → INVISIBLE (most deployments)

    Parameters
    ----------
    iframe_src:
        The ``src`` attribute of the Turnstile iframe.

    Returns
    -------
    TurnstileVersion
    """
    if not iframe_src:
        return TurnstileVersion.UNKNOWN

    src_lower = iframe_src.lower()

    if "mode=managed" in src_lower or "execution=render" in src_lower:
        return TurnstileVersion.MANAGED

    if "mode=invisible" in src_lower or "execution=execute" in src_lower:
        return TurnstileVersion.INVISIBLE

    # Default: most Turnstile deployments are invisible
    return TurnstileVersion.INVISIBLE


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

# JS to check all Turnstile indicators in a single evaluation.
_TURNSTILE_DETECT_JS = """
(function() {
    var result = {
        has_iframe: false,
        has_response_field: false,
        has_cf_div: false,
        iframe_src: '',
        sitekey: ''
    };
    // Check for Turnstile iframe
    var iframes = document.querySelectorAll('iframe[src*="challenges.cloudflare.com"]');
    if (iframes.length > 0) {
        result.has_iframe = true;
        result.iframe_src = iframes[0].src || '';
    }
    // Check for cf-turnstile-response hidden input
    var resp = document.querySelector('[name="cf-turnstile-response"]');
    if (resp) {
        result.has_response_field = true;
    }
    // Check for .cf-turnstile div
    var div = document.querySelector('.cf-turnstile');
    if (div) {
        result.has_cf_div = true;
        // Try to extract sitekey
        var sk = div.getAttribute('data-sitekey');
        if (sk) { result.sitekey = sk; }
    }
    return JSON.stringify(result);
})()
"""


class TurnstileDetector:
    """Detects and classifies Cloudflare Turnstile challenges.

    Detection is performed by inspecting the DOM for Turnstile
    indicators:
    - ``<iframe>`` with src containing ``challenges.cloudflare.com``
    - ``.cf-turnstile`` div
    - ``[name="cf-turnstile-response"]`` hidden input

    Version classification uses iframe src query parameters.

    **Two-indicator requirement**: At least two independent indicators
    must be present for a positive detection, to prevent false positives
    on normal pages that might reference Cloudflare resources.

    .. note::

        This detector does **NOT solve** Turnstile challenges.
        Resolution is deferred to v2.1.
    """

    def __init__(self, config: Optional[TurnstileConfig] = None) -> None:
        self._config = config or TurnstileConfig()

    @property
    def config(self) -> TurnstileConfig:
        return self._config

    async def detect(self, page: Any, cdp: Any) -> TurnstileDetection:
        """Detect and classify a Turnstile challenge on the page.

        Parameters
        ----------
        page:
            Browser page (used for URL extraction).
        cdp:
            CDP bridge with ``send()`` or ``cdp_send()`` method.

        Returns
        -------
        TurnstileDetection
        """
        if not self._config.detect_enabled:
            return TurnstileDetection(detected=False)

        # Evaluate detection JS
        try:
            val = await _cdp_eval(cdp, _TURNSTILE_DETECT_JS)
        except Exception as exc:
            logger.debug("Turnstile detection error: %s", exc)
            return TurnstileDetection(detected=False)

        if not val:
            return TurnstileDetection(detected=False)

        try:
            indicators = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return TurnstileDetection(detected=False)

        # Count independent indicators
        indicator_flags = {
            "iframe": indicators.get("has_iframe", False),
            "response_field": indicators.get("has_response_field", False),
            "cf_div": indicators.get("has_cf_div", False),
        }
        active_count = sum(1 for v in indicator_flags.values() if v)

        # Two-indicator requirement for positive detection
        if active_count < 2:
            return TurnstileDetection(
                detected=False,
                indicators=indicator_flags,
            )

        # Classify version
        iframe_src = indicators.get("iframe_src", "")
        version = classify_turnstile_version(iframe_src)

        page_url = ""
        if hasattr(page, "url"):
            page_url = page.url or ""
        elif hasattr(page, "engine_page"):
            page_url = getattr(page.engine_page, "url", "") or ""

        return TurnstileDetection(
            detected=True,
            version=version,
            iframe_src=iframe_src,
            sitekey=indicators.get("sitekey", ""),
            page_url=page_url,
            indicators=indicator_flags,
        )


# ---------------------------------------------------------------------------
# CDP helper (shared)
# ---------------------------------------------------------------------------

async def _cdp_eval(cdp: Any, expression: str) -> Any:
    """Evaluate a JS expression via CDP.

    Works with both ``cdp_send()`` and ``send()`` interfaces.
    Returns the result value, or ``None`` on failure.
    """
    if hasattr(cdp, "cdp_send") and callable(getattr(cdp, "cdp_send")):
        result = await cdp.cdp_send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )
    else:
        result = await cdp.send(
            "Runtime.evaluate",
            {"expression": expression, "returnByValue": True},
        )

    if result and hasattr(result, "ok") and result.ok and result.data:
        return result.data.get("result", {}).get("value")
    if isinstance(result, dict):
        data = result.get("data", result)
        if isinstance(data, dict):
            return data.get("result", {}).get("value")
    return None
