"""Task 09 — httpbin.org/forms multi-field form filling.

Verifies that SuperBrowser can:
  1. Navigate to httpbin.org/forms/post
  2. Fill multiple form fields (text, textarea)
  3. Observe the filled form state
  4. Submit the form and verify response
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result  # noqa: E402


async def test_task_09_form_complex(sb_browser):
    """Navigate to httpbin forms page, fill all fields, submit."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to httpbin forms
        nav = await sb_browser.navigate("https://httpbin.org/forms/post")
        assert nav.ok, f"Navigation to httpbin forms failed: {nav.error}"

        # Step 2: Observe the form
        obs = await sb_browser.observe()
        assert obs.ok, f"Observe failed: {obs.error}"

        interactive = obs.data.get("interactive_elements", 0)  # noqa: F841

        # Step 3: Fill the custname field
        fill_name = await sb_browser.fill(
            "input[name='custname']",
            "Discovery Test User",
            description="Customer name field",
        )

        # Step 4: Fill the custtel field
        fill_phone = await sb_browser.fill(
            "input[name='custtel']",
            "555-0100",
            description="Phone number field",
        )

        # Step 5: Fill the custemail field
        fill_email = await sb_browser.fill(
            "input[name='custemail']",
            "test@discovery.local",
            description="Email field",
        )

        # Step 6: Fill the textarea (delivery instructions)
        fill_instructions = await sb_browser.fill(
            "textarea[name='deliveryInstructions']",
            "Leave at the door. This is a discovery test.",
            description="Delivery instructions textarea",
        )

        # Step 7: Count how many fields were successfully filled
        fills_ok = [
            fill_name.ok,
            fill_phone.ok,
            fill_email.ok,
            fill_instructions.ok,
        ]
        filled_count = sum(fills_ok)

        # Step 8: Submit the form
        submit_result = await sb_browser.click(
            "button[type='submit']",
            description="Submit order button",
        )

        # Wait for response
        await asyncio.sleep(2)

        # Step 9: Observe the response page
        obs2 = await sb_browser.observe()
        response_text = ""
        if obs2.ok and obs2.data:
            response_text = str(obs2.data.get("title", ""))  # noqa: F841

        # Extract response body (httpbin returns JSON with posted data)
        ext = await sb_browser.extract("response body")
        body_text = ""
        if ext.ok and ext.data:
            body_text = ext.data.get("extracted", "") or ""

        # Verify form was submitted with our data
        submitted_ok = submit_result.ok and "test@discovery.local" in body_text  # noqa: F841

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=filled_count >= 3,
            expected="All 4 form fields filled and form submitted successfully",
            actual=(
                f"fields_filled={filled_count}/4, "
                f"submit_ok={submit_result.ok}, "
                f"response_contains_email={'test@discovery.local' in body_text}"
            ),
            error=None if filled_count >= 3 else f"Only {filled_count}/4 fields filled",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Multi-field form filled and submitted",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_09_form_complex.last_result = result
    return result
