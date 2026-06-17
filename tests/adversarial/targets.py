"""Adversarial target registry.

Each target is a self-contained descriptor: a URL, a tier, a parser that
turns a page evaluation into a Verdict, and metadata about how aggressively
it can be hit. Test files iterate this registry rather than hardcoding
per-site logic, so adding a new target never requires touching test code.

Design note: parsers take *already-evaluated* JS results, not a live page.
This keeps the registry importable and unit-testable without a browser —
``tests/adversarial/test_targets_unit.py`` (offline) verifies every parser
against canned fixtures so a markup-scraping regex change is caught without
needing network access at all.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum


class Tier(StrEnum):
    """Which class of adversary a target belongs to."""

    SCANNER = "tier1_scanner"          # open fingerprint scanners
    VENDOR = "tier2_vendor"            # commercial bot-management vendors
    CONTROLLED = "tier3_controlled"    # local, owned, offline-safe


class Verdict(StrEnum):
    """Outcome of a single target evaluation."""

    CLEAN = "clean"               # no detection signal raised
    FLAGGED = "flagged"           # explicit bot/automation signal raised
    CHALLENGED = "challenged"     # adversary presented a challenge (CAPTCHA, JS puzzle)
    INCONCLUSIVE = "inconclusive"  # could not extract a verdict (markup changed, timeout, etc)


@dataclass(frozen=True)
class TargetResult:
    """Result of evaluating one target."""

    target_id: str
    verdict: Verdict
    score: int  # 0-100, meaning is target-specific; INCONCLUSIVE always scores 0 and is excluded from averages
    detail: str
    raw: dict | None = None


@dataclass(frozen=True)
class Target:
    """A single adversarial test target."""

    target_id: str
    tier: Tier
    url: str
    description: str
    # JS expression(s) to evaluate on the page after navigation+settle.
    # Each key becomes a kwarg passed to `parser`.
    probes: dict[str, str]
    # Settle time after navigation before probes run, in ms.
    settle_ms: int = 3000
    # Per-target minimum delay before this target may be hit again, in seconds.
    # Enforced by the caller (conftest), not by the target itself.
    min_interval_s: float = 5.0
    parser: Callable[..., TargetResult] = field(repr=False, default=lambda **_: TargetResult(
        target_id="unset", verdict=Verdict.INCONCLUSIVE, score=0, detail="no parser configured"
    ))


# ---------------------------------------------------------------------------
# Tier 1 — open fingerprint scanners
# ---------------------------------------------------------------------------


def _parse_sannysoft(target_id: str, *, webdriver: bool, body_text: str, **_) -> TargetResult:
    if webdriver:
        return TargetResult(target_id, Verdict.FLAGGED, 0, "navigator.webdriver is true")
    if "you are a bot" in body_text.lower():
        return TargetResult(target_id, Verdict.FLAGGED, 0, "page explicitly labels visitor a bot")
    return TargetResult(target_id, Verdict.CLEAN, 100, "no webdriver flag, no bot label")


def _parse_incolumitas(target_id: str, *, bot_probability: float | None, body_text: str, **_) -> TargetResult:
    if bot_probability is None:
        if "human" in body_text.lower():
            return TargetResult(target_id, Verdict.CLEAN, 80, "page text indicates human, no numeric score available")
        return TargetResult(target_id, Verdict.INCONCLUSIVE, 0, "could not extract botProbability or text verdict")
    score = int(round((1.0 - bot_probability) * 100))
    verdict = Verdict.CLEAN if bot_probability <= 0.5 else Verdict.FLAGGED
    return TargetResult(target_id, verdict, score, f"bot_probability={bot_probability:.2f}")


def _parse_creepjs(target_id: str, *, trust_score: float | None, **_) -> TargetResult:
    if trust_score is None:
        return TargetResult(target_id, Verdict.INCONCLUSIVE, 0, "could not extract trust score from page")
    verdict = Verdict.CLEAN if trust_score >= 50 else Verdict.FLAGGED
    return TargetResult(target_id, verdict, int(trust_score), f"trust_score={trust_score:.1f}")


def _parse_browserscan(target_id: str, *, webdriver: bool, body_text: str, **_) -> TargetResult:
    lower = body_text.lower()
    if "selenium" in lower or "playwright" in lower:
        return TargetResult(target_id, Verdict.FLAGGED, 0, "page names an automation library directly")
    if any(p in lower for p in ("you are bot", "detected as bot", "you are a bot")):
        return TargetResult(target_id, Verdict.CHALLENGED, 20, "page renders an explicit bot verdict")
    if webdriver:
        return TargetResult(target_id, Verdict.FLAGGED, 0, "navigator.webdriver is true")
    return TargetResult(target_id, Verdict.CLEAN, 100, "no automation markers found")


TIER1_TARGETS: tuple[Target, ...] = (
    Target(
        target_id="sannysoft",
        tier=Tier.SCANNER,
        url="https://bot.sannysoft.com/",
        description="Classic WebDriver/plugin/headless indicator table",
        probes={
            "webdriver": "() => { try { return !!navigator.webdriver; } catch (e) { return false; } }",
            "body_text": "document.body.innerText",
        },
        settle_ms=2000,
        parser=_parse_sannysoft,
    ),
    Target(
        target_id="incolumitas",
        tier=Tier.SCANNER,
        url="https://bot.incolumitas.com/",
        description="Composite bot-probability score from multiple signals",
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
    Target(
        target_id="creepjs",
        tier=Tier.SCANNER,
        url="https://abrahamjuliot.github.io/creepjs/",
        description="Deep fingerprint entropy + trust score (canvas/audio/lies detection)",
        probes={
            "trust_score": (
                "() => { try { "
                "var el = document.querySelector('#trust-score, .trust-score, .visitor-trust-score, #visitor-trust'); "
                "if (el) { var m = el.innerText.match(/(\\d+(?:\\.\\d+)?)/); if (m) return parseFloat(m[1]); } "
                "if (typeof CreepJS !== 'undefined' && CreepJS.results) return CreepJS.results.trust || null; "
                "return null; } catch (e) { return null; } }"
            ),
        },
        settle_ms=6000,
        parser=_parse_creepjs,
    ),
    Target(
        target_id="browserscan",
        tier=Tier.SCANNER,
        url="https://www.browserscan.net/bot-detection",
        description="Commercial-style bot-detection consumer product",
        probes={
            "webdriver": "() => { try { return !!navigator.webdriver; } catch (e) { return false; } }",
            "body_text": "document.body.innerText",
        },
        settle_ms=6000,
        parser=_parse_browserscan,
    ),
)


# ---------------------------------------------------------------------------
# Tier 2 — commercial bot-management vendor test/demo endpoints
# ---------------------------------------------------------------------------
#
# Every URL here is a vendor-published test or demo page, explicitly meant
# to be hit by anyone evaluating the vendor's own detection product — not a
# production customer deployment. This distinction matters: we are testing
# "does Super Browser get flagged by Cloudflare's bot management product,"
# using the surface Cloudflare itself provides for that question, not
# "can Super Browser get past Ticketmaster's Cloudflare configuration."

def _parse_cloudflare_demo(target_id: str, *, challenge_present: bool, ray_id: str | None, **_) -> TargetResult:
    if challenge_present:
        return TargetResult(target_id, Verdict.CHALLENGED, 30, f"managed challenge served (ray={ray_id})")
    return TargetResult(target_id, Verdict.CLEAN, 100, f"no challenge served (ray={ray_id})")


def _parse_datadome_demo(target_id: str, *, blocked: bool, captcha_present: bool, **_) -> TargetResult:
    if blocked:
        return TargetResult(target_id, Verdict.FLAGGED, 0, "DataDome demo returned a block page")
    if captcha_present:
        return TargetResult(target_id, Verdict.CHALLENGED, 30, "DataDome demo presented a captcha")
    return TargetResult(target_id, Verdict.CLEAN, 100, "DataDome demo allowed normal access")


TIER2_TARGETS: tuple[Target, ...] = (
    Target(
        target_id="cloudflare_demo",
        tier=Tier.VENDOR,
        url="https://www.cloudflare.com/en-gb/the-bot-management-demo/",
        description="Cloudflare's own published bot-management demo/marketing page",
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
    Target(
        target_id="datadome_demo",
        tier=Tier.VENDOR,
        url="https://datadome.co/bot-protection-resources/blocking-page-demo/",
        description="DataDome's own published blocking-page demo",
        probes={
            "blocked": "() => /access denied|blocked|forbidden/i.test(document.body.innerText)",
            "captcha_present": "() => !!document.querySelector('iframe[src*=\"captcha\"], .dd-captcha')",
        },
        settle_ms=4000,
        min_interval_s=30.0,
        parser=_parse_datadome_demo,
    ),
)


ALL_TARGETS: tuple[Target, ...] = TIER1_TARGETS + TIER2_TARGETS


def targets_for_tier(tier: Tier) -> tuple[Target, ...]:
    """Return all registered targets for a given tier."""
    return tuple(t for t in ALL_TARGETS if t.tier == tier)


def target_by_id(target_id: str) -> Target | None:
    """Look up a single target by id, or None if not registered."""
    for t in ALL_TARGETS:
        if t.target_id == target_id:
            return t
    return None
