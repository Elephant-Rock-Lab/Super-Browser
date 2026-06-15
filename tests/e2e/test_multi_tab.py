"""E2E tests: multi-tab management.

Tests browser tab creation and management.
All tests require SB_E2E=1.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestMultiTabE2E:
    """Multi-tab operations on real browser."""

    async def test_multiple_tabs_navigate_independently(
        self,
        browser_session: object,
        e2e_context: object,
    ) -> None:
        """Two tabs can navigate to different fixture pages."""
        page1 = await browser_session.new_page()  # type: ignore[attr-defined]
        page2 = await browser_session.new_page()  # type: ignore[attr-defined]

        try:
            url1 = e2e_context.fixture_url("simple.html")  # type: ignore[attr-defined]
            url2 = e2e_context.fixture_url("form.html")  # type: ignore[attr-defined]

            await page1.goto(url1)
            await page2.goto(url2)

            title1 = await page1.title()
            title2 = await page2.title()

            assert title1 == "Simple Page"
            assert title2 == "Form Page"
        finally:
            await page1.close()
            await page2.close()

    async def test_tab_count(
        self,
        browser_session: object,
    ) -> None:
        """Browser context reports correct page count."""
        page1 = await browser_session.new_page()  # type: ignore[attr-defined]
        page2 = await browser_session.new_page()  # type: ignore[attr-defined]

        try:
            pages = browser_session.pages  # type: ignore[attr-defined]
            assert len(pages) >= 2
        finally:
            await page1.close()
            await page2.close()
