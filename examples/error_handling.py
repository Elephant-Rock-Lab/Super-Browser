#!/usr/bin/env python3
"""Error Handling Example — Super Browser.

Demonstrates structured error categories, recovery hints, and
stale reference detection. Shows how to use FailureCategory and
NextAction for programmatic error recovery.

Run:
    python examples/error_handling.py
"""

import asyncio
import logging

from super_browser.agent.facade import SuperBrowser
from super_browser.results.types import FailureCategory

logging.basicConfig(level=logging.INFO, format="%(name)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def demo_error_categories() -> None:
    """Show how different failure categories map to recovery strategies."""
    print("=" * 60)
    print("Super Browser — Error Handling")
    print("=" * 60)

    async with SuperBrowser() as sb:
        result = await sb.navigate("https://example.com")

        # ── Check result.ok ──────────────────────────────────────
        if result.ok:
            print("\n✓ Navigation succeeded")
            print(f"  URL: {result.data.final_url}")
            print(f"  Time: {result.meta.duration_ms:.0f}ms")
        else:
            # ── Inspect error category ───────────────────────────
            err = result.error
            print("\n✗ Navigation failed")
            print(f"  Category: {err.category.value}")
            print(f"  Message:  {err.message}")
            print(f"  Recoverable: {err.recoverable}")

            # ── Handle by category ───────────────────────────────
            if err.category.value == "timeout":
                print("  → Recovery: increase timeout or check network")
            elif err.category.value == "navigation":
                print("  → Recovery: check URL validity and DNS")
            elif err.category.value == "security":
                print("  → Recovery: review domain allow/deny lists")

        # ── Attempt a click that will likely fail ────────────────
        click_result = await sb.click("#nonexistent-element")

        if not click_result.ok:
            print("\n✗ Click failed (expected — element doesn't exist)")
            err = click_result.error
            print(f"  Category: {err.category.value}")
            print(f"  Message:  {err.message}")

        # ── Show failure categories ──────────────────────────────
        print(f"\n{'='*60}")
        print("Available FailureCategories:")
        for cat in FailureCategory:
            print(f"  • {cat.value}")
        print(f"{'='*60}")


async def demo_recovery_hints() -> None:
    """Show how NextAction recovery hints work."""
    print("\n\nRecovery Hints (NextAction)")
    print("-" * 40)

    async with SuperBrowser() as sb:
        await sb.navigate("https://example.com")

        # When an action fails, next_actions provides recovery guidance
        result = await sb.click("#this-element-does-not-exist")

        if not result.ok and result.error:
            # Check for stale ref detection
            if hasattr(result, 'failure_category'):
                fc = result.failure_category
                if fc == FailureCategory.STALE_REF:
                    print("  Stale reference detected!")
                    for hint in (result.next_actions or []):
                        print(f"    → {hint.action_id}: {hint.description}")

            print(f"\n  Error: {result.error.category.value} — {result.error.message}")
            print(f"  Recoverable: {result.error.recoverable}")
            if result.error.retry_hint:
                print(f"  Retry hint: {result.error.retry_hint}")


async def main() -> None:
    """Run all error handling demonstrations."""
    await demo_error_categories()
    await demo_recovery_hints()

    print(f"\n{'='*60}")
    print("Key takeaway: every ActionResult carries structured error info.")
    print("Use .error.category for branching, .error.message for logging,")
    print("and .next_actions for automated recovery.")
    print(f"{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())
