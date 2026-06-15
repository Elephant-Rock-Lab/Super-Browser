"""KasadaDetector — Kasada challenge detection and classification.

Track D slice 1 (Wave 25). Detects Kasada anti-bot challenges and
classifies them by type (PoW, JS challenge, fingerprint).

Design constraints (per RFC v2-track-d-challenge-infrastructure.md):

- **Detection only**: Does NOT solve challenges. No "bypass" language.
- **Resolution deferred to v2.1**: Kasada's encrypted PoW requires
  external solver infrastructure.
- **Offline-first**: All detection is DOM/CDP inspection. No network calls.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

from super_browser.stealth.challenges.turnstile import _cdp_eval

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class KasadaChallengeType(StrEnum):
    """Types of Kasada challenges."""
    POW = "pow"           # Proof-of-Work (encrypted collector_dx)
    JS_CHALLENGE = "js"   # JavaScript execution challenge
    FINGERPRINT = "fp"    # Browser fingerprint challenge
    UNKNOWN = "unknown"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KasadaDetection:
    """Result of Kasada challenge detection."""
    detected: bool = False
    challenge_type: KasadaChallengeType = KasadaChallengeType.UNKNOWN
    has_collector_script: bool = False
    has_ksd_cookie: bool = False
    has_kasada_meta: bool = False
    has_challenge_form: bool = False
    detail: str = ""
    page_url: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def requires_external_solver(self) -> bool:
        """Whether this challenge requires an external solver."""
        return self.detected and self.challenge_type in (
            KasadaChallengeType.POW,
            KasadaChallengeType.FINGERPRINT,
        )


@dataclass(frozen=True)
class KasadaConfig:
    """Configuration for Kasada detection."""
    detect_enabled: bool = True


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

# JS to check all Kasada indicators in a single evaluation.
_KASADA_DETECT_JS = """
(function() {
    var result = {
        has_collector: false,
        has_ksd: false,
        has_meta: false,
        has_form: false
    };
    // Check script tags for 'collector' in src
    var scripts = document.querySelectorAll('script[src]');
    for (var i = 0; i < scripts.length; i++) {
        if (scripts[i].src.indexOf('collector') !== -1) {
            result.has_collector = true;
            break;
        }
    }
    // Check ksd cookie
    result.has_ksd = document.cookie.indexOf('ksd') !== -1;
    // Check meta tags referencing kasada
    var metas = document.querySelectorAll('meta');
    for (var i = 0; i < metas.length; i++) {
        if ((metas[i].content || '').indexOf('kasada') !== -1 ||
            (metas[i].name || '').indexOf('kasada') !== -1) {
            result.has_meta = true;
            break;
        }
    }
    // Check challenge form
    result.has_form = !!document.querySelector('.challenge-form');
    return JSON.stringify(result);
})()
"""


class KasadaDetector:
    """Detects and classifies Kasada anti-bot challenges.

    Kasada uses encrypted Proof-of-Work challenges that require
    external solver infrastructure. This detector identifies the
    presence and type of Kasada challenge — it does **NOT solve it**.

    Detection indicators:
    1. ``<script>`` with ``collector`` in ``src``
    2. ``ksd`` cookie present
    3. ``<meta>`` referencing ``kasada``
    4. ``.challenge-form`` element

    Classification logic:
    - challenge-form + collector → POW
    - collector only → JS_CHALLENGE
    - ksd/meta only → FINGERPRINT

    .. note::

        Resolution is deferred to v2.1. No solver is implemented.
    """

    def __init__(self, config: Optional[KasadaConfig] = None) -> None:
        self._config = config or KasadaConfig()

    @property
    def config(self) -> KasadaConfig:
        return self._config

    async def detect(self, page: Any, cdp: Any) -> KasadaDetection:
        """Detect and classify a Kasada challenge on the page.

        Parameters
        ----------
        page:
            Browser page (used for URL extraction).
        cdp:
            CDP bridge with ``send()`` or ``cdp_send()`` method.

        Returns
        -------
        KasadaDetection
        """
        if not self._config.detect_enabled:
            return KasadaDetection()

        try:
            val = await _cdp_eval(cdp, _KASADA_DETECT_JS)
        except Exception as exc:
            logger.debug("Kasada detection error: %s", exc)
            return KasadaDetection()

        if not val:
            return KasadaDetection()

        try:
            indicators = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return KasadaDetection()

        has_collector = indicators.get("has_collector", False)
        has_ksd = indicators.get("has_ksd", False)
        has_meta = indicators.get("has_meta", False)
        has_form = indicators.get("has_form", False)

        any_detected = any([has_collector, has_ksd, has_meta, has_form])

        if not any_detected:
            return KasadaDetection()

        # Classify challenge type
        if has_form and has_collector:
            challenge_type = KasadaChallengeType.POW
        elif has_collector:
            challenge_type = KasadaChallengeType.JS_CHALLENGE
        else:
            challenge_type = KasadaChallengeType.FINGERPRINT

        page_url = ""
        if hasattr(page, "url"):
            page_url = page.url or ""
        elif hasattr(page, "engine_page"):
            page_url = getattr(page.engine_page, "url", "") or ""

        detail = (
            f"collector={has_collector}, ksd={has_ksd}, "
            f"meta={has_meta}, form={has_form}"
        )

        return KasadaDetection(
            detected=True,
            challenge_type=challenge_type,
            has_collector_script=has_collector,
            has_ksd_cookie=has_ksd,
            has_kasada_meta=has_meta,
            has_challenge_form=has_form,
            detail=detail,
            page_url=page_url,
        )


# ---------------------------------------------------------------------------
# Resolution documentation (not a solver)
# ---------------------------------------------------------------------------

KASADA_RESOLUTION_NOTES = """
Kasada Challenge Resolution (deferred to v2.1)
===============================================

Kasada's anti-bot system uses encrypted Proof-of-Work challenges that
require significant infrastructure to solve:

1. **collector_dx**: An encrypted payload fetched via XHR that contains
   the PoW challenge parameters. The encryption is proprietary and
   changes frequently.

2. **PoW solving**: The challenge requires computing a SHA-256 hash
   that meets a difficulty target. The parameters are encrypted in
   the collector_dx payload.

3. **Session establishment**: After solving, the solution must be
   posted back to Kasada's endpoint to receive a session token
   (ksd cookie).

What's needed for resolution:
- Reverse engineering of the collector_dx encryption (cat-and-mouse)
- Or: Use a third-party solver API (e.g., CapSolver, Anti-Captcha)
- Or: Use residential proxies to avoid triggering Kasada entirely

Current status: Detection only. No resolution.
"""
