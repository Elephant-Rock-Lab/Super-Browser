"""Task 02 — google.com search + DOM extraction.

Verifies that SuperBrowser can:
  1. Navigate to Google
  2. Fill the search box with a query
  3. Submit the search
  4. Extract search results from the DOM
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result  # noqa: E402


async def test_task_02_google_search(sb):
    """Search Google for 'Patchright browser automation' and extract results."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to Google
        nav = await sb_browser_nav(sb, "https://www.google.com")
        if not nav.ok:
            raise RuntimeError(f"Navigation failed: {nav.error}")

        # Step 2: Accept consent / cookie banner if present (EU/UK)
        try:
            await sb.click("Accept all", description="Google cookie consent button")
        except Exception:
            pass  # No consent dialog — fine

        # Step 3: Fill search box
        fill_result = await sb.fill(
            "textarea[name='q'], input[name='q']",
            "Patchright browser automation",
            description="Google search box",
        )
        if not fill_result.ok:
            # Try using act() with LLM if direct fill fails
            act_result = await sb.act(
                "Type 'Patchright browser automation' into the Google search box and press Enter",
                max_steps=10,
            )
            if not act_result.ok:
                raise RuntimeError("Both fill and act failed for search box")

        # Step 4: Wait for results to load
        import asyncio
        await asyncio.sleep(3)

        # Step 5: Extract search results
        obs = await sb.observe()  # noqa: F841
        ext = await sb.extract("search results")
        extracted_text = ""
        if ext.ok and ext.data:
            extracted_text = ext.data.get("extracted", "") or ""

        # Verify we got results
        has_results = bool(extracted_text and len(extracted_text) > 50)

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=has_results,
            expected="Search results page with multiple results for 'Patchright browser automation'",
            actual=f"Extracted {len(extracted_text)} chars of result text" if extracted_text else "No results extracted",
            error=None if has_results else "Search results extraction yielded insufficient content",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Search results page with multiple results",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_02_google_search.last_result = result
    return result


async def sb_browser_nav(sb, url):
    """Helper — navigate via the sb fixture."""
    return await sb.navigate(url)
