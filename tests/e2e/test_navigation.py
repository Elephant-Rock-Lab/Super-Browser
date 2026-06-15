"""E2E tests: local fixture navigation.

Tests navigation to local fixture pages served by FixtureServer.
All tests require SB_E2E=1.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestLocalNavigation:
    """Navigation against local fixture pages."""

    async def test_navigate_simple_page(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Navigate to simple.html and verify title."""
        url = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        title = await browser_page.title()  # type: ignore[attr-defined]
        assert title == "Simple Page"

    async def test_navigate_form_page(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Navigate to form.html and verify form elements exist."""
        url = e2e_context.fixture_url("form.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        # Verify the submit button exists
        button = await browser_page.query_selector("#submit-button")  # type: ignore[attr-defined]
        assert button is not None

    async def test_navigate_dom_heavy_page(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Navigate to dom-heavy.html and verify DOM structure."""
        url = e2e_context.fixture_url("dom-heavy.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]

        # Wait for JS to generate items
        await browser_page.wait_for_selector("#item-499")  # type: ignore[attr-defined]

        # Verify items were generated
        items = await browser_page.query_selector_all(".item")  # type: ignore[attr-defined]
        assert len(items) == 500
