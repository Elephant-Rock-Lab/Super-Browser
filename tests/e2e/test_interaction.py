"""E2E tests: browser interaction (click, type, scroll).

Tests basic interaction primitives against local fixture pages.
All tests require SB_E2E=1.
"""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
class TestInteraction:
    """Click, type, and scroll interactions on fixture pages."""

    async def test_click_submit_button(
        self,
        form_page: object,
    ) -> None:
        """Click the submit button on form.html."""
        button = await form_page.query_selector("#submit-button")  # type: ignore[attr-defined]
        assert button is not None
        await button.click()
        # No crash = success (button type="button", no navigation)

    async def test_type_into_input(
        self,
        form_page: object,
    ) -> None:
        """Type text into an input field and verify the value."""
        inp = await form_page.query_selector("#input-1")  # type: ignore[attr-defined]
        assert inp is not None
        await inp.fill("hello world")

        value = await inp.input_value()  # type: ignore[attr-defined]
        assert value == "hello world"

    async def test_select_dropdown(
        self,
        form_page: object,
    ) -> None:
        """Select an option from the dropdown."""
        select = await form_page.query_selector("#select-1")  # type: ignore[attr-defined]
        assert select is not None
        await select.select_option("b")

        value = await select.input_value()  # type: ignore[attr-defined]
        assert value == "b"

    async def test_scroll_dom_heavy(
        self,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """Scroll the dom-heavy page and verify viewport change."""
        url = e2e_context.fixture_url("dom-heavy.html")  # type: ignore[attr-defined]
        await browser_page.goto(url)  # type: ignore[attr-defined]
        await browser_page.wait_for_selector("#item-499")  # type: ignore[attr-defined]

        # Scroll down
        await browser_page.mouse.wheel(0, 500)  # type: ignore[attr-defined]
        await browser_page.wait_for_timeout(200)  # type: ignore[attr-defined]

        # Verify scroll position changed
        scroll_y = await browser_page.evaluate("window.scrollY")  # type: ignore[attr-defined]
        assert scroll_y > 0
