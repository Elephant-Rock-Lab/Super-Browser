"""Tier 7: External scanner and vendor targets.

Wraps external bot-detection sites (Sannysoft, Incolumitas, CreepJS,
Browserscan, Cloudflare demo, DataDome demo) as Vector implementations.

These are gated behind environment variables:
  SB_ADV=1              — enables scanner targets
  SB_ADV_VENDORS=1      — enables vendor targets
  SB_ADV_VENDORS_ACK=1  — required alongside SB_ADV_VENDORS
"""

from __future__ import annotations

import os
import time
from typing import Any

from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)


# ---------------------------------------------------------------------------
# Parser functions (offline-testable, take evaluated JS results)
# ---------------------------------------------------------------------------

def _parse_sannysoft(target_id: str, *, webdriver: bool, body_text: str, **_: Any) -> VectorResult:
    if webdriver:
        return _result(target_id, Verdict.FLAGGED, 0.0, "navigator.webdriver is true")
    if "you are a bot" in body_text.lower():
        return _result(target_id, Verdict.FLAGGED, 0.0, "page explicitly labels visitor a bot")
    return _result(target_id, Verdict.CLEAN, 1.0, "no webdriver flag, no bot label")


def _parse_incolumitas(target_id: str, *, bot_probability: float | None, body_text: str, **_: Any) -> VectorResult:
    if bot_probability is None:
        if "human" in body_text.lower():
            return _result(target_id, Verdict.CLEAN, 0.8, "page text indicates human")
        return _result(target_id, Verdict.INCONCLUSIVE, 0.0, "could not extract botProbability")
    score = 1.0 - bot_probability
    verdict = Verdict.CLEAN if bot_probability <= 0.5 else Verdict.FLAGGED
    return _result(target_id, verdict, score, f"bot_probability={bot_probability:.2f}")


def _parse_creepjs(target_id: str, *, trust_score: float | None, **_: Any) -> VectorResult:
    if trust_score is None:
        return _result(target_id, Verdict.INCONCLUSIVE, 0.0, "could not extract trust score")
    verdict = Verdict.CLEAN if trust_score >= 50 else Verdict.FLAGGED
    return _result(target_id, verdict, trust_score / 100.0, f"trust_score={trust_score:.1f}")


def _parse_browserscan(target_id: str, *, webdriver: bool, body_text: str, **_: Any) -> VectorResult:
    lower = body_text.lower()
    if "selenium" in lower or "playwright" in lower:
        return _result(target_id, Verdict.FLAGGED, 0.0, "page names an automation library")
    if any(p in lower for p in ("you are bot", "detected as bot", "you are a bot")):
        return _result(target_id, Verdict.CHALLENGED, 0.2, "page renders explicit bot verdict")
    if webdriver:
        return _result(target_id, Verdict.FLAGGED, 0.0, "navigator.webdriver is true")
    return _result(target_id, Verdict.CLEAN, 1.0, "no automation markers")


def _parse_cloudflare_demo(target_id: str, *, challenge_present: bool, ray_id: str | None, **_: Any) -> VectorResult:
    if challenge_present:
        return _result(target_id, Verdict.CHALLENGED, 0.3, f"managed challenge served (ray={ray_id})")
    return _result(target_id, Verdict.CLEAN, 1.0, f"no challenge served (ray={ray_id})")


def _parse_datadome_demo(target_id: str, *, blocked: bool, captcha_present: bool, **_: Any) -> VectorResult:
    if blocked:
        return _result(target_id, Verdict.FLAGGED, 0.0, "DataDome demo returned a block page")
    if captcha_present:
        return _result(target_id, Verdict.CHALLENGED, 0.3, "DataDome demo presented a captcha")
    return _result(target_id, Verdict.CLEAN, 1.0, "DataDome demo allowed normal access")


def _result(target_id: str, verdict: Verdict, score: float, detail: str) -> VectorResult:
    return VectorResult(
        vector_id=target_id,
        tier=Tier.EXTERNAL_SCANNER,  # overwritten by caller
        name=target_id,
        verdict=verdict,
        score=score,
        details={"detail": detail},
        severity=Severity.CRITICAL if verdict == Verdict.FLAGGED else Severity.INFO,
    )


# ---------------------------------------------------------------------------
# External target descriptors
# ---------------------------------------------------------------------------

class ExternalTarget:
    """Descriptor for an external target (URL + probes + parser)."""

    def __init__(
        self,
        target_id: str,
        tier: Tier,
        url: str,
        description: str,
        probes: dict[str, str],
        parser: Any,
        settle_ms: int = 4000,
        min_interval_s: float = 5.0,
    ) -> None:
        self.target_id = target_id
        self.tier = tier
        self.url = url
        self.description = description
        self.probes = probes
        self.parser = parser
        self.settle_ms = settle_ms
        self.min_interval_s = min_interval_s


SCANNER_TARGETS: list[ExternalTarget] = [
    ExternalTarget(
        target_id="ext_sannysoft",
        tier=Tier.EXTERNAL_SCANNER,
        url="https://bot.sannysoft.com/",
        description="Classic WebDriver/plugin/headless indicator table",
        probes={
            "webdriver": "() => { try { return !!navigator.webdriver; } catch (e) { return false; } }",
            "body_text": "document.body.innerText",
        },
        settle_ms=2000,
        parser=_parse_sannysoft,
    ),
    ExternalTarget(
        target_id="ext_incolumitas",
        tier=Tier.EXTERNAL_SCANNER,
        url="https://bot.incolumitas.com/",
        description="Composite bot-probability score",
        probes={
            "bot_probability": (
                "() => { var r = window.botResult; "
                "if (r && typeof r.botProbability === 'number') return r.botProbability; "
                "if (r && typeof r.score === 'number') return r.score; return null; }"
            ),
            "body_text": "document.body.innerText",
        },
        settle_ms=6000,
        parser=_parse_incolumitas,
    ),
    ExternalTarget(
        target_id="ext_creepjs",
        tier=Tier.EXTERNAL_SCANNER,
        url="https://abrahamjuliot.github.io/creepjs/",
        description="Deep fingerprint entropy + trust score",
        probes={
            "trust_score": (
                "() => { try { "
                "var el = document.querySelector('#trust-score, .trust-score'); "
                "if (el) { var m = el.innerText.match(/(\\d+(?:\\.\\d+)?)/); if (m) return parseFloat(m[1]); } "
                "return null; } catch (e) { return null; } }"
            ),
        },
        settle_ms=6000,
        parser=_parse_creepjs,
    ),
    ExternalTarget(
        target_id="ext_browserscan",
        tier=Tier.EXTERNAL_SCANNER,
        url="https://www.browserscan.net/bot-detection",
        description="Commercial-style bot-detection consumer product",
        probes={
            "webdriver": "() => { try { return !!navigator.webdriver; } catch (e) { return false; } }",
            "body_text": "document.body.innerText",
        },
        settle_ms=6000,
        parser=_parse_browserscan,
    ),
]

VENDOR_TARGETS: list[ExternalTarget] = [
    ExternalTarget(
        target_id="ext_cloudflare",
        tier=Tier.EXTERNAL_VENDOR,
        url="https://www.cloudflare.com/en-gb/the-bot-management-demo/",
        description="Cloudflare bot-management demo",
        probes={
            "challenge_present": (
                "() => !!document.querySelector('#challenge-running, .cf-turnstile, "
                "[data-translate=\"checking_browser\"]')"
            ),
            "ray_id": (
                "() => { var m = document.body.innerHTML.match(/Ray ID:\\s*([a-f0-9]+)/i); "
                "return m ? m[1] : null; }"
            ),
        },
        settle_ms=4000,
        min_interval_s=30.0,
        parser=_parse_cloudflare_demo,
    ),
    ExternalTarget(
        target_id="ext_datadome",
        tier=Tier.EXTERNAL_VENDOR,
        url="https://datadome.co/bot-protection-resources/blocking-page-demo/",
        description="DataDome blocking-page demo",
        probes={
            "blocked": "() => /access denied|blocked|forbidden/i.test(document.body.innerText)",
            "captcha_present": "() => !!document.querySelector('iframe[src*=\"captcha\"], .dd-captcha')",
        },
        settle_ms=4000,
        min_interval_s=30.0,
        parser=_parse_datadome_demo,
    ),
]

ALL_EXTERNAL_TARGETS = SCANNER_TARGETS + VENDOR_TARGETS


def get_external_targets(*, include_scanners: bool = False, include_vendors: bool = False) -> list[ExternalTarget]:
    """Return external targets based on gate flags."""
    targets: list[ExternalTarget] = []
    if include_scanners:
        targets.extend(SCANNER_TARGETS)
    if include_vendors:
        targets.extend(VENDOR_TARGETS)
    return targets


def external_targets_from_env() -> list[ExternalTarget]:
    """Return external targets enabled by environment variables."""
    adv_on = os.environ.get("SB_ADV", "").strip() == "1"
    vendor_on = (
        adv_on
        and os.environ.get("SB_ADV_VENDORS", "").strip() == "1"
        and os.environ.get("SB_ADV_VENDORS_ACK", "").strip() == "1"
    )
    return get_external_targets(include_scanners=adv_on, include_vendors=vendor_on)
