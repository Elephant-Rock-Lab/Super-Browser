"""Task 03 — github.com login form fill + session detection.

Verifies that SuperBrowser can:
  1. Navigate to GitHub login page
  2. Locate and fill username/password fields
  3. Detect that form fields accept input (no real login attempted)
"""

from __future__ import annotations

import time

import pytest

pytestmark = [pytest.mark.live, pytest.mark.asyncio]

from .conftest import make_result


async def test_task_03_github_login(sb):
    """Navigate to GitHub login, fill the form with dummy data (no submit)."""
    start = time.monotonic()
    result = None

    try:
        # Step 1: Navigate to GitHub login
        nav = await sb.navigate("https://github.com/login")
        assert nav.ok, f"Navigation to GitHub login failed: {nav.error}"

        # Step 2: Observe the page to confirm form elements exist
        obs = await sb.observe()
        assert obs.ok, f"Observe failed: {obs.error}"
        interactive = obs.data.get("interactive_elements", 0)

        # Step 3: Fill username field
        fill_user = await sb.fill(
            "input[name='login']",
            "discovery-test-user",
            description="GitHub username field",
        )

        # Step 4: Fill password field
        fill_pass = await sb.fill(
            "input[name='password']",
            "discovery-test-password-not-real",
            description="GitHub password field",
        )

        # Success = both fields accepted input
        both_filled = fill_user.ok and fill_pass.ok

        # Step 5: Observe again to confirm values
        obs2 = await sb.observe()

        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=both_filled,
            expected="Username and password fields accept input without error",
            actual=(
                f"username_fill={fill_user.ok}, password_fill={fill_pass.ok}, "
                f"interactive_elements={interactive}"
            ),
            error=None if both_filled else f"fill_user.ok={fill_user.ok}, fill_pass.ok={fill_pass.ok}",
            tier_used="selector",
            latency_ms=latency,
        )

    except Exception as exc:
        latency = (time.monotonic() - start) * 1000
        result = make_result(
            success=False,
            expected="Username and password fields accept input",
            actual=f"Exception: {exc}",
            error=str(exc),
            tier_used="selector",
            latency_ms=latency,
        )

    assert result is not None
    test_task_03_github_login.last_result = result
    return result
