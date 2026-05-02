#!/usr/bin/env python3
"""Stealth Mode Example — Super Browser.

Demonstrates the stealth subsystem:
  - Configuring stealth options (headers, UA rotation, proxy tiers)
  - Randomising HTTP headers per request
  - Rotating user agents
  - CAPTCHA detection and waiting for resolution
  - Proxy escalation tiers
  - Running stealth diagnostics
  - Validating stealth on external check sites

No API keys required — uses mock mode for demonstration.

Run:
    python examples/stealth_mode.py
"""

import asyncio
import logging
from pathlib import Path

from super_browser.agent.facade import SuperBrowser
from super_browser.agent.llm.protocol import LLMClient
from super_browser.stealth.manager import StealthManager
from super_browser.stealth.types import (
    CAPTCHAProvider,
    ProxyTier,
    StealthConfig,
    HTTPMorphRequestConfig,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)-7s  %(message)s",
)


# ---------------------------------------------------------------------------
# Mock LLM Client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Mock LLM for stealth demo — no real API calls."""

    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        return {"done": True, "summary": "Mock completed"}

    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        return [{"step": "Done"}]

    async def replan(
        self, *, instruction, original_plan, failed_step, error
    ) -> list[dict]:
        return original_plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Demonstrate stealth mode features."""

    print("=" * 60)
    print("Super Browser — Stealth Mode Example")
    print("=" * 60)

    # ── 1. Configure Stealth ────────────────────────────────────────
    print("\n1. Configuring stealth settings ...")

    stealth_config = StealthConfig(
        # Browser fingerprint
        headless=False,                    # Headless is more detectable
        locale="en-US",
        timezone="America/New_York",
        viewport_width=1920,
        viewport_height=1080,

        # Anti-detection
        patchright_args=(
            "--disable-blink-features=AutomationControlled",
        ),
        custom_init_scripts=(
            # Override navigator.webdriver
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});",
            # Override navigator.plugins (empty in headless)
            "Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});",
        ),

        # Proxy configuration
        proxy_tier=ProxyTier.DIRECT,
        # proxy_url="http://user:pass@proxy.example.com:8080",  # Uncomment for real proxy

        # CAPTCHA settings
        captcha_detection_enabled=True,
        captcha_blocking_timeout=60.0,

        # HTTP fingerprinting
        httpmorph_enabled=True,
        chrome_version_profile="chrome143",
        platform="macos",

        # Stealth check sites
        stealth_check_urls=(
            "https://nowsecure.nl",
            "https://bot.sannysoft.com",
        ),
    )

    print(f"   Headless:          {stealth_config.headless}")
    print(f"   Locale:            {stealth_config.locale}")
    print(f"   Timezone:          {stealth_config.timezone}")
    print(f"   Viewport:          {stealth_config.viewport_width}x{stealth_config.viewport_height}")
    print(f"   Proxy tier:        {stealth_config.proxy_tier.value}")
    print(f"   Init scripts:      {len(stealth_config.custom_init_scripts)}")
    print(f"   CAPTCHA detection: {stealth_config.captcha_detection_enabled}")

    # ── 2. Create StealthManager ────────────────────────────────────
    print("\n2. Creating StealthManager ...")

    async with StealthManager(config=stealth_config) as stealth:
        await stealth.initialize()
        print("   ✓ StealthManager initialized")

        # ── 3. Header Randomization ─────────────────────────────────
        print("\n3. Randomising HTTP headers ...")

        for i in range(3):
            headers = stealth.randomize_headers(is_json=False)
            print(f"   Request {i+1}:")
            print(f"     User-Agent:  {headers.get('User-Agent', 'N/A')[:60]}...")
            print(f"     Accept:      {headers.get('Accept', 'N/A')[:50]}...")
            print(f"     Headers:     {len(headers)} total")

        # ── 4. User-Agent Rotation ──────────────────────────────────
        print("\n4. Rotating user agents ...")

        user_agents = set()
        for i in range(5):
            ua = stealth.get_user_agent()
            user_agents.add(ua)
            print(f"   UA {i+1}: {ua[:70]}...")

        print(f"   Unique UAs in 5 requests: {len(user_agents)}")

        # ── 5. Proxy Tier Management ────────────────────────────────
        print("\n5. Proxy tier management ...")

        print("   Available tiers:")
        for tier in ProxyTier:
            print(f"     • {tier.value}")

        current_tier = stealth.current_proxy_tier()
        print(f"\n   Current tier: {current_tier.value}")

        # Domain-specific tier recommendation
        domain_tier = stealth.current_proxy_tier(domain="accounts.google.com")
        print(f"   Recommended for accounts.google.com: {domain_tier.value}")

        # Escalation history
        history = stealth.escalation_history()
        print(f"   Escalation history: {len(history)} records")

        # ── 6. CAPTCHA Detection ────────────────────────────────────
        print("\n6. CAPTCHA detection ...")

        # Check for current CAPTCHA
        captcha = stealth.current_captcha()
        if captcha:
            print(f"   ⚠️ CAPTCHA detected: {captcha.captcha_type.value}")
            print(f"     Age: {captcha.age_seconds:.1f}s")
            print(f"     Resolved: {captcha.resolved}")
        else:
            print("   ✓ No CAPTCHA detected")

        # Encounter count
        print(f"   Total encounters: {stealth.captcha_encounter_count}")

        # Supported CAPTCHA providers
        print("   Supported providers:")
        for provider in CAPTCHAProvider:
            print(f"     • {provider.value}")

        # ── 7. Action Policy ────────────────────────────────────────
        print("\n7. Stealth action policy ...")

        # Evaluate whether actions are allowed
        test_actions = [
            ("navigate", "https://example.com"),
            ("click", "https://accounts.google.com"),
            ("fill", "https://example.com/form"),
        ]

        for action, url in test_actions:
            decision = stealth.evaluate_action(action, url)
            print(f"   {action:10s} @ {url[:35]:35s} → {decision.verdict.value}")

        # ── 8. Stealth Diagnostics ──────────────────────────────────
        print("\n8. Stealth diagnostics (requires CDP session) ...")
        print("   In production, run diagnostics after browser launch:")
        print()
        print("   report = await stealth.run_diagnostics()")
        print("   print(f'Passed: {report.pass_count}/{len(report.checks)}')")
        print("   for check in report.checks:")
        print("       print(f'  {check.check.value}: {\"✓\" if check.passed else \"✗\"} {check.detail}')")

        # ── 9. HTTP Requests through Stealth Stack ──────────────────
        print("\n9. HTTP requests with stealth headers ...")
        print("   In production, use http_request() for stealthy HTTP calls:")
        print()
        print("   config = HTTPMorphRequestConfig(")
        print("       url='https://api.example.com/data',")
        print("       method='GET',")
        print("       headers=stealth.randomize_headers(is_json=True),")
        print("   )")
        print("   response = await stealth.http_request(config)")
        print("   print(f'Status: {response.status_code}, Time: {response.timing_ms:.0f}ms')")

        # ── 10. Using Stealth with SuperBrowser ─────────────────────
        print("\n10. Integrating stealth with SuperBrowser ...")
        print("   Stealth is automatically configured via SuperBrowserConfig:")
        print()
        print("   from super_browser.agent.config import SuperBrowserConfig")
        print("   config = SuperBrowserConfig(enable_stealth=True)")
        print("   async with SuperBrowser(config=config, llm_client=llm) as sb:")
        print("       await sb.navigate('https://bot.sannysoft.com')")
        print("       result = await sb.extract('detection results')")

    print("\n" + "=" * 60)
    print("Stealth mode example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
