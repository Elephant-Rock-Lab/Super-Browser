"""E2E tests: live external navigation.

These tests require SB_E2E_LIVE=1 in addition to SB_E2E=1.
They navigate to external sites and verify basic connectivity.

No assertions about page content — just that navigation succeeds
and the browser can reach the network.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestLiveNavigationE2E:
    """External navigation tests (SB_E2E_LIVE required)."""

    @pytest.fixture(autouse=True)
    def _require_live(self, e2e_context: object) -> None:
        """Skip if SB_E2E_LIVE is not set."""
        if not e2e_context.live:  # type: ignore[attr-defined]
            pytest.skip("SB_E2E_LIVE not set — skipping live navigation tests")

    async def test_navigate_example_com(
        self,
        browser_page: object,
    ) -> None:
        """Navigate to example.com (stable IANA test domain)."""
        await browser_page.goto("https://example.com", timeout=15000)  # type: ignore[attr-defined]

        title = await browser_page.title()  # type: ignore[attr-defined]
        assert "Example Domain" in title

    async def test_external_page_responsive(
        self,
        browser_page: object,
    ) -> None:
        """Verify external page responds to interaction."""
        await browser_page.goto("https://example.com", timeout=15000)  # type: ignore[attr-defined]

        # Verify page has an H1
        h1 = await browser_page.query_selector("h1")  # type: ignore[attr-defined]
        assert h1 is not None
