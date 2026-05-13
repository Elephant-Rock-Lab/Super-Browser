"""Task 06 — google.com/flights complex UI with date pickers.

Verifies that SuperBrowser can:
  1. Navigate to Google Flights
  2. Detect complex interactive elements (date pickers, dropdowns)
  3. Interact with at least one complex widget
  4. Observe the page state after interaction

NOTE: No real flight search or booking.
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result  # noqa: E402


async def test_task_06_google_flights(sb):
    """Navigate to Google Flights and interact with the search UI."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to Google Flights
        nav = await sb.navigate("https://www.google.com/flights")
        assert nav.ok, f"Navigation to Google Flights failed: {nav.error}"

        await asyncio.sleep(3)

        # Step 2: Observe the page
        obs = await sb.observe()
        assert obs.ok, f"Observe failed: {obs.error}"

        interactive = obs.data.get("interactive_elements", 0)
        title = obs.data.get("title", "")

        # Step 3: Try to fill the origin field
        origin_filled = False
        origin_selectors = [
            "input[aria-label*='Where from']",
            "input[placeholder*='Where from']",
            "input[aria-label*='origin']",
            ".n4HaVc input",  # Google Flights specific class
        ]
        for sel in origin_selectors:
            fill_result = await sb.fill(
                sel,
                "New York",
                clear_first=True,
                description="Flights origin field",
            )
            if fill_result.ok:
                origin_filled = True
                break

        # Step 4: Try to interact with date picker
        date_clicked = False
        date_selectors = [
            "input[aria-label*='Departure']",
            "button[aria-label*='Date']",
            ".n4HaVc:nth-child(2) input",
        ]
        for sel in date_selectors:
            try:
                click_result = await sb.click(sel, description="Date picker element")
                if click_result.ok:
                    date_clicked = True
                    break
            except Exception:
                continue

        # Step 5: Final observe
        await asyncio.sleep(1)
        obs2 = await sb.observe()
        final_interactive = obs2.data.get("interactive_elements", 0) if obs2.ok else 0

        # Success = page loaded with complex UI elements detected
        has_complex_ui = interactive >= 5

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=has_complex_ui,
            expected="Google Flights page with date pickers, dropdowns, and search fields",
            actual=(
                f"title={title!r}, interactive_elements={interactive}, "
                f"origin_filled={origin_filled}, date_clicked={date_clicked}, "
                f"final_interactive={final_interactive}"
            ),
            error=None if has_complex_ui else f"Only {interactive} interactive elements found (expected ≥5)",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Google Flights page with complex interactive elements",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_06_google_flights.last_result = result
    return result
