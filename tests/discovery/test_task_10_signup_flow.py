"""Task 10 — the-internet.herokuapp.com full signup/authentication journey.

Verifies that SuperBrowser can:
  1. Navigate to the-internet.herokuapp.com login page
  2. Fill username and password fields
  3. Submit the login form
  4. Verify successful login (green flash message)
  5. Extract the secure area content

Uses known test credentials: tomsmith / SuperSecretPassword!
"""

from __future__ import annotations

import asyncio
import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result


async def test_task_10_signup_flow(sb_browser):
    """Complete the login flow on the-internet.herokuapp.com."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to login page
        nav = await sb_browser.navigate(
            "https://the-internet.herokuapp.com/login"
        )
        assert nav.ok, f"Navigation to login page failed: {nav.error}"

        # Step 2: Observe the login form
        obs = await sb_browser.observe()
        assert obs.ok, f"Observe failed: {obs.error}"
        interactive = obs.data.get("interactive_elements", 0)

        # Step 3: Fill username
        fill_user = await sb_browser.fill(
            "input[name='username']",
            "tomsmith",
            description="Login username field",
        )

        # Step 4: Fill password
        fill_pass = await sb_browser.fill(
            "input[name='password']",
            "SuperSecretPassword!",
            description="Login password field",
        )

        # Step 5: Click login button
        click_login = await sb_browser.click(
            "button[type='submit']",
            description="Login button",
        )

        # Wait for redirect
        await asyncio.sleep(2)

        # Step 6: Observe the secure area
        obs2 = await sb_browser.observe()
        assert obs2.ok, f"Post-login observe failed: {obs2.error}"

        page_title = obs2.data.get("title", "")
        page_url = obs2.data.get("url", "")

        # Step 7: Extract the flash message (success indicator)
        flash_ext = await sb_browser.extract(
            "flash message",
            selector="#flash",
        )
        flash_text = ""
        if flash_ext.ok and flash_ext.data:
            flash_text = flash_ext.data.get("extracted", "") or ""

        # Step 8: Extract secure area heading
        heading_ext = await sb_browser.extract(
            "secure area heading",
            selector="h2",
        )
        heading_text = ""
        if heading_ext.ok and heading_ext.data:
            heading_text = heading_ext.data.get("extracted", "") or ""

        # Verify successful login
        login_success = (
            "secure" in page_url.lower()
            or "You logged into a secure area" in flash_text
            or "Secure Area" in heading_text
        )

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=login_success,
            expected="Successful login redirect to /secure with green flash message",
            actual=(
                f"url={page_url!r}, heading={heading_text!r}, "
                f"flash={flash_text[:80]!r}, "
                f"fill_user={fill_user.ok}, fill_pass={fill_pass.ok}, "
                f"click_login={click_login.ok}"
            ),
            error=None if login_success else "Login did not redirect to secure area",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Successful login with redirect to secure area",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_10_signup_flow.last_result = result
    return result
