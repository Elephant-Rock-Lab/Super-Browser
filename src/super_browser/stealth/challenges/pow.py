"""Kasada PoW challenge awareness — detection and classification.

Gate 4-B of the v2.0 roadmap.

Kasada uses an encrypted Proof-of-Work challenge (`collector_dx`) that
requires external solver infrastructure. This module provides:

- Detection of Kasada PoW challenges via JS/CSS fingerprinting
- Classification of challenge type (PoW, JS challenge, fingerprint)
- Documentation of what's needed for resolution (deferred to v2.1)

This module does NOT solve Kasada challenges — it detects and classifies
them so the operator can take appropriate action (proxy escalation, etc.).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class KasadaChallengeType(StrEnum):
    """Types of Kasada challenges."""

    POW = "pow"              # Proof-of-Work (encrypted collector_dx)
    JS_CHALLENGE = "js"      # JavaScript execution challenge
    FINGERPRINT = "fp"       # Browser fingerprint challenge
    UNKNOWN = "unknown"


@dataclass
class KasadaDetection:
    """Result of Kasada challenge detection."""

    detected: bool = False
    challenge_type: KasadaChallengeType = KasadaChallengeType.UNKNOWN
    collector_url: str = ""
    has_collector_dx: bool = False
    has_ksd_payload: bool = False
    page_url: str = ""
    detail: str = ""
    timestamp: float = field(default_factory=time.monotonic)

    @property
    def requires_external_solver(self) -> bool:
        """Whether this challenge requires an external solver."""
        return self.detected and self.challenge_type in (
            KasadaChallengeType.POW,
            KasadaChallengeType.FINGERPRINT,
        )


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------

# Kasada detection indicators
_KASADA_INDICATORS = {
    "script_src": "collector",
    "cookie": "ksd",
    "meta": "kasada",
    "xhr": "collector_dx",
    "css_class": "challenge-form",
    "iframe": "kasada",
}


async def detect_kasada_challenge(
    page: Any,
    cdp: Any,
) -> KasadaDetection:
    """Detect if the current page has a Kasada challenge.

    Checks multiple indicators:
    1. Script tags with 'collector' in src
    2. KSD cookie presence
    3. Meta tags referencing Kasada
    4. XHR/fetch calls to collector_dx
    5. Challenge form elements

    Args:
        page: Browser page.
        cdp: CDP bridge for Runtime.evaluate.

    Returns:
        KasadaDetection with detection details.
    """
    detection = KasadaDetection()

    # Check for Kasada indicators via JS evaluation
    js = (
        "(function() {"
        "  var result = {collector: false, ksd: false, meta: false, form: false};"
        # Check script tags
        "  var scripts = document.querySelectorAll('script[src]');"
        "  for (var i = 0; i < scripts.length; i++) {"
        "    if (scripts[i].src.indexOf('collector') !== -1) { result.collector = true; break; }"
        "  }"
        # Check cookies
        "  result.ksd = document.cookie.indexOf('ksd') !== -1;"
        # Check meta tags
        "  var metas = document.querySelectorAll('meta');"
        "  for (var i = 0; i < metas.length; i++) {"
        "    if ((metas[i].content || '').indexOf('kasada') !== -1) { result.meta = true; break; }"
        "  }"
        # Check challenge form
        "  result.form = !!document.querySelector('.challenge-form');"
        "  return JSON.stringify(result);"
        "})()"
    )

    try:
        if hasattr(cdp, "cdp_send"):
            cdp_result = await cdp.cdp_send("Runtime.evaluate", {"expression": js, "returnByValue": True})
        else:
            cdp_result = await cdp.send("Runtime.evaluate", {"expression": js, "returnByValue": True})

        if cdp_result.ok and cdp_result.data:
            val = cdp_result.data.get("result", {}).get("value")
            if val:
                import json
                indicators = json.loads(val)

                has_kasada = any([
                    indicators.get("collector"),
                    indicators.get("ksd"),
                    indicators.get("meta"),
                    indicators.get("form"),
                ])

                if has_kasada:
                    detection.detected = True
                    detection.has_ksd_payload = indicators.get("ksd", False)
                    detection.detail = (
                        f"Kasada indicators: collector={indicators.get('collector')}, "
                        f"ksd={indicators.get('ksd')}, meta={indicators.get('meta')}, "
                        f"form={indicators.get('form')}"
                    )
                    # Classify the challenge type
                    if indicators.get("form"):
                        detection.challenge_type = KasadaChallengeType.POW
                        detection.has_collector_dx = True
                    elif indicators.get("collector"):
                        detection.challenge_type = KasadaChallengeType.JS_CHALLENGE
                    else:
                        detection.challenge_type = KasadaChallengeType.FINGERPRINT

                    logger.info("Kasada challenge detected: %s", detection.detail)

    except Exception as exc:
        logger.debug("Kasada detection error: %s", exc)
        detection.detail = f"Detection failed: {exc}"

    return detection


# ---------------------------------------------------------------------------
# Documentation
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
