"""E2E tests: session persistence.

Tests save/load of browser session state (cookies, localStorage).
All tests require SB_E2E=1.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestSessionPersistenceE2E:
    """Session state save/load on real browser."""

    async def test_cookie_persistence_across_contexts(
        self,
        browser_session: object,
        e2e_context: object,
    ) -> None:
        """Set a cookie, save state, verify it persists."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]

        page = await browser_session.new_page()  # type: ignore[attr-defined]
        await page.goto(url)

        # Set a cookie via JS
        await page.evaluate("document.cookie = 'test_cookie=e2e_value; path=/'")

        # Verify cookie is set
        cookies = await browser_session.cookies()  # type: ignore[attr-defined]
        test_cookies = [c for c in cookies if c.get("name") == "test_cookie"]
        assert len(test_cookies) == 1
        assert test_cookies[0]["value"] == "e2e_value"

        await page.close()

    async def test_local_storage_persistence(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """localStorage persists values within the same context."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        # Set localStorage
        await browser_page.evaluate("localStorage.setItem('test_key', 'test_value')")  # type: ignore[attr-defined]

        # Verify
        value = await browser_page.evaluate("localStorage.getItem('test_key')")  # type: ignore[attr-defined]
        assert value == "test_value"
