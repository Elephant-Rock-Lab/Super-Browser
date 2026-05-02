"""Task 01 — example.com basic Tier-1 navigation.

Verifies that SuperBrowser can:
  1. Navigate to a simple static page
  2. Read the page title
  3. Confirm the expected heading text is present
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result


async def test_task_01_example_nav(sb_browser):
    """Navigate to example.com and verify basic page content."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate
        nav = await sb_browser.navigate("https://example.com")
        assert nav.ok, f"Navigation failed: {nav.error}"

        # Step 2: Read title
        obs = await sb_browser.observe()
        assert obs.ok, f"Observe failed: {obs.error}"
        title = obs.data.get("title", "")
        assert "Example Domain" in title, f"Unexpected title: {title!r}"

        # Step 3: Extract heading text
        ext = await sb_browser.extract("heading", selector="h1")
        assert ext.ok, f"Extract failed: {ext.error}"
        heading = ext.data.get("extracted", "") or ""
        assert "Example Domain" in heading, f"Unexpected heading: {heading!r}"

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=True,
            expected="Page loads with title 'Example Domain' and h1 containing 'Example Domain'",
            actual=f"title={title!r}, heading excerpt={heading[:80]!r}",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Page loads with title 'Example Domain' and h1 containing 'Example Domain'",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    # Attach result for discovery collection
    test_task_01_example_nav.last_result = result
    return result
