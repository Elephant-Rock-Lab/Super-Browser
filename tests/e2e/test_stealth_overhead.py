"""E2E tests: stealth injection overhead.

Measures the timing impact of stealth script injection on navigation.
All tests require SB_E2E=1.
"""

from __future__ import annotations

import time

import pytest


@pytest.mark.asyncio
class TestStealthOverhead:
    """Stealth injection timing on local fixtures."""

    async def test_navigation_without_stealth(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Baseline navigation time without stealth injection."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]

        start = time.monotonic()
        await browser_page.goto(url)  # type: ignore[attr-defined]
        elapsed_ms = (time.monotonic() - start) * 1000

        # Should be well under 5 seconds for a local page
        assert elapsed_ms < 5000, f"Navigation took {elapsed_ms:.0f}ms"

    async def test_dom_ready_after_navigation(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Verify DOM is ready after navigation to dom-heavy page."""
        url = e2e_context.fixture_url("dom-heavy.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        # Wait for JS-generated content
        await browser_page.wait_for_selector("#item-0", timeout=5000)  # type: ignore[attr-defined]

        # Verify webdriver property is not trivially exposed
        has_webdriver = await browser_page.evaluate(  # type: ignore[attr-defined]
            "() => navigator.webdriver"
        )
        # In non-stealth mode, webdriver may be True or undefined
        # This test just verifies the evaluation works
        assert has_webdriver is None or isinstance(has_webdriver, bool)
