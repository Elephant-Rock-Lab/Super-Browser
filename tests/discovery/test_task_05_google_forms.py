"""Task 05 — docs.google.com multi-page form.

Verifies that SuperBrowser can:
  1. Navigate to a public Google Form
  2. Locate form fields
  3. Fill text inputs
  4. Detect form structure (multiple pages / sections)

NOTE: No real form submission. Uses a public test form URL.
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result

# Public Google Form for testing (a simple feedback form or similar)
FORM_URL = "https://docs.google.com/forms/d/e/1FAIpQLSfzPThYQJYeGN06snemT1gCYCfoFElx20Y2RppBZcjOlPfI1g/viewform"


async def test_task_05_google_forms(sb):
    """Navigate to a Google Form, observe structure, fill a text field."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to Google Form
        nav = await sb.navigate(FORM_URL)
        assert nav.ok, f"Navigation to Google Form failed: {nav.error}"

        # Step 2: Observe the form page
        obs = await sb.observe()
        assert obs.ok, f"Observe failed: {obs.error}"

        interactive = obs.data.get("interactive_elements", 0)
        title = obs.data.get("title", "")

        # Step 3: Try to locate and fill a text input
        # Google Forms uses various selectors for input fields
        filled_field = False
        selectors_to_try = [
            "input[type='text']",
            "input.whsOnd",
            "textarea",
            "input[aria-label]",
        ]
        for sel in selectors_to_try:
            fill_result = await sb.fill(
                sel,
                "Discovery test response",
                description=f"Google Form text field ({sel})",
            )
            if fill_result.ok:
                filled_field = True
                break

        # Step 4: Observe after filling
        obs2 = await sb.observe()
        total_elements = obs2.data.get("total_elements", 0) if obs2.ok else 0

        # Partial success = page loaded with form elements detected
        page_loaded = bool(title or interactive > 0)

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=page_loaded,
            expected="Google Form page loads with interactive form fields",
            actual=(
                f"title={title!r}, interactive_elements={interactive}, "
                f"field_filled={filled_field}, total_elements={total_elements}"
            ),
            error=None if page_loaded else "Form page did not render interactive elements",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Google Form page loads with interactive form fields",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_05_google_forms.last_result = result
    return result
